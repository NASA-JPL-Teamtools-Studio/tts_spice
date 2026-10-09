import numpy as np
import spiceypy as sp
from typing import Union, Tuple

def str2et(time_str: str) -> float:
    """Convert a UTC time string to Ephemeris Time (ET)."""
    return sp.str2et(time_str)

def spkpos(target: str, et: float, frame: str = 'J2000', observer: str = 'NONE', abcorr: str = 'NONE') -> Tuple[np.ndarray, float]:
    """Get the position of a target relative to an observer at a given ET."""
    pos, ltime = sp.spkpos(target, et, frame, abcorr, observer)
    return np.array(pos), ltime

def q2m(q: np.ndarray) -> np.ndarray:
    """Convert a SPICE quaternion [q1, q2, q3, q0] to a rotation matrix."""
    return np.array(sp.q2m(q))

def kclear() -> None:
    """Unload all SPICE kernels."""
    sp.kclear()
