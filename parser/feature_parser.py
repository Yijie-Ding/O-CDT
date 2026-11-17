from __future__ import division, print_function

import math
from collections import OrderedDict

import numpy as np

from bspline import bspline_to_bezier
from onshape_client import decode

EXTENT_TYPES = {'BLIND': 'OneSideFeatureExtentType',
                'SYMMETRIC': 'SymmetricFeatureExtentType'}
OPERATIONS = {'NEW': 'NewBodyFeatureOperation',
              'ADD': 'JoinFeatureOperation',
              'REMOVE': 'CutFeatureOperation',
              'INTERSECT': 'IntersectFeatureOperation'}
ENDPOINT_TOLERANCE = 1e-6


def xyz(values):
    return OrderedDict(zip('xyz', values))


def unit(vector):
    return vector / np.linalg.norm(vector)


def polar_angle(vector):
    return math.atan2(vector[1], vector[0]) % (2.0 * math.pi)


def parse_angle(angle):
    if isinstance(angle, (int, float)):
        return float(angle)
    value, unit_name = angle.split()
    if unit_name != 'deg':
        raise ValueError('unexpected angle format: {}'.format(angle))
    return float(value)


def parse_feature_params(parameters):
    params = {}
    for item in parameters:
        message = item['message']
        if 'queries' in message:
            value = [geometry_id for query in message['queries'] for geometry_id in query['message']['geometryIds']]
        elif 'expression' in message:
            value = message['expression']
        elif 'value' in message:
            value = message['value']
        else:
            raise NotImplementedError('unsupported parameter: {}'.format(message))
        params[message['parameterId']] = value
    return params


def model_parameter(value, role):
    return {'type': 'ModelParameter', 'value': value, 'name': 'none', 'role': role}


def distance_extent(distance, distance_role, taper_role):
    return {'distance': model_parameter(distance, distance_role),
            'taper_angle': model_parameter(0.0, taper_role),
            'type': 'DistanceExtentDefinition'}


