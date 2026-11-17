from __future__ import division

import numpy as np


def blossom(control_points, knots, degree, span, args):
    points = [np.asarray(control_points[i], dtype=float) for i in range(span - degree, span + 1)]
    for level, t in enumerate(args, 1):
        for j in range(degree, level - 1, -1):
            i = span - degree + j
            alpha = (t - knots[i]) / (knots[i + degree + 1 - level] - knots[i])
            points[j] = (1.0 - alpha) * points[j - 1] + alpha * points[j]
    return points[degree]


def bspline_to_bezier(control_points, knots, degree):
    if len(knots) != len(control_points) + degree + 1:
        raise ValueError('expected {} knots, got {}'.format(len(control_points) + degree + 1, len(knots)))
    segments = []
    for span in range(degree, len(control_points)):
        a, b = knots[span], knots[span + 1]
        if a < b:
            segments.append([
                blossom(control_points, knots, degree, span, [a] * (degree - k) + [b] * k).tolist()
                for k in range(degree + 1)
            ])
    return segments
