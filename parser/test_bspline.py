from __future__ import division, print_function

import numpy as np

from bspline import bspline_to_bezier


def basis(i, degree, knots, u):
    if degree == 0:
        return 1.0 if knots[i] <= u < knots[i + 1] else 0.0
    value = 0.0
    if knots[i + degree] > knots[i]:
        value += (u - knots[i]) / (knots[i + degree] - knots[i]) * basis(i, degree - 1, knots, u)
    if knots[i + degree + 1] > knots[i + 1]:
        value += (knots[i + degree + 1] - u) / (knots[i + degree + 1] - knots[i + 1]) * basis(i + 1, degree - 1, knots, u)
    return value


def bspline_point(control_points, knots, degree, u):
    return sum(basis(i, degree, knots, u) * np.asarray(p) for i, p in enumerate(control_points))


def bezier_point(segment, t):
    points = [np.asarray(p, dtype=float) for p in segment]
    while len(points) > 1:
        points = [(1 - t) * p + t * q for p, q in zip(points, points[1:])]
    return points[0]


def check(name, knots, num_control_points, degree=3):
    control_points = np.random.RandomState(0).normal(size=(num_control_points, 3)).tolist()
    segments = bspline_to_bezier(control_points, knots, degree)
    domain = sorted(set(k for k in knots[degree:len(knots) - degree]))
    assert len(segments) == len(domain) - 1, name
    for segment, a, b in zip(segments, domain, domain[1:]):
        for t in np.linspace(0.0, 0.99, 12):
            error = np.abs(bezier_point(segment, t) - bspline_point(control_points, knots, degree, a + t * (b - a))).max()
            assert error < 1e-12, (name, error)
    for left, right in zip(segments, segments[1:]):
        assert np.allclose(left[-1], right[0]), name
    print('ok  {:<28} {} segments'.format(name, len(segments)))


if __name__ == '__main__':
    check('single interior knot', [0, 0, 0, 0, 0.42458506755049114, 1, 1, 1, 1], 5)
    check('several interior knots', [0, 0, 0, 0, 0.2, 0.5, 0.7, 1, 1, 1, 1], 7)
    check('double interior knot', [0, 0, 0, 0, 0.3, 0.3, 0.6, 1, 1, 1, 1], 7)
    check('triple interior knot', [0, 0, 0, 0, 0.4, 0.4, 0.4, 1, 1, 1, 1], 7)
    check('shifted domain', [2, 2, 2, 2, 3.5, 7, 7, 7, 7], 5)
    check('single bezier', [0, 0, 0, 0, 1, 1, 1, 1], 4)
    check('periodic (onshape layout)', [-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75], 7)
    check('quadratic', [0, 0, 0, 0.5, 1, 1, 1], 4, degree=2)
