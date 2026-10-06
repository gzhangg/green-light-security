# Public code release notes

This repository package is a cleaned public release derived from the original Raspberry Pi prototype scripts used during the Green-Light Security project.

## Changes made for the public release

- Renamed the main scripts to describe their roles clearly.
- Removed macOS metadata files from the source archive.
- Omitted `simple_gls_live_demo.py`, an earlier exploratory script that is not part of the final public workflow.
- Updated the paper-aligned prototype configurations to:
  - 64 B data / 16 B parity
  - 512 B data / 44 B parity
  - 1024 B data / 52 B parity
  - 2048 B data / 60 B parity
- Added the 2048 B configuration to the standalone local-latency measurement script.
- Changed the main RS timing path so that codeword encoding and setup occur before the timed region; the reported measurement is decode-only.
- Removed the dummy CPU-loop fallback for missing `reedsolo`. The scripts now fail clearly if a required dependency is absent.
- Added command-line controls for the serial port, modeling scale factors, simulation size, and plot output.
- Added explicit separation in the console output and documentation between raw hardware measurements and effective modeling latencies.
- Added README, hardware protocol documentation, dependency list, citation metadata, and code license.

These cleanup changes improve clarity and alignment with the final manuscript; they do not turn the Raspberry Pi/ESP32 prototype into a production hardware implementation.
