#!/usr/bin/env python3
"""Measure Raspberry Pi local tag and Reed-Solomon decode latency.

The default configurations match the four prototype block sizes reported in
Green-Light Security for AI Computing. RS codewords are prepared before the
timed region so the RS measurement is decode-only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import statistics
import time
from pathlib import Path

try:
    from reedsolo import RSCodec
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency 'reedsolo'. Install with: pip install -r requirements.txt"
    ) from exc


CONFIGS = [
    (64, 16),
    (512, 44),
    (1024, 52),
    (2048, 60),
]
MAC_TAG_BYTES = 8


def timed_mean_us(func, iterations: int) -> float:
    t0 = time.perf_counter()
    for _ in range(iterations):
        func()
    t1 = time.perf_counter()
    return (t1 - t0) / iterations * 1e6


def repeated_stats(func, iterations: int, repeats: int) -> tuple[float, float]:
    samples = [timed_mean_us(func, iterations) for _ in range(repeats)]
    return statistics.mean(samples), statistics.pstdev(samples)


def measure_configuration(
    data_len: int,
    parity_bytes: int,
    warmup: int,
    rs_iters: int,
    tag_iters: int,
    repeats: int,
) -> dict[str, float | int]:
    data = os.urandom(data_len)

    codec = RSCodec(parity_bytes)
    codeword = codec.encode(data)

    def rs_decode_once() -> None:
        codec.decode(codeword)

    def tag_once() -> None:
        hashlib.sha256(data).digest()[:MAC_TAG_BYTES]

    for _ in range(warmup):
        rs_decode_once()
        tag_once()

    rs_mean, rs_std = repeated_stats(rs_decode_once, rs_iters, repeats)
    tag_mean, tag_std = repeated_stats(tag_once, tag_iters, repeats)

    return {
        "block_bytes": data_len,
        "parity_bytes": parity_bytes,
        "rs_decode_mean_us": rs_mean,
        "rs_decode_std_us": rs_std,
        "tag_mean_us": tag_mean,
        "tag_std_us": tag_std,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warmup", type=int, default=50)
    parser.add_argument("--rs-iters", type=int, default=200)
    parser.add_argument("--tag-iters", type=int, default=2000)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--csv", type=Path, default=None, help="Optional CSV output path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = []

    print("Green-Light Security — local Raspberry Pi latency measurement")
    print("RS timing is decode-only; tag timing is 8-byte truncated SHA-256.\n")

    for data_len, parity_bytes in CONFIGS:
        row = measure_configuration(
            data_len,
            parity_bytes,
            args.warmup,
            args.rs_iters,
            args.tag_iters,
            args.repeats,
        )
        rows.append(row)
        print(
            f"{data_len:4d} B | parity {parity_bytes:2d} B | "
            f"RS {row['rs_decode_mean_us']:9.2f} ± {row['rs_decode_std_us']:.2f} us | "
            f"tag {row['tag_mean_us']:8.3f} ± {row['tag_std_us']:.3f} us"
        )

    if args.csv is not None:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nSaved: {args.csv}")


if __name__ == "__main__":
    main()
