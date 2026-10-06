#!/usr/bin/env python3
"""Green-Light Security Raspberry Pi live demo.

This script separates two layers:

1. Raw prototype measurements on Raspberry Pi + ESP32:
   - local truncated-SHA256 tag latency;
   - local Reed-Solomon decode latency using ``reedsolo``;
   - ESP32 serial round-trip latency for the off-path operation.

2. An effective-latency model used to compare a 64 B baseline with
   Green-Light Security (GLS) block sizes.

The default block/parity settings match the configurations reported in the
paper's prototype study:

    64 B -> 16 B parity
   512 B -> 44 B parity
  1024 B -> 52 B parity
  2048 B -> 60 B parity

Important: ``reedsolo`` is a Python software timing proxy. These measurements
are not intended as a cycle-accurate hardware ECC benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import random
import statistics as stats
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    import serial
except ImportError as exc:  # pragma: no cover - dependency error path
    raise SystemExit(
        "Missing dependency 'pyserial'. Install with: pip install -r requirements.txt"
    ) from exc

try:
    import reedsolo
except ImportError as exc:  # pragma: no cover - dependency error path
    raise SystemExit(
        "Missing dependency 'reedsolo'. Install with: pip install -r requirements.txt"
    ) from exc


DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD = 115200
DEFAULT_GLS_BLOCK_SIZES = [512, 1024, 2048]
MAC_TAG_BYTES = 8
RNG_SEED = 42

# Paper-aligned parity settings for the prototype configurations.
PAPER_RS_PARITY_BYTES = {
    64: 16,
    512: 44,
    1024: 52,
    2048: 60,
}

# Defaults carried over from the prototype modeling layer. They transform raw
# Pi/ESP32 measurements into effective architectural latencies; they are not
# additional hardware measurements.
DEFAULT_LOCAL_SCALE = 1000.0
DEFAULT_REMOTE_SCALE = 0.1


def validate_block_sizes(block_sizes: list[int]) -> None:
    unsupported = [b for b in block_sizes if b not in PAPER_RS_PARITY_BYTES]
    if unsupported:
        supported = ", ".join(str(x) for x in sorted(PAPER_RS_PARITY_BYTES))
        raise SystemExit(
            f"Unsupported block size(s): {unsupported}. "
            f"Public paper-aligned configurations are: {supported} B."
        )


def open_serial(port: str, baud: int, timeout: float = 1.0):
    print(f"[INFO] Opening serial port {port} @ {baud} baud")
    ser = serial.Serial(port, baud, timeout=timeout)
    time.sleep(2.0)  # many ESP32 boards reset when the serial port opens
    ser.reset_input_buffer()
    return ser


def measure_remote_latency(ser, n_trials: int) -> tuple[float, float]:
    """Measure ESP32 round-trip latency for the ``ECC`` serial command."""
    print("\n[STEP] Measuring ESP32 off-path round-trip latency")
    samples: list[float] = []

    for i in range(n_trials):
        ser.reset_input_buffer()
        t0 = time.perf_counter()
        ser.write(b"ECC\r\n")
        reply = ser.readline().decode("ascii", errors="ignore").strip()
        t1 = time.perf_counter()

        if not reply:
            raise RuntimeError(
                "No ESP32 reply received. Check the serial port, firmware, and baud rate."
            )

        dt = t1 - t0
        samples.append(dt)
        print(f"  trial {i + 1:02d}: {dt * 1e3:8.3f} ms  reply='{reply}'")

    mean = stats.mean(samples)
    stdev = stats.pstdev(samples) if len(samples) > 1 else 0.0
    print(f"  mean: {mean * 1e3:.3f} ms   std: {stdev * 1e3:.3f} ms")
    return mean, stdev


def measure_tag_latency(block_sizes: list[int], n_iters: int) -> dict[int, float]:
    """Measure 8-byte truncated SHA-256 tag-computation latency."""
    print("\n[STEP] Measuring local 8-byte tag latency")
    results: dict[int, float] = {}

    for block_size in block_sizes:
        data = os.urandom(block_size)
        hashlib.sha256(data).digest()[:MAC_TAG_BYTES]  # warm-up

        t0 = time.perf_counter()
        for _ in range(n_iters):
            hashlib.sha256(data).digest()[:MAC_TAG_BYTES]
        t1 = time.perf_counter()

        mean = (t1 - t0) / n_iters
        results[block_size] = mean
        print(f"  {block_size:4d} B: {mean * 1e6:8.3f} us")

    return results


def _prepare_rs_decode(block_size: int, parity_bytes: int):
    """Prepare a valid codeword once; returned callable times decode only."""
    codec = reedsolo.RSCodec(parity_bytes)
    data = os.urandom(block_size)
    codeword = codec.encode(data)

    def decode_once() -> None:
        codec.decode(codeword)

    return decode_once


def measure_rs_decode_latency(
    block_sizes: list[int], n_trials: int, warmup: int
) -> dict[int, float]:
    """Measure local RS *decode-only* latency for paper configurations."""
    print("\n[STEP] Measuring local RS decode-only latency")
    results: dict[int, float] = {}

    for block_size in block_sizes:
        parity = PAPER_RS_PARITY_BYTES[block_size]
        decode_once = _prepare_rs_decode(block_size, parity)

        for _ in range(warmup):
            decode_once()

        samples: list[float] = []
        for _ in range(n_trials):
            t0 = time.perf_counter()
            decode_once()
            t1 = time.perf_counter()
            samples.append(t1 - t0)

        mean = stats.mean(samples)
        stdev = stats.pstdev(samples) if len(samples) > 1 else 0.0
        results[block_size] = mean
        print(
            f"  {block_size:4d} B, parity={parity:2d} B: "
            f"{mean * 1e3:8.3f} ms (std={stdev * 1e3:.3f} ms)"
        )

    return results


def build_effective_latencies(
    tag_latency: dict[int, float],
    remote_latency: float,
    gls_block_sizes: list[int],
    local_scale: float,
    remote_scale: float,
) -> tuple[dict[int, float], float]:
    """Build the prototype's effective-latency modeling layer."""
    all_sizes = sorted(set([64] + gls_block_sizes))
    ref_size = min(gls_block_sizes) if gls_block_sizes else 64

    base_local = local_scale * tag_latency[ref_size]
    local = {size: base_local for size in all_sizes}
    remote = remote_scale * remote_latency

    print("\n[STEP] Effective modeling latencies")
    print(
        f"  local reference: tag({ref_size} B) x {local_scale:g} "
        f"= {base_local * 1e3:.3f} ms"
    )
    print(
        f"  remote: measured ESP32 RTT x {remote_scale:g} "
        f"= {remote * 1e3:.3f} ms"
    )
    return local, remote


