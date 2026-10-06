# Hardware prototype

The prototype uses:

- **Raspberry Pi 5** — fast-tier host; performs local tag work and software RS decoding measurements.
- **ESP32** — off-path tier; responds to serial requests used to measure remote round-trip latency.
- **USB serial connection** — default host device path `/dev/ttyUSB0`, default baud rate `115200`.

## Serial protocol expected by the Raspberry Pi scripts

`run_hardware_demo.py` expects the ESP32 to accept:

```text
ECC
```

and return one newline-terminated response after the ESP32-side emulated off-path operation.

`serial_latency_probe.py` expects the diagnostic command:

```text
PING_US <delay_us>
```

and one newline-terminated response.

The ESP32 firmware is not included in this Raspberry Pi code package. Add the final firmware here (or in an `esp32/` directory) when it is ready for public release.
