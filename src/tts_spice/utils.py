import math
from typing import Iterable, Tuple

import numpy as np
import spiceypy as sp


def str2et(time_str: str) -> float:
    """Convert a UTC time string to Ephemeris Time (ET)."""
    return sp.str2et(time_str)


def spkpos(
    target: str,
    et: float,
    frame: str = "J2000",
    observer: str = "NONE",
    abcorr: str = "NONE",
) -> Tuple[np.ndarray, float]:
    """Get the position of a target relative to an observer at a given ET."""
    pos, ltime = sp.spkpos(target, et, frame, abcorr, observer)
    return np.array(pos), ltime


def q2m(q: np.ndarray) -> np.ndarray:
    """Convert a SPICE quaternion [q1, q2, q3, q0] to a rotation matrix."""
    return np.array(sp.q2m(q))


def oco2_quaternion_to_spice(quaternion: Iterable[float]) -> np.ndarray:
    """Convert an OCO-2 ``[x, y, z, w]`` quaternion to SPICE order."""
    q = np.asarray(list(quaternion), dtype=float)
    if q.shape != (4,):
        raise ValueError("OCO-2 quaternions must contain four components")
    return np.array([q[3], -q[0], -q[1], -q[2]])


def target_body_axis_angle(
    target: str,
    utc: str,
    quaternion: Iterable[float],
    latitude_deg: float,
    longitude_deg: float,
    altitude_km: float,
    *,
    body_axis: Iterable[float] = (-1.0, 0.0, 0.0),
    earth_frame: str = "IAU_EARTH",
    inertial_frame: str = "J2000",
    observer: str = "EARTH",
) -> float:
    """Return the angle from a body-frame axis to a SPICE target in degrees.

    The quaternion is the OCO-2 ``QInrToBdy`` telemetry convention. The
    spacecraft position is derived from geodetic latitude, longitude, and
    altitude, and the target position is obtained relative to ``observer``.
    """
    et = str2et(utc)
    radii = sp.bodvrd("EARTH", "RADII", 3)[1]
    ecef = sp.georec(
        math.radians(float(longitude_deg)),
        math.radians(float(latitude_deg)),
        float(altitude_km),
        radii[0],
        (radii[0] - radii[2]) / radii[0],
    )
    earth_to_inertial = sp.pxform(earth_frame, inertial_frame, et)
    spacecraft_position = np.asarray(earth_to_inertial).dot(np.asarray(ecef))
    target_position, _ = spkpos(target, et, inertial_frame, observer=observer)
    target_body = q2m(oco2_quaternion_to_spice(quaternion)).dot(
        target_position - spacecraft_position
    )

    axis = np.asarray(list(body_axis), dtype=float)
    if axis.shape != (3,) or not np.all(np.isfinite(axis)):
        raise ValueError("body_axis must contain three finite components")
    target_norm = np.linalg.norm(target_body)
    axis_norm = np.linalg.norm(axis)
    if target_norm == 0 or axis_norm == 0:
        raise ValueError("target and body axis vectors must be nonzero")
    cosine = np.dot(target_body, axis) / (target_norm * axis_norm)
    return math.degrees(math.acos(float(np.clip(cosine, -1.0, 1.0))))


def kclear() -> None:
    """Unload all SPICE kernels."""
    sp.kclear()
