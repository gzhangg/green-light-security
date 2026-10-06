# Raspberry Pi prototype code

This directory contains the cleaned Raspberry Pi side of the Green-Light Security hardware prototype.

## Scripts

### `run_hardware_demo.py`

Main live demo. It:

1. measures ESP32 serial round-trip latency for the off-path operation;
2. measures local 8-byte truncated SHA-256 tag latency;
3. measures software RS **decode-only** latency;
4. reports the raw measurements before applying any model normalization; and
5. generates analytical or Monte Carlo prototype throughput curves versus raw bit-error rate.

Example:

```bash
python raspberry-pi/run_hardware_demo.py \
  --mode analytic \
  --port /dev/ttyUSB0 \
  --output results/prototype_throughput.png \
  --no-show
```

The default GLS block sizes are 512 B, 1024 B, and 2048 B. The 64 B baseline is measured automatically.

### `measure_local_latency.py`

Standalone Raspberry Pi timing utility for the four configurations reported in the paper:

| User-data block | RS parity parameter |
|---:|---:|
| 64 B | 16 B |
| 512 B | 44 B |
| 1024 B | 52 B |
| 2048 B | 60 B |

Example:

```bash
python raspberry-pi/measure_local_latency.py \
  --csv results/local_latency.csv
```

RS encoding / codeword construction happens before timing; the reported RS measurement times decoding only.

### `serial_latency_probe.py`

Small diagnostic tool for the ESP32 `PING_US` command.

```bash
python raspberry-pi/serial_latency_probe.py --port /dev/ttyUSB0
```

## ESP32 protocol

The main demo expects the ESP32 to accept a newline-terminated command:

```text
ECC
```

and return one newline-terminated response.

The diagnostic probe expects:

```text
PING_US <delay_us>
```

and one newline-terminated response.

## Measurement vs. modeling

The scripts print **raw Pi/ESP32 measurements first**. The main demo then constructs effective modeling latencies using:

- `--local-scale` (default `1000`), applied to the measured local tag latency;
- `--remote-scale` (default `0.1`), applied to the measured ESP32 round-trip latency; and
- `--alpha-rs`, applied uniformly to measured RS decode latency.

These scale factors are modeling parameters used by the prototype demonstration. They are not additional hardware measurements.

If `--alpha-rs` is omitted, the script preserves the original prototype calibration rule that chooses a value corresponding to a configurable low-error target gain (`--target-low-error-gain`, default `1.5`). For a fixed public run, pass `--alpha-rs` explicitly and record the command line.

## Trigger probability

For a block of `B` user-data bytes and an 8-byte tag, the prototype uses the paper's trigger model:

```text
p_err(B, p_b) = 1 - (1 - p_b) ** (8 * (B + 8))
```

## Important scope note

The prototype does **not** implement production HBM security hardware. The Raspberry Pi and ESP32 emulate the architectural separation between a fast in-path operation and a slower off-path recovery operation. Likewise, `reedsolo` is a Python software timing proxy; for long inputs it may internally chunk data into multiple codewords. Do not interpret these measurements as cycle-accurate hardware-decoder results.
