# Green-Light Security for AI Computing

**Toward secure, energy-efficient, and sustainable AI infrastructure**

[Research page](https://gzhangg.github.io/green-light.html) ·
[Paper](paper/Green_Light_Security_for_AI_Computing.pdf)

Green-Light Security explores how protection mechanisms can be reorganized
so that computing systems do not pay the full cost of expensive protection
on every operation.

The central idea is simple:

> Keep lightweight protection continuously on the common path, while
> invoking expensive corrective work only when it is actually needed.

The project combines mathematical modeling, simulation, optimization, and
a Raspberry Pi 5 / ESP32 hardware prototype.

---

## Motivation

AI systems move enormous volumes of data, making memory bandwidth,
capacity, and energy first-order system constraints.

Traditional protection mechanisms impose recurring overhead on every
memory access. Green-Light Security asks whether reliability and integrity
can instead be organized according to how frequently their work is needed.

The proposed architecture keeps integrity verification on the fast path
while moving expensive reliability correction to an off-path tier.

---

## Research components

### 1. Mathematical model

The analytical framework studies the interaction among:

- protection granularity
- ECC redundancy
- integrity metadata
- raw bit-error rate
- decoding throughput
- off-path bandwidth
- memory cost
- effective throughput

The model identifies operating regions in which strong protection can be
maintained without allowing correction work to throttle the common path.

### 2. Simulation and optimization

The simulation explores how the preferred protection granularity changes
with reliability conditions, decoder capability, and off-path bandwidth.

### 3. Hardware prototype

A Raspberry Pi 5 represents the fast tier and executes the experiment under
Linux using Python.

An ESP32 provides a physically separate external path used to emulate the
latency of reaching an off-path reliability resource.

The prototype is an architectural emulation rather than a production HBM
or hardware-ECC implementation.

See [`hardware/`](hardware/) for details.

---

## Repository structure

```text
green-light-security/
├── README.md
├── LICENSE
├── CITATION.cff
├── requirements.txt
├── paper/
├── raspberry-pi/
├── hardware/
└── results/
