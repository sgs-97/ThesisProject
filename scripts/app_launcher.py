#!/usr/bin/env python3
"""
Quest App Launcher
Launches an app on a connected Meta Quest device via ADB,
then automatically closes it after a specified number of minutes.
"""

import subprocess
import time
import sys


def run_adb(args: list[str]) -> tuple[int, str, str]:
    """Run an ADB command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["adb"] + args,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_device_connected() -> bool:
    """Check if a Quest device is connected via ADB."""
    code, out, _ = run_adb(["devices"])
    lines = [l for l in out.splitlines() if "\tdevice" in l]
    return len(lines) > 0


def list_installed_packages() -> list[str]:
    """Return list of installed package names on the device."""
    code, out, _ = run_adb(["shell", "pm", "list", "packages"])
    packages = []
    for line in out.splitlines():
        if line.startswith("package:"):
            packages.append(line.replace("package:", "").strip())
    return sorted(packages)


def get_launch_activity(package: str) -> str | None:
    """Try to find the main launchable activity for a package."""
    code, out, _ = run_adb([
        "shell", "cmd", "package", "resolve-activity",
        "--brief", package
    ])
    for line in out.splitlines():
        line = line.strip()
        if "/" in line and not line.startswith("No activity"):
            return line
    return None


def launch_app(package: str) -> bool:
    """Launch an app using its package name."""
    activity = get_launch_activity(package)

    if activity:
        print(f"  Launching activity: {activity}")
        code, out, err = run_adb([
            "shell", "am", "start", "-n", activity
        ])
    else:
        print(f"  No specific activity found, using monkey launcher...")
        code, out, err = run_adb([
            "shell", "monkey", "-p", package, "-c",
            "android.intent.category.LAUNCHER", "1"
        ])

    if code != 0 or "Error" in out:
        print(f"  Error launching app: {err or out}")
        return False
    return True


def close_app(package: str) -> bool:
    """Force-stop an app by package name."""
    code, out, err = run_adb(["shell", "am", "force-stop", package])
    return code == 0


def countdown(total_seconds: int, package: str):
    """Show a live countdown timer, then close the app."""
    print()
    try:
        for remaining in range(total_seconds, 0, -1):
            mins, secs = divmod(remaining, 60)
            timer = f"\r  Time remaining: {mins:02d}:{secs:02d}  (Ctrl+C to stop early)"
            print(timer, end="", flush=True)
            time.sleep(1)
        print("\r  Time's up! Closing app...              ")
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user. Closing app early...")

    success = close_app(package)
    if success:
        print(f"  App '{package}' has been closed.")
    else:
        print(f"  Warning: Could not close app. Try manually: adb shell am force-stop {package}")


def main():
    print("=" * 55)
    print("         Meta Quest App Launcher via ADB")
    print("=" * 55)
    print()

    # Step 1: Check ADB device connection
    print("[1/3] Checking ADB device connection...")
    if not check_device_connected():
        print("\n  ERROR: No Quest device found.")
        print("  Make sure:")
        print("  - Developer Mode is ON in the Meta app")
        print("  - USB cable is connected")
        print("  - You accepted the 'Allow USB Debugging' prompt on the headset")
        print("  - ADB is installed and in your system PATH")
        sys.exit(1)
    print("  Device connected!\n")

    # Step 2: Choose app
    print("[2/3] App selection")
    print("  (a) Enter package name manually")
    print("  (b) List installed packages and choose")
    choice = input("\n  Your choice [a/b]: ").strip().lower()

    if choice == "b":
        print("\n  Fetching installed packages (this may take a moment)...")
        packages = list_installed_packages()
        if not packages:
            print("  No packages found. Try entering manually.")
            choice = "a"
        else:
            for i, pkg in enumerate(packages, 1):
                print(f"  {i:>4}. {pkg}")
            while True:
                try:
                    idx = int(input(f"\n  Enter number (1-{len(packages)}): ").strip())
                    if 1 <= idx <= len(packages):
                        package = packages[idx - 1]
                        break
                    else:
                        print("  Invalid number. Try again.")
                except ValueError:
                    print("  Please enter a valid number.")

    if choice == "a":
        package = input("\n  Enter the full package name\n  (e.g. com.mycompany.myapp): ").strip()
        if not package:
            print("  No package entered. Exiting.")
            sys.exit(1)

    # Step 3: Duration
    print("\n[3/3] How long should the app run?")
    while True:
        try:
            minutes = float(input("  Enter duration in minutes (e.g. 5 or 1.5): ").strip())
            if minutes <= 0:
                print("  Please enter a positive number.")
            else:
                break
        except ValueError:
            print("  Invalid input. Please enter a number.")

    total_seconds = int(minutes * 60)

    # Launch
    print(f"\n  Launching '{package}'...")
    if not launch_app(package):
        print("  Failed to launch app. Exiting.")
        sys.exit(1)

    print(f"  App launched! Will auto-close in {minutes} minute(s).\n")

    # Countdown and close
    countdown(total_seconds, package)

    print("\nDone.")


if __name__ == "__main__":
    main()