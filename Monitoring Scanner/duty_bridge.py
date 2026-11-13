r"""Serial-to-HTTP bridge for the LIBTRACK duty RFID scanner.

The Arduino sketch prints ``ID NUMBER: <UID>`` for every tap. This script reads
those lines from the scanner's serial port and forwards the UID to the
token-scoped duty endpoint, which stores the time-in/time-out in DutyRecord.
The web app never opens the serial port itself.

Usage (from the project root):
    .\\Libtrack\\Scripts\\python.exe "Monitoring Scanner\\duty_bridge.py"
    .\\Libtrack\\Scripts\\python.exe "Monitoring Scanner\\duty_bridge.py" --port COM5 --baud 9600
    .\\Libtrack\\Scripts\\python.exe "Monitoring Scanner\\duty_bridge.py" --list-ports
"""

#python "Monitoring Scanner\duty_bridge.py" 
import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# This script lives in a sub-folder, so make the project root importable before
# loading the shared settings module. Running it no longer needs PYTHONPATH.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import serial
from serial.tools import list_ports

from config import settings

UID_RE = re.compile(r"ID\s*NUMBER:\s*([0-9A-Fa-f]{4,64})")
MIN_TOKEN_LENGTH = 32
DEDUPE_SECONDS = 2.0
RECONNECT_SECONDS = 3.0
REQUEST_TIMEOUT_SECONDS = 10.0


def extract_uid(line: str) -> str | None:
    """Return the uppercase card UID from an Arduino serial line."""
    match = UID_RE.search(line)
    return match.group(1).upper() if match else None


def post_scan(api_url: str, token: str, uid: str) -> dict:
    """Send one card tap to the duty API and return the parsed response."""
    body = urlencode({"rfid": uid}).encode("utf-8")
    request = Request(
        f"{api_url.rstrip('/')}/api/duty/scan/device",
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Duty-Token": token,
        },
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.load(response)


def describe(result: dict) -> str:
    """Turn the API response into one readable console line."""
    if result.get("message"):
        return str(result["message"])

    status = result.get("status", "unknown")
    person = (result.get("person") or {}).get("fullname")
    if status == "time_in":
        return f"{person or 'Duty personnel'} timed in."
    if status == "time_out":
        return f"{person or 'Duty personnel'} timed out."
    return f"Scan status: {status}"


def describe_ports() -> str:
    """List the serial ports Windows currently exposes."""
    ports = list(list_ports.comports())
    if not ports:
        return "  (no serial ports detected - is the scanner plugged in?)"
    return "\n".join(f"  {port.device}: {port.description}" for port in ports)


def report_error(error: Exception) -> None:
    """Print a useful error without ever exposing the device token."""
    if isinstance(error, HTTPError):
        if error.code == 401:
            print(
                "Rejected: check DUTY_BRIDGE_TOKEN and DUTY_MONITOR_ID.",
                file=sys.stderr,
            )
        elif error.code == 429:
            print("Rate limited: wait a moment before tapping again.", file=sys.stderr)
        else:
            detail = error.read().decode("utf-8", errors="replace")[:200]
            print(f"HTTP {error.code}: {detail}", file=sys.stderr)
        return

    print(f"Cannot reach the web app: {error}", file=sys.stderr)


def run(port: str, baud: int, api_url: str, token: str) -> None:
    last_uid = ""
    last_seen = 0.0
    ports_reported = False

    print("LIBTRACK duty bridge")
    print(f"  API:  {api_url.rstrip('/')}")
    print(f"  Port: {port} @ {baud} baud")
    print("Waiting for cards. Press Ctrl+C to stop.")

    while True:
        try:
            with serial.Serial(port, baud, timeout=1) as connection:
                connection.reset_input_buffer()
                ports_reported = False
                print(f"Serial port {port} connected.")

                while True:
                    raw = connection.readline()
                    if not raw:
                        continue

                    uid = extract_uid(raw.decode("ascii", errors="replace"))
                    if uid is None:
                        continue

                    now = time.monotonic()
                    if uid == last_uid and now - last_seen < DEDUPE_SECONDS:
                        continue
                    last_uid, last_seen = uid, now

                    try:
                        result = post_scan(api_url, token, uid)
                        print(f"[{time.strftime('%H:%M:%S')}] {describe(result)}")
                    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
                        report_error(error)

        except KeyboardInterrupt:
            print("\nStopped.")
            return
        except serial.SerialException as error:
            print(f"Cannot open {port}: {error}", file=sys.stderr)
            if not ports_reported:
                print("Available serial ports:", file=sys.stderr)
                print(describe_ports(), file=sys.stderr)
                print(
                    "Set DUTY_SERIAL_PORT in .env to the scanner's port.",
                    file=sys.stderr,
                )
                ports_reported = True
            print(f"Retrying in {int(RECONNECT_SECONDS)}s...", file=sys.stderr)
            time.sleep(RECONNECT_SECONDS)
        except Exception as error:  # keep the kiosk bridge alive
            print(f"Bridge error: {error}. Reconnecting...", file=sys.stderr)
            time.sleep(RECONNECT_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Forward RFID card taps to the LIBTRACK duty API."
    )
    parser.add_argument(
        "--port",
        default=settings.duty_serial_port,
        help="Serial port (default: %(default)s)",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=settings.duty_serial_baud,
        help="Serial baud rate (default: %(default)s)",
    )
    parser.add_argument(
        "--api-url",
        default=settings.duty_api_url,
        help="Web app base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="List the serial ports Windows can see, then exit.",
    )
    args = parser.parse_args()

    if args.list_ports:
        print("Available serial ports:")
        print(describe_ports())
        return

    token = settings.duty_bridge_token
    if not token:
        raise SystemExit("DUTY_BRIDGE_TOKEN is not set in .env.")
    if len(token) < MIN_TOKEN_LENGTH:
        raise SystemExit(
            f"DUTY_BRIDGE_TOKEN must be at least {MIN_TOKEN_LENGTH} characters."
        )
    if settings.duty_monitor_id is None:
        raise SystemExit("DUTY_MONITOR_ID is not set in .env.")

    try:
        run(args.port, args.baud, args.api_url, token)
    except serial.SerialException as error:
        raise SystemExit(f"Serial error: {error}") from error


if __name__ == "__main__":
    main()