def suggest_alpha_rs(
    local: dict[int, float],
    rs_latency: dict[int, float],
    gls_block_sizes: list[int],
    target_low_error_gain: float,
) -> float:
    """Preserve the original prototype's low-error-gain calibration rule."""
    ref_size = min(gls_block_sizes) if gls_block_sizes else 64
    numerator = target_low_error_gain * local[ref_size] - local[64]
    denominator = rs_latency[64]
    alpha = numerator / denominator if denominator > 0 else 1.0
    return max(alpha, 0.0)


def p_err_from_raw_ber(raw_ber: float, block_size: int) -> float:
    """Paper Eq. (19): p_err(B,p_b)=1-(1-p_b)^[8(B+8)]."""
    total_bits = 8 * (block_size + MAC_TAG_BYTES)
    return 1.0 - (1.0 - raw_ber) ** total_bits


def baseline_latency(
    local: dict[int, float], rs_latency: dict[int, float], alpha_rs: float
) -> float:
    return local[64] + alpha_rs * rs_latency[64]


def gls_expected_latency(
    block_size: int,
    raw_ber: float,
    local: dict[int, float],
    rs_latency: dict[int, float],
    alpha_rs: float,
    remote_effective: float,
) -> tuple[float, float]:
    trigger = p_err_from_raw_ber(raw_ber, block_size)
    latency = local[block_size] + trigger * (
        remote_effective + alpha_rs * rs_latency[block_size]
    )
    return latency, trigger


def simulate_gls_throughput(
    block_size: int,
    raw_ber: float,
    local: dict[int, float],
    rs_latency: dict[int, float],
    alpha_rs: float,
    remote_effective: float,
    n_accesses: int,
    rng: random.Random,
) -> float:
    trigger = p_err_from_raw_ber(raw_ber, block_size)
    slow_extra = remote_effective + alpha_rs * rs_latency[block_size]
    total_time = 0.0

    for _ in range(n_accesses):
        total_time += local[block_size]
        if rng.random() < trigger:
            total_time += slow_extra

    return n_accesses / total_time


