from pathlib import Path
from typing import List, Dict, Optional, Set, Union
import os
import spiceypy as sp
import enum

from tts_utilities.logger import create_logger
from tts_utilities.util import as_list

logger = create_logger(__name__)

# Base path for all SPICE kernels
SPICE_BASE = Path(__file__).parent.joinpath("kernels")

# Track which kernels have been loaded to prevent duplicate loading
_LOADED_KERNELS: Set[str] = set()


class KernelType(enum.Enum):
    """
    Enumeration of different types of SPICE kernels.
    
    These abbreviations correspond to the standard NAIF SPICE kernel types:
    - LSK: Leap Seconds Kernel (time conversion)
    - SPK: Spacecraft Planet Kernel (ephemeris/positions)
    - PCK: Planetary Constants Kernel (body size, shape, orientation)
    - IK:  Instrument Kernel (field-of-view, mounting alignment)
    - FK:  Frames Kernel (reference frame definitions)
    - EK:  Events Kernel (mission events)
    - SCLK: Spacecraft Clock Kernel (time correlation)
    - DSK: Digital Shape Kernel (topography)
    - MK:  Meta-Kernel (lists other kernels to load)
    """
    LEAP_SECONDS = "LSK"
    EPHEMERIS = "SPK"
    ORIENTATION = "PCK"
    INSTRUMENT = "IK"
    FRAME = "FK"
    EVENTS = "EK"
    SPACECRAFT_CLOCK = "SCLK"
    DSK = "DSK"
    META = "MK"


class KernelRegistry:
    """
    Registry of available SPICE kernels organized by type and body.
    
    This class acts as a catalog, mapping abstract requests (e.g., "Earth orientation")
    to concrete filenames located in the SPICE_BASE directory.
    """
    
    # Standard kernels that should be available in the package
    STANDARD_KERNELS = {
        KernelType.LEAP_SECONDS: ["naif0012.tls"],
        KernelType.EPHEMERIS: ["de430.bsp"],
        KernelType.ORIENTATION: ["pck00010.tpc"],
    }
    
    # Body-specific kernels
    BODY_KERNELS = {
        "earth": {
            KernelType.ORIENTATION: ["earth_latest_high_prec.bpc"],
        },
        "moon": {
            KernelType.ORIENTATION: ["moon_pa_de421_1900-2050.bpc"],
        },
        # Add more bodies as needed
    }
    
    @classmethod
    def get_kernel_path(cls, kernel_name: str) -> Path:
        """
        Get the absolute path to a kernel file.
        
        Args:
            kernel_name: The filename of the kernel (e.g., "de430.bsp").
            
        Returns:
            Path: The full PosixPath to the kernel file.
        """
        return SPICE_BASE.joinpath(kernel_name)
    
    @classmethod
    def get_standard_kernels(cls, kernel_type: KernelType) -> List[Path]:
        """
        Get paths to all standard kernels of a specific type.
        
        Standard kernels are those used for general solar system calculations,
        such as generic planetary ephemerides (DE4xx) or leap seconds (LSK).
        
        Args:
            kernel_type: The category of kernel requested.
            
        Returns:
            List[Path]: A list of full paths to the matching kernels.
        """
        if kernel_type not in cls.STANDARD_KERNELS:
            return []
        
        return [cls.get_kernel_path(k) for k in cls.STANDARD_KERNELS[kernel_type]]
    
    @classmethod
    def get_body_kernels(cls, body: str, kernel_type: Optional[KernelType] = None) -> List[Path]:
        """
        Get paths to all kernels for a specific body, optionally filtered by type.
        
        Args:
            body: The name of the celestial body (e.g., 'earth', 'moon'). Case-insensitive.
            kernel_type: If provided, only returns kernels of this specific type.
                         If None, returns all known kernels for that body.
                         
        Returns:
            List[Path]: A list of full paths to the matching kernels.
        """
        body = body.lower()
        if body not in cls.BODY_KERNELS:
            logger.warning(f"No kernels registered for body: {body}")
            return []
        
        if kernel_type is None:
            # Return all kernel types for this body
            result = []
            for type_kernels in cls.BODY_KERNELS[body].values():
                result.extend([cls.get_kernel_path(k) for k in type_kernels])
            return result
        
        if kernel_type not in cls.BODY_KERNELS[body]:
            return []
            
        return [cls.get_kernel_path(k) for k in cls.BODY_KERNELS[body][kernel_type]]


