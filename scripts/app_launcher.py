#!/usr/bin/env python3
"""
VR Network Analysis — Experiment Runner
Orchestrates a full capture session on Meta Quest 3:
  - Pre-flight checks and connection reset
  - tcpdump on Mac hotspot (bridge100)
  - PCAPdroid on Quest (broadcast start/stop)
  - Screen recording via ADB
  - App launch and timed session
  - Post-session pull of all files
"""

import subprocess
import time
import sys
import os
import argparse
from datetime import datetime


# ── Config ─────────────────────────────────────────────────────────────────

HOTSPOT_INTERFACE      = "bridge100"
RECORDING_PATH_DEVICE  = "/sdcard/experiment_recording.mp4"
PCAPDROID_PKG          = "com.emanuelef.remote_capture"
PCAPDROID_ACTIVITY     = f"{PCAPDROID_PKG}/.activities.MainActivity"
PCAPDROID_START_ACTION = f"{PCAPDROID_PKG}.action.START_CAPTURE"
PCAPDROID_STOP_ACTION  = f"{PCAPDROID_PKG}.action.STOP_CAPTURE"
PCAPDROID_RECEIVER     = f"{PCAPDROID_PKG}/.receivers.ActionReceiver"
PCAPDROID_DOWNLOAD_DIR = "/storage/emulated/0/Download/PCAPdroid"

EXCLUDED_PREFIXES = {
    "com.oculus", "com.meta", "com.facebook",
    "com.android", "android", "com.google.android",
    "com.emanuelef"
}


# ── Helpers ────────────────────────────────────────────────────────────────