class FeatureListParser(object):

    def __init__(self, client, document, data_id=None):
        self.client = client
        self.document = document
        self.data_id = data_id
        self.features = client.get_features(*document).json()['features']
        self.profile_to_sketch = {}
        self.detected_bsplines = []

    def parse(self):
        result = {'entities': OrderedDict(), 'properties': {}, 'sequence': []}
        try:
            result['properties']['bounding_box'] = self._bounding_box()
        except Exception as e:
            print(self.data_id, 'bounding box failed:', e)
            return result
        for index, item in enumerate(self.features):
            feature = item['message']
            feature_id = feature['featureId']
            try:
                entity = self._parse_feature(feature)
            except Exception as e:
                print(self.data_id, 'parse feature failed:', e)
                break
            result['entities'][feature_id] = entity
            result['sequence'].append({'index': index, 'type': entity['type'], 'entity': feature_id})
        return result

    def _parse_feature(self, feature):
        feature_type = feature['featureType']
        if feature_type == 'newSketch':
            sketch = SketchParser(self.client, feature, self.document, self.data_id)
            entity = sketch.parse()
            self.detected_bsplines.extend(sketch.detected_bsplines)
            for profile_id in entity['profiles']:
                self.profile_to_sketch[profile_id] = feature['featureId']
            return entity
        if feature_type == 'extrude':
            return self._parse_extrude(feature)
        if feature_type == 'revolve':
            return self._parse_revolve(feature)
        raise NotImplementedError('unsupported feature type: {}'.format(feature_type))

    def _bounding_box(self):
        box = self.client.bounding_box(self.document)
        return {'type': 'BoundingBox3D',
                'max_point': xyz(box['maxCorner']),
                'min_point': xyz(box['minCorner'])}

    def _to_meter(self, expression):
        return self.client.expression_to_meter(self.document, expression)

    def _profiles(self, geometry_ids):
        return [{'profile': profile_id, 'sketch': self.profile_to_sketch[profile_id]} for profile_id in geometry_ids]

    def _parse_extrude(self, feature):
        params = parse_feature_params(feature['parameters'])
        if params.get('hasOffset') is True:
            raise NotImplementedError('extrude with offset')
        end_bound = params['endBound']
        if end_bound not in EXTENT_TYPES:
            raise NotImplementedError('endBound type: {}'.format(end_bound))

        extent_one = self._to_meter(params['depth'])
        if end_bound == 'SYMMETRIC':
            extent_one /= 2
        if params.get('oppositeDirection') is True:
            extent_one = -extent_one

        extent_two = 0.0
        extent_type = EXTENT_TYPES[end_bound]
        if params.get('hasSecondDirection') is True:
            if params['secondDirectionBound'] != 'BLIND':
                raise NotImplementedError('secondDirectionBound type: {}'.format(params['secondDirectionBound']))
            extent_type = 'TwoSidesFeatureExtentType'
            extent_two = self._to_meter(params['secondDirectionDepth'])
            if params.get('secondDirectionOppositeDirection') is True:
                extent_two = -extent_two

        return {'name': feature['name'],
                'type': 'ExtrudeFeature',
                'profiles': self._profiles(params['entities']),
                'operation': OPERATIONS[params['operationType']],
                'start_extent': {'type': 'ProfilePlaneStartDefinition'},
                'extent_type': extent_type,
                'extent_one': distance_extent(extent_one, 'AlongDistance', 'TaperAngle'),
                'extent_two': distance_extent(extent_two, 'AgainstDistance', 'Side2TaperAngle')}

    def _parse_revolve(self, feature):
        params = parse_feature_params(feature['parameters'])
        if params.get('hasOffset') is True:
            raise NotImplementedError('revolve with offset')

        revolve_type = params.get('revolveType', 'FULL')
        if revolve_type == 'FULL':
            angle_one, angle_two, extent_type = 360.0, 0.0, 'FullFeatureExtentType'
        elif revolve_type == 'ONE_DIRECTION':
            angle_one, angle_two, extent_type = parse_angle(params['angle']), 0.0, 'OneSideFeatureExtentType'
        elif revolve_type == 'SYMMETRIC':
            angle_one = angle_two = parse_angle(params['angle'])
            extent_type = 'SymmetricFeatureExtentType'
        elif revolve_type == 'TWO_DIRECTIONS':
            angle_one, angle_two = parse_angle(params['angle']), parse_angle(params['angleBack'])
            extent_type = 'TwoSidesFeatureExtentType'
        else:
            raise NotImplementedError('revolveType: {}'.format(revolve_type))
        if params.get('oppositeDirection', False):
            angle_one = -angle_one

        return {'name': feature['name'],
                'type': 'RevolveFeature',
                'profiles': self._profiles(params['entities']),
                'axis': self._revolve_axis(params['axis'][0]),
                'operation': OPERATIONS.get(params.get('operationType', 'NEW'), OPERATIONS['NEW']),
                'extent_type': extent_type,
                'angle_one': angle_one,
                'angle_two': angle_two,
                'start_extent': {'type': 'ProfilePlaneStartDefinition'}}

    def _revolve_axis(self, axis_id):
        line = self.client.entity_definitions(self.document, [axis_id], 'EDGE')[0]
        origin = np.array(line['origin'])
        return {'type': 'EdgeAxisDefinition',
                'entity': axis_id,
                'start_point': xyz(origin.tolist()),
                'end_point': xyz((origin + np.array(line['direction'])).tolist())}


