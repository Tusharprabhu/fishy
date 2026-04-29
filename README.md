# fishy

TF02 (Benewake) LiDAR UART reader (Jetson Nano friendly).

## Hardware wiring (Jetson Nano J41 header)

Jetson Nano UART on the 40-pin header is **3.3V logic**.

- TF02 **TX** -> Jetson **RX** (J41 pin 10)
- TF02 **RX** -> Jetson **TX** (J41 pin 8)
- TF02 **GND** -> Jetson **GND** (any GND pin, e.g. J41 pin 6)
- TF02 **VCC** -> provide the sensor's required power (often 5V). Do **not** assume Jetson pin 2/4 can supply enough current for every sensor.

Important: confirm your TF02 UART TX voltage. If it outputs 5V TTL, use a level shifter before feeding Jetson RX.

## Enable UART on Jetson Nano

Common symptom if UART is busy: you open `/dev/ttyTHS1` but get garbage / nothing, or it's used by a console.

Typical setup is to use `/dev/ttyTHS1` (UART1 on J41).

1. Disable serial console/getty (one of these may apply depending on image):
	- `sudo systemctl stop nvgetty`
	- `sudo systemctl disable nvgetty`
2. Reboot.

Then verify:

- `ls -l /dev/ttyTHS1`
- `sudo usermod -aG dialout $USER` (log out/in afterwards)

## Run

Install dependency:

```bash
python3 -m pip install -r requirements.txt
```

Read TF02 frames:

```bash
python3 fishy.py --port /dev/ttyTHS1 --baud 115200
```

CSV output:

```bash
python3 fishy.py --port /dev/ttyTHS1 --format csv
```