def run_adb(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    result = subprocess.run(
        ["adb"] + args,
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def banner(text: str):
    print(f"\n{'=' * 55}")
    print(f"  {text}")
    print(f"{'=' * 55}")


def step(text: str):
    print(f"\n[»] {text}")


def ok(text: str):
    print(f"    ✓ {text}")


def fail(text: str):
    print(f"    ✗ {text}")


def warn(text: str):
    print(f"    ⚠ {text}")


# ── App Selection ──────────────────────────────────────────────────────────

def list_user_packages() -> list[str]:
    _, out, _ = run_adb(["shell", "pm", "list", "packages"])
    packages = []
    for line in out.splitlines():
        if line.startswith("package:"):
            pkg = line.replace("package:", "").strip()
            if not any(pkg.startswith(p) for p in EXCLUDED_PREFIXES):
                packages.append(pkg)
    return sorted(packages)


def select_app() -> str:
    print("\n[1/2] App Selection")
    print("  (a) Enter package name manually")
    print("  (b) List installed apps and choose")
    choice = input("\n  Your choice [a/b]: ").strip().lower()

    if choice == "b":
        print("\n  Fetching installed packages...")
        packages = list_user_packages()
        if not packages:
            print("  No packages found. Enter manually.")
            choice = "a"
        else:
            for i, pkg in enumerate(packages, 1):
                print(f"  {i:>4}. {pkg}")
            while True:
                try:
                    idx = int(input(f"\n  Enter number (1-{len(packages)}): ").strip())
                    if 1 <= idx <= len(packages):
                        return packages[idx - 1]
                    print("  Invalid number. Try again.")
                except ValueError:
                    print("  Please enter a valid number.")

    pkg = input("\n  Enter full package name (e.g. com.Icosa.OpenBrush): ").strip()
    if not pkg:
        print("  No package entered. Exiting.")
        sys.exit(1)
    return pkg


# ── Device / Network Checks ────────────────────────────────────────────────

def check_device() -> bool:
    _, out, _ = run_adb(["devices"])
    return any("\tdevice" in l for l in out.splitlines())


def get_uid(package: str) -> str | None:
    _, out, _ = run_adb(["shell", "dumpsys", "package", package])
    for line in out.splitlines():
        if "userId=" in line:
            return line.strip().split("userId=")[1].split()[0]
    return None


def disable_wifi():
    run_adb(["shell", "svc", "wifi", "disable"])


def enable_wifi():
    run_adb(["shell", "svc", "wifi", "enable"])


def kill_all_apps(package: str):
    run_adb(["shell", "am", "force-stop", package])
    run_adb(["shell", "am", "kill-all"])


def check_no_established_tcp() -> bool:
    _, tcp6, _ = run_adb(["shell", "cat", "/proc/net/tcp6"])
    _, tcp4, _ = run_adb(["shell", "cat", "/proc/net/tcp"])
    est6 = [l for l in tcp6.splitlines() if " 01 " in l]
    est4 = [l for l in tcp4.splitlines() if " 01 " in l]
    return len(est6) == 0 and len(est4) == 0


def check_wlan0_idle() -> bool:
    def parse_wlan(output: str) -> tuple[str, str]:
        for line in output.splitlines():
            if "wlan0" in line:
                parts = line.split()
                return parts[1], parts[9]
        return "", ""

    _, snap1, _ = run_adb(["shell", "cat", "/proc/net/dev"])
    time.sleep(3)
    _, snap2, _ = run_adb(["shell", "cat", "/proc/net/dev"])
    rx1, tx1 = parse_wlan(snap1)
    rx2, tx2 = parse_wlan(snap2)
    return rx1 == rx2 and tx1 == tx2


def run_preflight(package: str) -> bool:
    banner("Pre-flight Checks")

    step("Checking ADB device connection...")
    if not check_device():
        fail("No Quest device found. Check USB cable and developer mode.")
        return False
    ok("Device connected")

    step("Killing app and all user processes...")
    kill_all_apps(package)
    ok("Apps killed")

    step("Disabling WiFi to reset all connections...")
    disable_wifi()
    time.sleep(3)
    ok("WiFi disabled")

    step("Checking for ESTABLISHED TCP connections...")
    if not check_no_established_tcp():
        fail("ESTABLISHED connections still present. Cannot proceed.")
        enable_wifi()
        return False
    ok("No ESTABLISHED TCP connections")

    step("Re-enabling WiFi...")
    enable_wifi()
    time.sleep(4)
    ok("WiFi re-enabled")

    step("Checking wlan0 is idle (two snapshots 3s apart)...")
    if not check_wlan0_idle():
        warn("wlan0 not fully idle — background OS traffic present. Proceeding anyway.")
    else:
        ok("wlan0 idle — clean baseline confirmed")

    return True


# ── eBPF Snapshot ──────────────────────────────────────────────────────────

def get_ebpf_snapshot(uid: str) -> str:
    _, out, _ = run_adb(["shell", "dumpsys", "netstats"])
    in_section = False
    for line in out.splitlines():
        if "mAppUidStatsMap" in line:
            in_section = True
        if in_section and uid in line:
            return line.strip()
    return "NOT FOUND"


def save_ebpf(uid: str, label: str, output_dir: str) -> str:
    snapshot = get_ebpf_snapshot(uid)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"ebpf_{label}_{ts}.txt")
    with open(path, "w") as f:
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Label: {label}\n")
        f.write(f"UID: {uid}\n")
        f.write(f"Snapshot: {snapshot}\n")
    ok(f"eBPF {label} snapshot → {path}")
    print(f"    {snapshot}")
    return path


# ── App Launch / Close ─────────────────────────────────────────────────────

def get_launch_activity(package: str) -> str | None:
    _, out, _ = run_adb([
        "shell", "cmd", "package", "resolve-activity", "--brief", package
    ])
    for line in out.splitlines():
        line = line.strip()
        if "/" in line and not line.startswith("No activity"):
            return line
    return None


def launch_app(package: str) -> bool:
    activity = get_launch_activity(package)
    if activity:
        code, out, err = run_adb(["shell", "am", "start", "-n", activity])
    else:
        code, out, err = run_adb([
            "shell", "monkey", "-p", package,
            "-c", "android.intent.category.LAUNCHER", "1"
        ])
    if code != 0 or "Error" in out:
        fail(f"Failed to launch: {err or out}")
        return False
    return True


def close_app(package: str):
    run_adb(["shell", "am", "force-stop", package])


# ── Screen Recording ───────────────────────────────────────────────────────

def start_screen_recording(duration_seconds: int) -> subprocess.Popen:
    proc = subprocess.Popen(
        ["adb", "shell", "screenrecord",
         "--time-limit", str(min(duration_seconds + 30, 180)),
         RECORDING_PATH_DEVICE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return proc


def stop_screen_recording(proc: subprocess.Popen):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    time.sleep(2)
    ok("Screen recording stopped")


def pull_screen_recording(output_dir: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_path = os.path.join(output_dir, f"screen_recording_{ts}.mp4")
    run_adb(["pull", RECORDING_PATH_DEVICE, local_path])
    ok(f"Screen recording → {local_path}")
    return local_path


# ── tcpdump on bridge100 ───────────────────────────────────────────────────

def start_tcpdump(output_dir: str) -> tuple[subprocess.Popen, str]:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pcap_path = os.path.join(output_dir, f"hotspot_{ts}.pcap")
    print(f"\n  Starting tcpdump on {HOTSPOT_INTERFACE} → {pcap_path}")
    print("  (You may be prompted for your sudo password)")
    proc = subprocess.Popen(
        ["sudo", "tcpdump", "-i", HOTSPOT_INTERFACE, "-w", pcap_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return proc, pcap_path


def stop_tcpdump(proc: subprocess.Popen, pcap_path: str):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    ok(f"tcpdump stopped → {pcap_path}")


# ── PCAPdroid ──────────────────────────────────────────────────────────────

def start_pcapdroid(app_filter: str) -> bool:
    """
    Open PCAPdroid and attempt broadcast start.
    First time requires VPN permission accepted manually on headset.
    Returns True if auto-started, False if manual confirmation needed.
    """
    # Open PCAPdroid app on Quest
    run_adb(["shell", "am", "start", "-n", PCAPDROID_ACTIVITY])
    time.sleep(3)

    # Send broadcast start with app filter
    run_adb([
        "shell", "am", "broadcast",
        "-a", PCAPDROID_START_ACTION,
        "-n", PCAPDROID_RECEIVER,
        "--es", "app_filter", app_filter
    ])
    time.sleep(3)

    # Check if CaptureService started
    _, out, _ = run_adb([
        "shell", "dumpsys", "activity", "services", PCAPDROID_PKG
    ])
    return "CaptureService" in out


def stop_pcapdroid():
    run_adb([
        "shell", "am", "broadcast",
        "-a", PCAPDROID_STOP_ACTION,
        "-n", PCAPDROID_RECEIVER
    ])
    time.sleep(2)
    ok("PCAPdroid capture stopped")


def pull_pcapdroid(output_dir: str) -> str | None:
    _, out, _ = run_adb([
        "shell", "find", PCAPDROID_DOWNLOAD_DIR, "-name", "*.pcap"
    ])
    files = [f.strip() for f in out.splitlines() if f.strip()]
    if not files:
        warn("No PCAPdroid pcap files found on device")
        return None
    latest = sorted(files)[-1]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_path = os.path.join(output_dir, f"pcapdroid_{ts}.pcap")
    run_adb(["pull", latest, local_path])
    ok(f"PCAPdroid pcap → {local_path}")
    return local_path


# ── Countdown ──────────────────────────────────────────────────────────────

def countdown(total_seconds: int, package: str):
    print()
    try:
        for remaining in range(total_seconds, 0, -1):
            mins, secs = divmod(remaining, 60)
            print(
                f"\r  Session running: {mins:02d}:{secs:02d} remaining  "
                f"(Ctrl+C to stop early)",
                end="", flush=True
            )
            time.sleep(1)
        print("\r  Session complete. Closing app...                          ")
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Closing app early...")
    close_app(package)
    ok(f"App '{package}' closed")

def pull_apk(package: str, output_dir: str) -> str | None:
    step(f"Pulling APK for {package}...")
    _, out, _ = run_adb(["shell", "pm", "path", package])
    if not out.startswith("package:"):
        warn(f"Could not find APK path for {package}")
        return None
    apk_path = out.replace("package:", "").strip()
    local_path = os.path.join(output_dir, f"{package}.apk")
    run_adb(["pull", apk_path, local_path])
    ok(f"APK → {local_path}")
    return local_path


# ── Main ───────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="VR Network Analysis Experiment Runner"
    )
    parser.add_argument(
        "--output", "-o", required=True,
        help="Output directory for all captured files"
    )
    parser.add_argument(
        "--duration", "-d", type=float, default=7.0,
        help="Session duration in minutes (default: 7)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    duration_seconds = 7 * 60  # fixed 7 minutes

    banner("VR Network Analysis — Experiment Runner")
    print(f"  Session duration  : 7 minutes")
    print(f"  Hotspot interface : {HOTSPOT_INTERFACE}")

    # ── 1. Select app
    package = select_app()
    print(f"\n  Selected app: {package}")

    # Create session directory named after app
    app_short_name = package.split(".")[-1].lower()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.path.expanduser(args.output), f"{app_short_name}_{ts}")
    os.makedirs(output_dir, exist_ok=True)
    print(f"  Session directory : {output_dir}")

    # ── 2. Resolve UID
    step("Resolving app UID...")
    uid = get_uid(package)
    if not uid:
        fail(f"Could not resolve UID for {package}. Is it installed?")
        sys.exit(1)
    ok(f"UID = {uid}")

    # ── 3. Pre-flight checks
    if not run_preflight(package):
        print("\n  Pre-flight checks failed. Exiting.")
        sys.exit(1)

    # ── 4. eBPF BEFORE
    banner("Baseline Measurement")
    save_ebpf(uid, "BEFORE", output_dir)

    # ── 5. Start tcpdump on bridge100
    banner("Starting Captures")
    tcpdump_proc, pcap_path = start_tcpdump(output_dir)
    time.sleep(1)
    ok(f"tcpdump running on {HOTSPOT_INTERFACE} → {pcap_path}")

    # ── 6. Start PCAPdroid via broadcast
    step(f"Starting PCAPdroid with app filter: {package}...")
    auto_started = start_pcapdroid(package)

    if auto_started:
        ok("PCAPdroid capture started automatically via broadcast")
    else:
        print("\n" + "─" * 55)
        print("  ACTION REQUIRED on Quest headset:")
        print("  PCAPdroid is open — please:")
        print("  1. Accept the VPN permission dialog if shown")
        print(f"  2. Confirm app filter is set to: {package}")
        print("  3. Tap PLAY to start capture")
        print("  (After accepting VPN once, future sessions start automatically)")
        print("─" * 55)
        input("\n  Press ENTER when PCAPdroid is capturing...")

    # ── 7. Start screen recording
    step("Starting screen recording on Quest...")
    rec_proc = start_screen_recording(duration_seconds)
    time.sleep(1)
    ok("Screen recording started")

    # ── 8. Launch app
    banner("Launching App")
    step(f"Launching {package}...")
    if not launch_app(package):
        fail("Could not launch app. Stopping all captures.")
        stop_tcpdump(tcpdump_proc, pcap_path)
        stop_pcapdroid()
        stop_screen_recording(rec_proc)
        sys.exit(1)
    ok(f"App launched — session running for {args.duration} minutes")

    # ── 9. Countdown timer
    countdown(duration_seconds, package)

    # ── 10. Stop all captures
    banner("Stopping Captures")

    step("Stopping tcpdump...")
    stop_tcpdump(tcpdump_proc, pcap_path)

    step("Stopping PCAPdroid...")
    stop_pcapdroid()

    step("Stopping screen recording...")
    stop_screen_recording(rec_proc)

    # ── 11. eBPF AFTER
    banner("Post-session Measurement")
    save_ebpf(uid, "AFTER", output_dir)

    # ── 12. Pull all files from Quest
    banner("Pulling Files from Quest")
    pull_screen_recording(output_dir)
    pull_pcapdroid(output_dir)
    pull_apk(package, output_dir)
    

    # ── 13. Session summary
    banner("Session Complete")
    print(f"  App               : {package}")
    print(f"  UID               : {uid}")
    print(f"  Duration          : {args.duration} minutes")
    print(f"  Hotspot interface : {HOTSPOT_INTERFACE}")
    print(f"  Output directory  : {output_dir}")
    print(f"\n  Files saved:")
    for f in sorted(os.listdir(output_dir)):
        size = os.path.getsize(os.path.join(output_dir, f))
        print(f"    {f:<45} {size:>12,} bytes")
    print("\n  Done.\n")


if __name__ == "__main__":
    main()