def plot_throughput(
    mode: str,
    raw_ber: np.ndarray,
    gls_block_sizes: list[int],
    local: dict[int, float],
    rs_latency: dict[int, float],
    alpha_rs: float,
    remote_effective: float,
    n_accesses: int,
    output: Path | None,
    show: bool,
) -> None:
    base_latency = baseline_latency(local, rs_latency, alpha_rs)
    base_throughput = 1.0 / base_latency

    print(
        f"\n[INFO] Baseline modeled latency: {base_latency * 1e3:.3f} ms; "
        f"throughput={base_throughput:.1f} ops/s"
    )

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.axhline(base_throughput, linestyle="--", label="Baseline (64 B, always RS)")

    rng = random.Random(RNG_SEED)
    for block_size in gls_block_sizes:
        y = []
        for ber in raw_ber:
            if mode == "analytic":
                latency, _ = gls_expected_latency(
                    block_size,
                    float(ber),
                    local,
                    rs_latency,
                    alpha_rs,
                    remote_effective,
                )
                y.append(1.0 / latency)
            else:
                y.append(
                    simulate_gls_throughput(
                        block_size,
                        float(ber),
                        local,
                        rs_latency,
                        alpha_rs,
                        remote_effective,
                        n_accesses,
                        rng,
                    )
                )
        ax.plot(raw_ber, y, marker="o", label=f"GLS ({block_size} B)")

    ax.set_xscale("log")
    ax.set_xlabel("Raw bit-error rate $p_b$")
    ax.set_ylabel("Throughput (1 / modeled latency)")
    ax.set_title("Green-Light Security prototype throughput model")
    ax.grid(True, which="both")
    ax.legend()
    fig.tight_layout()

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=180)
        print(f"[INFO] Saved plot: {output}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["analytic", "simulate"], default="analytic")
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--remote-trials", type=int, default=20)
    parser.add_argument("--tag-iters", type=int, default=2000)
    parser.add_argument("--rs-trials", type=int, default=50)
    parser.add_argument("--rs-warmup", type=int, default=10)
    parser.add_argument(
        "--gls-block-sizes",
        type=int,
        nargs="+",
        default=DEFAULT_GLS_BLOCK_SIZES,
        help="Paper-aligned GLS sizes; default: 512 1024 2048",
    )
    parser.add_argument("--local-scale", type=float, default=DEFAULT_LOCAL_SCALE)
    parser.add_argument("--remote-scale", type=float, default=DEFAULT_REMOTE_SCALE)
    parser.add_argument(
        "--alpha-rs",
        type=float,
        default=None,
        help="RS scaling factor. If omitted, use the original low-error-gain calibration rule.",
    )
    parser.add_argument("--target-low-error-gain", type=float, default=1.5)
    parser.add_argument("--raw-ber-min", type=float, default=1e-9)
    parser.add_argument("--raw-ber-max", type=float, default=1e-5)
    parser.add_argument("--raw-ber-points", type=int, default=10)
    parser.add_argument("--sim-accesses", type=int, default=100000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/prototype_throughput.png"),
        help="Output plot path.",
    )
    parser.add_argument("--no-show", action="store_true", help="Do not open a plot window.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gls_sizes = sorted(set(args.gls_block_sizes))
    all_sizes = sorted(set([64] + gls_sizes))
    validate_block_sizes(all_sizes)

    print("=" * 68)
    print(" Green-Light Security — Raspberry Pi + ESP32 prototype")
    print(" Raw measurements are reported separately from model normalization.")
    print("=" * 68)

    ser = open_serial(args.port, args.baud)
    try:
        remote_mean, _ = measure_remote_latency(ser, args.remote_trials)
    finally:
        ser.close()

    tag_latency = measure_tag_latency(all_sizes, args.tag_iters)
    rs_latency = measure_rs_decode_latency(all_sizes, args.rs_trials, args.rs_warmup)

    print("\n[SUMMARY] Raw measurements")
    print(f"  ESP32 round-trip mean: {remote_mean * 1e3:.3f} ms")
    for size in all_sizes:
        print(
            f"  {size:4d} B: tag={tag_latency[size] * 1e6:.3f} us, "
            f"RS decode={rs_latency[size] * 1e3:.3f} ms"
        )

    local, remote_effective = build_effective_latencies(
        tag_latency,
        remote_mean,
        gls_sizes,
        args.local_scale,
        args.remote_scale,
    )

    alpha_rs = args.alpha_rs
    if alpha_rs is None:
        alpha_rs = suggest_alpha_rs(
            local, rs_latency, gls_sizes, args.target_low_error_gain
        )
        print(f"[INFO] Auto-selected alpha_RS={alpha_rs:.6g}")
    elif alpha_rs < 0:
        raise SystemExit("--alpha-rs must be non-negative")

    raw_ber = np.logspace(
        np.log10(args.raw_ber_min),
        np.log10(args.raw_ber_max),
        num=args.raw_ber_points,
    )

    plot_throughput(
        mode=args.mode,
        raw_ber=raw_ber,
        gls_block_sizes=gls_sizes,
        local=local,
        rs_latency=rs_latency,
        alpha_rs=alpha_rs,
        remote_effective=remote_effective,
        n_accesses=args.sim_accesses,
        output=args.output,
        show=not args.no_show,
    )


if __name__ == "__main__":
    main()
