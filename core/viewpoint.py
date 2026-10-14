"""Camera pose helpers for the Webots demonstration viewpoints."""

from __future__ import annotations

import math


Vector3 = tuple[float, float, float]
Rotation = tuple[float, float, float, float]


def look_at_orientation(
    camera_position: Vector3,
    target_position: Vector3,
    up_hint: Vector3 = (0.0, 0.0, 1.0),
) -> Rotation:
    """Return a Webots axis-angle rotation whose camera looks at a target."""
    direction = tuple(t - p for p, t in zip(camera_position, target_position))
    forward = _normalise(direction, "camera and target positions must differ")
    up = _normalise(up_hint, "up hint must be non-zero")
    if abs(_dot(forward, up)) > 0.98:
        up = (0.0, 1.0, 0.0)
        if abs(_dot(forward, up)) > 0.98:
            up = (1.0, 0.0, 0.0)

    right = _normalise(_cross(forward, up), "could not derive camera right axis")
    camera_up = _normalise(_cross(tuple(-v for v in forward), right), "could not derive camera up axis")
    backward = tuple(-v for v in forward)

    # The columns are the world-space camera X, Y, and Z axes.
    matrix = (
        (right[0], camera_up[0], backward[0]),
        (right[1], camera_up[1], backward[1]),
        (right[2], camera_up[2], backward[2]),
    )
    quaternion = _quaternion_from_matrix(matrix)
    if quaternion[3] < 0.0:
        quaternion = tuple(-value for value in quaternion)
    w = min(1.0, max(-1.0, quaternion[3]))
    angle = 2.0 * math.acos(w)
    half_sine = math.sqrt(max(0.0, 1.0 - w * w))
    if half_sine < 1e-8:
        return (0.0, 0.0, 1.0, 0.0)
    return (
        quaternion[0] / half_sine,
        quaternion[1] / half_sine,
        quaternion[2] / half_sine,
        angle,
    )


def rotate_vector(vector: Vector3, rotation: Rotation) -> Vector3:
    """Apply a Webots axis-angle rotation to a vector."""
    axis = _normalise(rotation[:3], "rotation axis must be non-zero")
    angle = rotation[3]
    cosine = math.cos(angle)
    sine = math.sin(angle)
    dot = _dot(axis, vector)
    cross = _cross(axis, vector)
    return tuple(
        vector[i] * cosine + cross[i] * sine + axis[i] * dot * (1.0 - cosine)
        for i in range(3)
    )


def _normalise(vector: Vector3, error: str) -> Vector3:
    length = math.sqrt(_dot(vector, vector))
    if length < 1e-12:
        raise ValueError(error)
    return tuple(value / length for value in vector)


def _dot(first: Vector3, second: Vector3) -> float:
    return sum(a * b for a, b in zip(first, second))


def _cross(first: Vector3, second: Vector3) -> Vector3:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _quaternion_from_matrix(matrix: tuple[tuple[float, float, float], ...]) -> tuple[float, float, float, float]:
    trace = matrix[0][0] + matrix[1][1] + matrix[2][2]
    if trace > 0.0:
        scale = math.sqrt(trace + 1.0) * 2.0
        return (
            (matrix[2][1] - matrix[1][2]) / scale,
            (matrix[0][2] - matrix[2][0]) / scale,
            (matrix[1][0] - matrix[0][1]) / scale,
            0.25 * scale,
        )
    if matrix[0][0] > matrix[1][1] and matrix[0][0] > matrix[2][2]:
        scale = math.sqrt(1.0 + matrix[0][0] - matrix[1][1] - matrix[2][2]) * 2.0
        return (
            0.25 * scale,
            (matrix[0][1] + matrix[1][0]) / scale,
            (matrix[0][2] + matrix[2][0]) / scale,
            (matrix[2][1] - matrix[1][2]) / scale,
        )
    if matrix[1][1] > matrix[2][2]:
        scale = math.sqrt(1.0 + matrix[1][1] - matrix[0][0] - matrix[2][2]) * 2.0
        return (
            (matrix[0][1] + matrix[1][0]) / scale,
            0.25 * scale,
            (matrix[1][2] + matrix[2][1]) / scale,
            (matrix[0][2] - matrix[2][0]) / scale,
        )
    scale = math.sqrt(1.0 + matrix[2][2] - matrix[0][0] - matrix[1][1]) * 2.0
    return (
        (matrix[0][2] + matrix[2][0]) / scale,
        (matrix[1][2] + matrix[2][1]) / scale,
        0.25 * scale,
        (matrix[1][0] - matrix[0][1]) / scale,
    )
