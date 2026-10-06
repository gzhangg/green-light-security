# Green-Light Security for AI Computing

**Gianna Zhang**  
Research site: <https://gzhangg.github.io/green-light.html>

Green-Light Security studies a progressive-protection architecture for AI memory systems: lightweight integrity verification remains on the common path, while more expensive reliability correction is invoked only when needed. The project combines mathematical modeling, simulation, and a compact Raspberry Pi + ESP32 prototype.

This public package contains the paper and a cleaned release of the **Raspberry Pi side of the hardware prototype**. The code is organized to make a clear distinction between:

1. **raw measurements** taken on the Raspberry Pi / ESP32 setup; and
2. **effective modeling latencies** used by the prototype throughput model.

## Repository contents

```text
green-light-security/
├── README.md
├── LICENSE
├── CITATION.cff
├── requirements.txt
├── paper/
│   └── Green_Light_Security_for_AI_Computing.pdf
├── raspberry-pi/
│   ├── README.md
│   ├── run_hardware_demo.py
│   ├── measure_local_latency.py
│   └── serial_latency_probe.py
├── hardware/
│   └── README.md
└── results/
    └── README.md
```

## Quick start on Raspberry Pi

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

With the ESP32 connected over USB serial (default `/dev/ttyUSB0`):

```bash
python raspberry-pi/run_hardware_demo.py --mode analytic
```

See [`raspberry-pi/README.md`](raspberry-pi/README.md) for the serial protocol, measurement procedure, configuration, and reproducibility notes.

## Public-release cleanup

The Raspberry Pi scripts in this repository are a curated public release of the original prototype code. The cleanup intentionally:

- uses the four block sizes reported in the paper's prototype study: **64 B, 512 B, 1024 B, and 2048 B**;
- uses the corresponding paper parity settings **16 B, 44 B, 52 B, and 60 B**;
- times **RS decoding only** (encoding and codeword preparation occur outside the timed region);
- removes the old dummy-loop fallback when `reedsolo` is unavailable;
- keeps raw hardware timing separate from modeling-scale parameters; and
- removes earlier exploratory scripts that are not part of the final public workflow.

## Scope of the prototype

The prototype is an architectural demonstration, not a production HBM security implementation. The Raspberry Pi represents the fast tier and performs the local integrity-tag computation / verification proxy. The ESP32 represents an off-path reliability tier and is contacted through a simple serial protocol when recovery is invoked.

The Python `reedsolo` implementation is used as a software timing proxy for local RS decoding. In particular, long inputs may be internally chunked by the library; these timings should not be interpreted as a hardware-decoder benchmark or as a cycle-accurate implementation of the paper's memory ECC.

## Paper and figures

The research paper is included under [`paper/`](paper/). The MIT license in this repository applies to the **source code**. The paper, text, and figures remain © Gianna Zhang unless otherwise noted.
