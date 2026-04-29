"""TF02 (Benewake) UART reader for Jetson Nano.

Default parsing is compatible with Benewake's common 9-byte UART frame format:
  0x59 0x59 Dist_L Dist_H Strength_L Strength_H Temp_L Temp_H Checksum

Notes:
- Many Benewake modules (TFmini/TF02 family) use the same framing; if your TF02
  is configured to a different output mode, this script will not decode it.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Optional


try:
	import serial  # type: ignore
except ImportError as exc:  # pragma: no cover
	raise SystemExit(
		"Missing dependency: pyserial. Install with: python3 -m pip install pyserial"
	) from exc


FRAME_HEADER = b"\x59\x59"
FRAME_LEN = 9


@dataclass(frozen=True)
class TFFrame:
	distance_cm: int
	strength: int
	temperature_c: float


def _checksum_ok(frame: bytes) -> bool:
	if len(frame) != FRAME_LEN:
		return False
	return (sum(frame[0:8]) & 0xFF) == frame[8]


def _parse_frame(frame: bytes) -> TFFrame:
	if len(frame) != FRAME_LEN or not frame.startswith(FRAME_HEADER):
		raise ValueError("Invalid frame")
	if not _checksum_ok(frame):
		raise ValueError("Bad checksum")

	distance_cm = frame[2] | (frame[3] << 8)
	strength = frame[4] | (frame[5] << 8)
	temp_raw = frame[6] | (frame[7] << 8)
	# Benewake docs typically: Temp(°C) = temp_raw/8 - 256
	temperature_c = (temp_raw / 8.0) - 256.0
	return TFFrame(distance_cm=distance_cm, strength=strength, temperature_c=temperature_c)


def read_tf_frame(ser: "serial.Serial", *, timeout_s: float) -> Optional[TFFrame]:
	"""Read one TF UART frame.

	Returns None on timeout.
	"""

	deadline = time.monotonic() + timeout_s
	while time.monotonic() < deadline:
		b0 = ser.read(1)
		if not b0:
			continue
		if b0 != FRAME_HEADER[:1]:
			continue

		b1 = ser.read(1)
		if not b1:
			continue
		if b1 != FRAME_HEADER[1:2]:
			continue

		rest = ser.read(FRAME_LEN - 2)
		if len(rest) != FRAME_LEN - 2:
			continue

		frame = b0 + b1 + rest
		if not _checksum_ok(frame):
			# Bad frame; keep scanning (resync).
			continue

		return _parse_frame(frame)

	return None


def _open_serial(port: str, baud: int, *, timeout_s: float) -> "serial.Serial":
	# timeout applies to individual read() calls.
	return serial.Serial(
		port=port,
		baudrate=baud,
		bytesize=serial.EIGHTBITS,
		parity=serial.PARITY_NONE,
		stopbits=serial.STOPBITS_ONE,
		timeout=0.1,
	)


def main(argv: Optional[list[str]] = None) -> int:
	parser = argparse.ArgumentParser(description="Read TF02 UART frames and print distance")
	parser.add_argument(
		"--port",
		default="/dev/ttyTHS1" if sys.platform != "win32" else "COM3",
		help="Serial port (Jetson Nano: /dev/ttyTHS1; Windows example: COM3)",
	)
	parser.add_argument("--baud", type=int, default=115200, help="UART baud rate")
	parser.add_argument(
		"--timeout",
		type=float,
		default=2.0,
		help="Seconds to wait for one valid frame before printing a timeout message",
	)
	parser.add_argument(
		"--format",
		choices=["pretty", "csv"],
		default="pretty",
		help="Output format",
	)
	args = parser.parse_args(argv)

	try:
		ser = _open_serial(args.port, args.baud, timeout_s=args.timeout)
	except Exception as exc:
		print(f"Failed to open {args.port} @ {args.baud}: {exc}", file=sys.stderr)
		return 2

	if args.format == "csv":
		print("ts,distance_cm,strength,temperature_c")

	try:
		while True:
			frame = read_tf_frame(ser, timeout_s=args.timeout)
			ts = time.time()
			if frame is None:
				print(f"{ts:.3f} timeout", file=sys.stderr)
				continue

			if args.format == "csv":
				print(f"{ts:.3f},{frame.distance_cm},{frame.strength},{frame.temperature_c:.2f}")
			else:
				print(
					f"dist={frame.distance_cm} cm | strength={frame.strength} | temp={frame.temperature_c:.2f} C"
				)
	except KeyboardInterrupt:
		return 0
	finally:
		try:
			ser.close()
		except Exception:
			pass


if __name__ == "__main__":
	raise SystemExit(main())
