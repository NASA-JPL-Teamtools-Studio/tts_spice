import pytest
import spiceypy as sp
from pathlib import Path
import os

# Import the module under test
from tts_spice import furnish

# --- FIXTURES ---

@pytest.fixture(autouse=True)
def clean_spice_state():
    """
    Runs before and after every test.
    Ensures the SPICE runtime and the module's internal tracking set 
    are completely cleared so tests don't interfere with each other.
    """
    # Teardown any existing state
    sp.kclear()
    furnish._LOADED_KERNELS.clear()
    
    yield
    
    # Clean up after test finishes
    sp.kclear()
    furnish._LOADED_KERNELS.clear()

# --- 1. REGISTRY & FILE EXISTENCE TESTS ---

def test_kernel_paths_exist_on_disk():
    """
    Since we are running with real kernels, verify that the 
    paths defined in KernelRegistry actually resolve to real files.
    """
    # Check Standard Kernels
    for k_type in furnish.KernelRegistry.STANDARD_KERNELS:
        paths = furnish.KernelRegistry.get_standard_kernels(k_type)
        for p in paths:
            assert p.exists(), f"Standard kernel missing on disk: {p}"

    # Check Body Kernels (Earth)
    earth_kernels = furnish.KernelRegistry.get_body_kernels("earth")
    for p in earth_kernels:
        assert p.exists(), f"Earth kernel missing on disk: {p}"

def test_registry_retrieval():
    """Test that the registry returns the correct path objects."""
    lsk = furnish.KernelRegistry.get_standard_kernels(furnish.KernelType.LEAP_SECONDS)
    assert len(lsk) > 0
    assert lsk[0].name == "naif0012.tls"
    assert isinstance(lsk[0], Path)

# --- 2. LOADING TESTS (INTEGRATION WITH SPICE) ---

def test_furnish_kernel_loads_into_spice():
    """
    Test loading a single kernel.
    We verify success by asking SPICE (ktotal) if the kernel count increased.
    """
    # 1. Get a path to a real kernel (Leap Seconds)
    lsk_path = furnish.KernelRegistry.get_standard_kernels(furnish.KernelType.LEAP_SECONDS)[0]
    
    # 2. Ensure SPICE is empty initially
    assert sp.ktotal("ALL") == 0
    
    # 3. Load it
    furnish.furnish_kernel(lsk_path)
    
    # 4. Verify loaded in SPICE runtime
    assert sp.ktotal("ALL") == 1
    
    # 5. Verify loaded in module tracking
    assert str(lsk_path) in furnish._LOADED_KERNELS

def test_furnish_kernel_prevents_duplicates():
    """
    Test that calling furnish_kernel twice on the same file 
    doesn't raise an error and doesn't load it into SPICE twice.
    """
    lsk_path = furnish.KernelRegistry.get_standard_kernels(furnish.KernelType.LEAP_SECONDS)[0]
    
    furnish.furnish_kernel(lsk_path)
    assert sp.ktotal("ALL") == 1
    
    # Attempt to load again
    furnish.furnish_kernel(lsk_path)
    
    # SPICE count should still be 1 (or SPICE would handle it, 
    # but our module specifically prevents the call)
    assert sp.ktotal("ALL") == 1

def test_furnish_nonexistent_file():
    """Test that trying to load a fake file raises FileNotFoundError."""
    fake_path = Path("this_does_not_exist.bsp")
    
    with pytest.raises(FileNotFoundError):
        furnish.furnish_kernel(fake_path)

def test_clear_kernels_unloads_spice():
    """Test that clear_kernels() actually wipes the SPICE runtime."""
    # Load a kernel
    furnish.leap_seconds()
    assert sp.ktotal("ALL") > 0
    assert len(furnish._LOADED_KERNELS) > 0
    
    # Clear
    furnish.clear_kernels()
    
    # Verify empty
    assert sp.ktotal("ALL") == 0
    assert len(furnish._LOADED_KERNELS) == 0

# --- 3. HELPER FUNCTION TESTS ---

def test_leap_seconds_helper():
    """Test the leap_seconds() shortcut."""
    furnish.leap_seconds()
    
    # Check that a text kernel was loaded
    assert sp.ktotal("TEXT") >= 1
    
    # Double check the specific file is tracked
    lsk_name = "naif0012.tls"
    assert any(lsk_name in str(k) for k in furnish._LOADED_KERNELS)

def test_planetary_ephemerides_helper():
    """Test the planetary_ephemerides() shortcut."""
    furnish.planetary_ephemerides()
    
    # Check that an SPK (ephemeris) file was loaded
    assert sp.ktotal("SPK") >= 1

def test_rotation_kernels_valid_body():
    """Test loading rotation kernels for Earth."""
    furnish.rotation_kernels("Earth")
    
    # This usually loads a PCK (Planetary Constants Kernel)
    # Depending on the file type (binary or text), it counts as PCK or TEXT
    assert sp.ktotal("ALL") >= 1
    
    # Verify the tracking set has the earth file
    assert any("earth" in str(k).lower() for k in furnish._LOADED_KERNELS)

def test_rotation_kernels_unsupported_body():
    """Test that asking for an unsupported body raises ValueError."""
    with pytest.raises(ValueError) as e:
        furnish.rotation_kernels(["Pluto", "Mars"]) # Assuming these aren't in your BODY_KERNELS dict
    
    assert "Rotation kernels not available" in str(e.value)

# --- 4. MISSION KERNEL TESTS ---

def test_mission_kernels_missing_directory():
    """
    Since we don't know exactly which mission folders you have,
    we test the error case. We ask for a mission that definitely 
    doesn't exist to verify the directory check logic works.
    """
    fake_mission = "fake_mission_123"
    
    with pytest.raises(FileNotFoundError) as e:
        furnish.mission_kernels(fake_mission)
    
    assert f"Mission kernels not found for: {fake_mission}" in str(e.value)