class SketchParser(object):

    def __init__(self, client, feature, document, data_id=None):
        self.client = client
        self.document = document
        self.data_id = data_id
        self.feature_id = feature['featureId']
        self.name = feature['name']
        params = parse_feature_params(feature['parameters'])

        self.plane = client.plane(document, params['sketchPlane'][0])
        self.origin = np.array(self.plane['origin'])
        self.axes = np.array([self.plane['x'], np.cross(self.plane['normal'], self.plane['x']), self.plane['normal']])

        topology = client.sketch_topology(document, self.feature_id)
        self.faces = topology['faces']
        self.edges = topology['edges']
        self.vertices = dict((vertex_id, self.to_local(point)) for vertex_id, point in topology['vertices'].items())
        self.detected_bsplines = []

    def to_local(self, point):
        return self.axes.dot(np.asarray(point) - self.origin).tolist()

    def parse(self):
        profiles = {}
        for face in self.faces:
            loops = [{'is_outer': True,
                      'profile_curves': [curve for edge_id in loop for curve in self._parse_edge(edge_id)]}
                     for loop in self._edge_loops(face['edges'])]
            profiles[face['id']] = {'loops': loops, 'properties': {}}
        transform = {'origin': xyz(self.plane['origin']),
                     'z_axis': xyz(self.plane['normal']),
                     'x_axis': xyz(self.plane['x']),
                     'y_axis': xyz(self.axes[1].tolist())}
        return {'name': self.name, 'type': 'Sketch', 'profiles': profiles,
                'transform': transform, 'reference_plane': {}}

    def _edge_loops(self, edge_ids):
        vertex_to_edges = {}
        for edge_id in edge_ids:
            for vertex_id in self.edges[edge_id]['vertices']:
                vertex_to_edges.setdefault(vertex_id, []).append(edge_id)

        loops = []
        remaining = list(edge_ids)
        while remaining:
            edge_id = remaining.pop(0)
            loop = [edge_id]
            vertices = self.edges[edge_id]['vertices']
            if vertices:
                start, end = vertices[0], vertices[-1]
                while end != start:
                    edge_id = next(e for e in vertex_to_edges[end] if e != edge_id)
                    loop.append(edge_id)
                    remaining.remove(edge_id)
                    end = next(v for v in self.edges[edge_id]['vertices'] if v != end)
            loops.append(loop)
        return loops

    def _parse_edge(self, edge_id):
        edge = self.edges[edge_id]
        param = edge['param']
        edge_type = param['type']
        points = [self.vertices[vertex_id] for vertex_id in edge['vertices']]

        if edge_type == 'Line':
            start, end = points
            return [OrderedDict([('type', 'Line3D'), ('start_point', xyz(start)), ('end_point', xyz(end)),
                                 ('curve', edge_id)])]
        if edge_type == 'Circle' and len(points) == 2:
            return [self._arc(edge_id, param, *points)]
        if edge_type == 'Circle' and len(points) < 2:
            return [OrderedDict([('type', 'Circle3D'),
                                 ('center_point', xyz(self.to_local(param['coordSystem']['origin']))),
                                 ('radius', param['radius']),
                                 ('normal', xyz(param['coordSystem']['zAxis'])),
                                 ('curve', edge_id)])]
        if edge_type == 'BSplineCurve':
            return self._bezier_segments(edge_id, param, points)
        raise NotImplementedError('edge type: {}'.format(edge_type))

    def _arc(self, edge_id, param, start, end):
        center = np.array(self.to_local(param['coordSystem']['origin']))
        start_vector = unit(np.array(start) - center)
        end_vector = unit(np.array(end) - center)
        start_angle, end_angle = polar_angle(start_vector), polar_angle(end_vector)
        if start_angle > end_angle:
            start_angle, end_angle = end_angle, start_angle
            start_vector, end_vector = end_vector, start_vector
        sweep_angle = end_angle - start_angle

        midpoint = self.to_local(self.client.curve_midpoint(self.document, edge_id))
        mid_angle = polar_angle(unit(np.array(midpoint) - center))
        if round(mid_angle, 3) != round((start_angle + end_angle) / 2, 3):
            sweep_angle = 2 * np.pi - sweep_angle
            start_vector = end_vector

        return OrderedDict([('type', 'Arc3D'),
                            ('start_point', xyz(start)),
                            ('end_point', xyz(end)),
                            ('center_point', xyz(center.tolist())),
                            ('radius', param['radius']),
                            ('normal', xyz(param['coordSystem']['zAxis'])),
                            ('start_angle', 0.0),
                            ('end_angle', sweep_angle),
                            ('reference_vector', xyz(start_vector.tolist())),
                            ('curve', edge_id)])

    def _bezier_segments(self, edge_id, param, vertices):
        degree = int(param['degree'])
        if degree != 3 or param.get('isRational'):
            raise NotImplementedError('only non-rational cubic B-splines are supported')
        control_points = [self.to_local(point) for point in param['controlPoints']]
        segments = bspline_to_bezier(control_points, param['knots'], degree)
        if not matches_vertices(segments[0][0], segments[-1][-1], vertices):
            raise NotImplementedError('B-spline edge is trimmed by its vertices')

        self.detected_bsplines.append({'file_id': self.data_id,
                                       'edge_id': edge_id,
                                       'control_points': control_points,
                                       'knots': param['knots'],
                                       'degree': degree})
        return [OrderedDict([('type', 'Bezier3D'), ('control_points', segment), ('curve', edge_id)])
                for segment in segments]


def matches_vertices(first, last, vertices):
    def close(a, b):
        return np.allclose(a, b, atol=ENDPOINT_TOLERANCE)

    if len(vertices) == 2:
        a, b = vertices
        return (close(first, a) and close(last, b)) or (close(first, b) and close(last, a))
    return close(first, last) and all(close(first, v) for v in vertices)
