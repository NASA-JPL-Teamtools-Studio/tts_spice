# TTS Spice

![Project logo](https://github.com/NASA-JPL-Teamtools-Studio/teamtools_documentation/blob/main/docs/images/tts_image_artifacts/tts_starter_template.png)

## About Teamtools Studio

Teamtools Studio Utilities is part of JPL's Teamtools Studio (TTS).

TTS is an effort originated in JPL's Planning and Execution section to centralize shared repositories across missions. This benefits JPL by reducing cost through reducing duplicated code, collaborating across missions, and unifying standards for development and design across JPL.

Although Planning and Execution is primarily concerned with flight operations, the TTS suite has been generalized and atomized to the point where many of these tools are applicable during other mission phases and even in non-spaceflight contexts. Through our work flying space missions, we hope to provide tools to the open source community that have utility in data analysis or planning for any complex system where failure is not an option.

For more infomation on how to contribute, and how these libraries form a complete ecosystem for high reliability data analysis, see the [Full TTS Documentation](https://nasa-jpl-teamtools-studio.github.io/teamtools_documentation/).

## What is TTS Spice?

### Overview

TTS Spice is a library that provides a clean, organized approach to SPICE kernel management. As we developed the Teamtools Studio suite, we found ourselves needing to put kernels in every repository, leading to duplication and inconsistency. This library centralizes kernel management, allowing the TTS team to manage which kernels are used and update them in a single place when new ones are released.

The library provides:

- A structured way to organize SPICE kernels by type and celestial body
- Functions to load standard kernels (leap seconds, planetary ephemerides, etc.)
- Body-specific kernel loading (Earth, Moon, etc.)
- Mission-specific kernel setup
- Kernel tracking to prevent duplicate loading
- Clean error handling and logging

### Features

- **Organized Kernel Management**: Kernels are organized by type (LSK, SPK, PCK, etc.) and by celestial body
- **Standard Kernel Loading**: Easy loading of commonly used kernels
- **Body-Specific Kernels**: Load rotation models and other kernels for specific bodies
- **Mission Setup**: Configure SPICE for specific missions with a single function call
- **Duplicate Prevention**: Automatically tracks loaded kernels to prevent duplicates
- **Error Handling**: Proper error handling and logging for kernel loading issues

### Usage Examples

```python
# Load standard kernels (leap seconds, planetary ephemerides, constants)
from tts_spice import standard_kernels, rotation_kernels, clear_kernels

# Load the basic kernels needed for most operations
standard_kernels()

# Load Earth and Moon rotation kernels
rotation_kernels(["earth", "moon"])

# Use SPICE functions as normal
import spiceypy as sp
et = sp.str2et("2026-01-17")
position, _ = sp.spkpos("EARTH", et, "J2000", "NONE", "SUN")

# Always clean up when done
clear_kernels()
```

### Available Kernels

The library includes these standard kernels:

- **Leap Seconds**: `naif0012.tls`
- **Planetary Ephemerides**: `de430.bsp`
- **Planetary Constants**: `pck00010.tpc`

Body-specific kernels:

- **Earth**: `earth_latest_high_prec.bpc`
- **Moon**: `moon_pa_de421_1900-2050.bpc`

### TTS dependencies

* TTS Utilities

## Extending the Library

### Adding New Kernels

To add new kernels to the library:

1. Place the kernel file in the `tts_spice/kernels/` directory
2. Update the `KernelRegistry` class in `furnish.py` to include the new kernel

For mission-specific kernels, create a subdirectory in `tts_spice/kernels/missions/mission_name/`

### Recommended Additional Kernels

Depending on your mission needs, you might want to add:

- Higher precision ephemerides (e.g., `de440.bsp` or `de441.bsp`)
- Additional planetary rotation models
- Spacecraft-specific kernels
- DSK (shape) kernels for small bodies
- Instrument kernels for specific missions