def furnish_kernel(kernel_path: Union[str, Path]) -> None:
    """
    Load a single SPICE kernel into the CSPICE runtime.
    
    This function wraps `spiceypy.furnsh()` with tracking to prevent 
    duplicate loads and error handling for missing files.
    
    Args:
        kernel_path: The full path to the kernel file.
        
    Raises:
        FileNotFoundError: If the kernel file does not exist.
        Exception: If SPICE fails to load the kernel (e.g., corrupt file).
    """
    kernel_path_str = str(kernel_path)
    if kernel_path_str in _LOADED_KERNELS:
        return
    
    if not os.path.exists(kernel_path):
        raise FileNotFoundError(f"SPICE kernel not found: {kernel_path}")
    
    try:
        sp.furnsh(kernel_path_str)
        _LOADED_KERNELS.add(kernel_path_str)
        logger.info(f"Loaded SPICE kernel: {kernel_path_str}")
    except Exception as e:
        logger.error(f"Failed to load SPICE kernel {kernel_path_str}: {e}")
        raise


def furnish_kernels(kernel_paths: List[Union[str, Path]]) -> None:
    """
    Load a list of SPICE kernels.
    
    Args:
        kernel_paths: A list of paths to kernel files to load.
    """
    for kernel_path in kernel_paths:
        furnish_kernel(kernel_path)


def clear_kernels() -> None:
    """
    Unload all SPICE kernels from the CSPICE runtime.
    
    This wraps `spiceypy.kclear()`. It resets the internal kernel pool
    and clears the local `_LOADED_KERNELS` tracking set.
    """
    sp.kclear()
    _LOADED_KERNELS.clear()
    logger.info("All SPICE kernels unloaded")


def leap_seconds() -> None:
    """
    Load the standard Leap Seconds Kernel (LSK).
    
    This is required for converting between UTC and Ephemeris Time (ET/TDB).
    Without this, time conversions will fail.
    """
    kernels = KernelRegistry.get_standard_kernels(KernelType.LEAP_SECONDS)
    furnish_kernels(kernels)


def planetary_ephemerides() -> None:
    """
    Load standard Planetary Ephemeris Kernels (SPK).
    
    These kernels (e.g., DE430, DE440) contain the positions and velocities
    of major solar system bodies (sun, planets, moon) relative to the 
    solar system barycenter.
    """
    kernels = KernelRegistry.get_standard_kernels(KernelType.EPHEMERIS)
    furnish_kernels(kernels)


def planetary_constants() -> None:
    """
    Load standard Planetary Constants Kernels (PCK).
    
    These text kernels (e.g., pck00010.tpc) define the size, shape (radii),
    and orientation models for planets and satellites.
    """
    kernels = KernelRegistry.get_standard_kernels(KernelType.ORIENTATION)
    furnish_kernels(kernels)


def rotation_kernels(bodies: Union[str, List[str]]) -> None:
    """
    Load high-precision rotation kernels for specified bodies.
    
    These are typically binary PCK files that provide more accurate 
    orientation data than the generic text PCK files.
    
    Args:
        bodies: A single body name (str) or list of names (List[str]).
                
    Raises:
        ValueError: If a requested body does not have rotation kernels registered.
    """
    if not bodies:
        logger.warning("No bodies specified for rotation kernels")
        return

    bodies = as_list(bodies)    
    available_bodies = set(KernelRegistry.BODY_KERNELS.keys())
    requested_bodies = set(b.lower() for b in bodies)
    
    # Check for unsupported bodies
    unsupported = requested_bodies - available_bodies
    if unsupported:
        raise ValueError(f"Rotation kernels not available for: {', '.join(unsupported)}")
    
    # Load kernels for each requested body
    for body in requested_bodies:
        body_kernels = KernelRegistry.get_body_kernels(body, KernelType.ORIENTATION)
        furnish_kernels(body_kernels)

def mission_kernels(mission_name: str) -> None:
    """
    Load SPICE kernels for a specific space mission.
    
    This attempts to locate a directory in `kernels/missions/{mission_name}`.
    It prioritizes loading a meta-kernel (*.tm) if one exists. If not, it falls
    back to loading all kernel files in that directory matching the glob `*.????`.
    
    Args:
        mission_name: The name of the mission subdirectory (e.g., 'cassini', 'juno').
        
    Raises:
        FileNotFoundError: If the mission directory does not exist.
    """
    # This is a placeholder for mission-specific setup
    # In a real implementation, this would load mission-specific kernels
    # based on a configuration or convention
    
    # Example implementation:
    mission_dir = SPICE_BASE.joinpath(f"missions/{mission_name}")
    
    if not mission_dir.exists():
        raise FileNotFoundError(f"Mission kernels not found for: {mission_name}")
    
    # Load a mission meta-kernel if available
    meta_kernel = mission_dir.joinpath(f"{mission_name}.tm")
    if meta_kernel.exists():
        furnish_kernel(meta_kernel)
        return
    
    # Otherwise load individual kernels based on a convention
    # This is just an example - actual implementation would depend on your needs
    mission_kernels = list(mission_dir.glob("*.????"))
    furnish_kernels(mission_kernels)