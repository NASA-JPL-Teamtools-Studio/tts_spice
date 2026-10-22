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


def target_body_axis_angles(
    target: str,
    ets: Iterable[float],
    quaternions: Iterable[Iterable[float]],
    latitudes_deg: Iterable[float],
    longitudes_deg: Iterable[float],
    altitudes_km: Iterable[float],
    *,
    body_axis: Iterable[float] = (-1.0, 0.0, 0.0),
    earth_frame: str = "IAU_EARTH",
    inertial_frame: str = "J2000",
    observer: str = "EARTH",
) -> np.ndarray:
    """Return target-to-body-axis angles for a batch of epochs in degrees.

    This keeps the expensive SPK target lookup vectorized and evaluates the
    attitude/frame transforms once per requested sample. Inputs use the
    OCO-2 ``QInrToBdy`` quaternion convention and geodetic altitude in km.
    """
    ets = np.asarray(list(ets), dtype=float)
    quaternions = np.asarray(list(quaternions), dtype=float)
    latitudes_deg = np.asarray(list(latitudes_deg), dtype=float)
    longitudes_deg = np.asarray(list(longitudes_deg), dtype=float)
    altitudes_km = np.asarray(list(altitudes_km), dtype=float)
    if ets.ndim != 1:
        raise ValueError("ets must be one-dimensional")
    count = len(ets)
    if quaternions.shape != (count, 4):
        raise ValueError("quaternions must have shape (N, 4)")
    if any(values.shape != (count,) for values in (latitudes_deg, longitudes_deg, altitudes_km)):
        raise ValueError("position arrays must have shape (N,)")

    axis = np.asarray(list(body_axis), dtype=float)
    if axis.shape != (3,) or not np.all(np.isfinite(axis)):
        raise ValueError("body_axis must contain three finite components")
    axis_norm = np.linalg.norm(axis)
    if axis_norm == 0:
        raise ValueError("body axis vector must be nonzero")
    axis = axis / axis_norm

    radii = sp.bodvrd("EARTH", "RADII", 3)[1]
    latitudes = np.deg2rad(latitudes_deg)
    longitudes = np.deg2rad(longitudes_deg)
    eccentricity_squared = (radii[0] ** 2 - radii[2] ** 2) / radii[0] ** 2
    prime_vertical_radius = radii[0] / np.sqrt(1.0 - eccentricity_squared * np.sin(latitudes) ** 2)
    ecef = np.column_stack((
        (prime_vertical_radius + altitudes_km) * np.cos(latitudes) * np.cos(longitudes),
        (prime_vertical_radius + altitudes_km) * np.cos(latitudes) * np.sin(longitudes),
        (prime_vertical_radius * (1.0 - eccentricity_squared) + altitudes_km) * np.sin(latitudes),
    ))

    target_positions, _ = sp.spkpos(target, ets, inertial_frame, "NONE", observer)
    target_positions = np.asarray(target_positions, dtype=float)
    spacecraft_positions = np.empty_like(ecef)
    target_body = np.empty_like(ecef)
    for index, et in enumerate(ets):
        earth_to_inertial = np.asarray(sp.pxform(earth_frame, inertial_frame, float(et)))
        spacecraft_positions[index] = earth_to_inertial.dot(ecef[index])
        target_body[index] = q2m(oco2_quaternion_to_spice(quaternions[index])).dot(
            target_positions[index] - spacecraft_positions[index]
        )

    target_norms = np.linalg.norm(target_body, axis=1)
    if np.any(target_norms == 0):
        raise ValueError("target vectors must be nonzero")
    cosine = np.sum(target_body * axis, axis=1) / target_norms
    return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))


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
    """Return the angle from a body-frame axis to a SPICE target in degrees."""
    angle = target_body_axis_angles(
        target,
        [str2et(utc)],
        [quaternion],
        [latitude_deg],
        [longitude_deg],
        [altitude_km],
        body_axis=body_axis,
        earth_frame=earth_frame,
        inertial_frame=inertial_frame,
        observer=observer,
    )
    return float(angle[0])


def kclear() -> None:
    """Unload all SPICE kernels."""
    sp.kclear()
