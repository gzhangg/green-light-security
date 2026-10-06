#!/usr/bin/env python3
"""Simple Raspberry Pi -> ESP32 serial round-trip diagnostic."""

from __future__ import annotations

import argparse
import time

try:
    import serial
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency 'pyserial'. Install with: pip install -r requirements.txt"
    ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument(
        "--delays-us",
        type=int,
        nargs="+",
        default=[100, 500, 1000, 5000],
        help="ESP32 diagnostic delay values sent with PING_US.",
    )
    parser.add_argument("--timeout", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ser = serial.Serial(args.port, args.baud, timeout=args.timeout)
    try:
        time.sleep(2.0)
        ser.reset_input_buffer()

        for delay_us in args.delays_us:
            ser.reset_input_buffer()
            command = f"PING_US {delay_us}\r\n".encode("ascii")
            t0 = time.perf_counter()
            ser.write(command)
            reply = ser.readline().decode("ascii", errors="ignore").strip()
            t1 = time.perf_counter()

            if not reply:
                print(f"PING_US {delay_us}: timeout / empty reply")
                continue

            rtt_us = (t1 - t0) * 1_000_000.0
            print(
                f"PING_US {delay_us:5d} -> '{reply}' | "
                f"host RTT = {rtt_us:10.1f} us"
            )
    finally:
        ser.close()


if __name__ == "__main__":
    main()
