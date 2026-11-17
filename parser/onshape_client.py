from apikey.client import Client

FEATURESCRIPT_URL = '/api/partstudios/d/{}/w/{}/e/{}/featurescript'

ENTITY_DEFINITION_SCRIPT = """
function(context is Context, queries) {
    var res_list = [];
    var q_arr = evaluateQuery(context, queries.id);
    for (var i = 0; i < size(q_arr); i += 1) {
        res_list = append(res_list, %s(context, { "%s" : q_arr[i] }));
    }
    return res_list;
}
"""

SKETCH_TOPOLOGY_SCRIPT = """
function(context is Context, queries) {
    var topo = {};
    topo.faces = [];
    topo.edges = [];
    topo.vertices = [];
    var all_edge_ids = [];
    var all_vertex_ids = [];
    var face_arr = evaluateQuery(context, qSketchRegion(makeId("%s")));
    for (var i = 0; i < size(face_arr); i += 1) {
        var face_topo = {};
        face_topo.id = transientQueriesToStrings(face_arr[i]);
        face_topo.edges = [];
        var edge_arr = evaluateQuery(context, qAdjacent(face_arr[i], AdjacencyType.EDGE, EntityType.EDGE));
        for (var j = 0; j < size(edge_arr); j += 1) {
            var edge_topo = {};
            const edge_id = transientQueriesToStrings(edge_arr[j]);
            edge_topo.id = edge_id;
            edge_topo.vertices = [];
            edge_topo.param = evCurveDefinition(context, { "edge" : edge_arr[j] });
            face_topo.edges = append(face_topo.edges, edge_id);
            var vertex_arr = evaluateQuery(context, qAdjacent(edge_arr[j], AdjacencyType.VERTEX, EntityType.VERTEX));
            for (var k = 0; k < size(vertex_arr); k += 1) {
                var vertex_topo = {};
                const vertex_id = transientQueriesToStrings(vertex_arr[k]);
                vertex_topo.id = vertex_id;
                vertex_topo.param = evVertexPoint(context, { "vertex" : vertex_arr[k] });
                edge_topo.vertices = append(edge_topo.vertices, vertex_id);
                if (isIn(vertex_id, all_vertex_ids)) { continue; }
                all_vertex_ids = append(all_vertex_ids, vertex_id);
                topo.vertices = append(topo.vertices, vertex_topo);
            }
            if (isIn(edge_id, all_edge_ids)) { continue; }
            all_edge_ids = append(all_edge_ids, edge_id);
            topo.edges = append(topo.edges, edge_topo);
        }
        topo.faces = append(topo.faces, face_topo);
    }
    return topo;
}
"""

BOUNDING_BOX_SCRIPT = """
function(context is Context, queries) {
    var q_body = qBodyType(qEverything(EntityType.BODY), BodyType.SOLID);
    return evBox3d(context, { "topology" : q_body });
}
"""

CURVE_MIDPOINT_SCRIPT = """
function(context is Context, queries) {
    var q_arr = evaluateQuery(context, queries.id);
    return evEdgeTangentLine(context, { "edge" : q_arr[0], "parameter" : 0.5 }).origin;
}
"""

EXPRESSION_SCRIPT = """
function(context is Context, queries) {
    return lookupTableEvaluate("%s") * meter;
}
"""

ENTITY_EVALUATORS = {'VERTEX': ('evVertexPoint', 'vertex'),
                     'EDGE': ('evCurveDefinition', 'edge'),
                     'FACE': ('evSurfaceDefinition', 'face')}


def decode(entry):
    message = entry['message']
    value = message.get('value')
    if entry.get('typeName') == 'BTFSValueArray':
        return [decode(item) for item in value]
    if entry.get('typeName') == 'BTFSValueMap':
        result = dict((decode(item['message']['key']), decode(item['message']['value'])) for item in value)
        if message.get('typeTag'):
            result['type'] = message['typeTag']
        return result
    return value


def rounded(values):
    return [round(v, 8) for v in values]


class OnshapeClient(Client):

    def run_featurescript(self, document, script, queries=None):
        response = self._api.request('post', FEATURESCRIPT_URL.format(*document),
                                     body={'script': script, 'queries': queries or []})
        return decode(response.json()['result'])

    def entity_definitions(self, document, entity_ids, entity_type):
        script = ENTITY_DEFINITION_SCRIPT % ENTITY_EVALUATORS[entity_type]
        return self.run_featurescript(document, script, [{'key': 'id', 'value': entity_ids}])

    def plane(self, document, face_id):
        definition = self.entity_definitions(document, [face_id], 'FACE')[0]
        return dict((key, rounded(definition[key])) for key in ('origin', 'normal', 'x'))

    def sketch_topology(self, document, feature_id):
        topology = self.run_featurescript(document, SKETCH_TOPOLOGY_SCRIPT % feature_id)
        edges = {}
        for edge in topology['edges']:
            param = edge['param']
            if 'coordSystem' in param:
                param['coordSystem'] = dict((key, rounded(param['coordSystem'][key]))
                                            for key in ('origin', 'xAxis', 'zAxis'))
            if 'radius' in param:
                param['radius'] = round(param['radius'], 8)
            edges[edge['id']] = edge
        vertices = dict((vertex['id'], rounded(vertex['param'])) for vertex in topology['vertices'])
        return {'faces': topology['faces'], 'edges': edges, 'vertices': vertices}

    def bounding_box(self, document):
        return self.run_featurescript(document, BOUNDING_BOX_SCRIPT)

    def curve_midpoint(self, document, edge_id):
        return self.run_featurescript(document, CURVE_MIDPOINT_SCRIPT, [{'key': 'id', 'value': [edge_id]}])

    def expression_to_meter(self, document, expression):
        return self.run_featurescript(document, EXPRESSION_SCRIPT % expression)
