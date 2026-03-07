"""
configure_port.py — Detects the Arduino COM port and patches app.py.
Called by start.bat before launching the server.
"""
import re
import sys

try:
    from serial.tools import list_ports
except ImportError:
    print("ERROR: pyserial is not installed. Run: pip install pyserial")
    sys.exit(1)

APP_FILE = "app.py"
COM_PATTERN = re.compile(r'^(COM_PORT\s*=\s*)"[^"]*"', re.MULTILINE)


def get_ports():
    return list(list_ports.comports())


def patch_app(port_name):
    with open(APP_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    if not COM_PATTERN.search(content):
        print(f"ERROR: Could not find COM_PORT setting in {APP_FILE}.")
        sys.exit(1)

    new_content = COM_PATTERN.sub(lambda m: f'{m.group(1)}"{port_name}"', content)

    with open(APP_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)


def main():
    ports = get_ports()

    if len(ports) == 0:
        print()
        print("  Arduino not detected.")
        print("  Please plug in the Arduino via USB and try again.")
        print()
        sys.exit(1)

    if len(ports) == 1:
        selected = ports[0]
        print(f"  Arduino detected on {selected.device} ({selected.description})")
        patch_app(selected.device)
        print(f"  COM port set to {selected.device}. Starting Veritime...")
        sys.exit(0)

    # Multiple ports — ask the user to choose
    print()
    print("  Multiple USB devices found. Which one is the Arduino?")
    print()
    for i, p in enumerate(ports, 1):
        print(f"    [{i}] {p.device} — {p.description}")
    print()

    while True:
        try:
            choice = input("  Type a number and press Enter: ").strip()
            index = int(choice) - 1
            if 0 <= index < len(ports):
                selected = ports[index]
                break
            else:
                print(f"  Please enter a number between 1 and {len(ports)}.")
        except (ValueError, EOFError):
            print(f"  Please enter a number between 1 and {len(ports)}.")

    patch_app(selected.device)
    print(f"  COM port set to {selected.device}. Starting Veritime...")
    sys.exit(0)


if __name__ == "__main__":
    main()
