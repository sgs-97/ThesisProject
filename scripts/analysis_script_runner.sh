#!/usr/bin/env bash

# Unified analysis script for all hmd_umount_* analyses

function show_help() {
    echo "Description:"
    echo "  Run one or more HMD umount analysis scripts on the specified directory containing log and annotation (laps) data after being preprocessed."
    echo
    echo "Usage: path/to/$(basename $0) <dir> [options]"
    echo
    echo "Arguments:"
    echo "  <dir>              Directory of log and annotation (laps) data"
    echo
    echo "Options (choose one or more):"
    echo "  --umount_lap_to_sleep_lap      Run hmd_umount_lap_to_sleep_lap_durations.py"
    echo "  --umount_lap_to_sleep_log      Run hmd_umount_lap_to_sleep_log_durations.py"
    echo "  --umount_log_to_lap            Run hmd_umount_log_to_lap_durations.py"
    echo "  --umount_log_to_sleep_log      Run hmd_umount_log_to_sleep_log_durations.py"
    echo "  --umount_sleep_imx471          Run hmd_umount_sleep_imx471_durations.py (runs extract_imx471_activations.py if needed)"
    echo "  --umount_sleep_pt              Run hmd_umount_sleep_pt_durations.py (runs extract_pt_activations.py if needed)"
    echo "  --umount_to_sleep              Run hmd_umount_to_sleep_durations.py"
    echo "  --imx471_spikes_csv            Run extract_imx471_spikes.py on adb_log*.csv in the directory"
    echo "  --first_last_pt_activations    Run first_last_pt_activations.py and print a 2-row table (first and last activation). Rows show: sensor_name, duration, start_time, stop_time, rel_start, rel_stop. A row is 'nil' if its activation fails filters: duration <= --max-gap and start within --start-window-s or within --sleep-window-s of device sleep."
    echo "  --verbose                      Print more detailed output during processing"
    echo "  -h, --help                     Show this help message and exit"
    echo
}

function print_error() {
    local MESSAGE="$*"
    printf -- "\033[0;31m[\u2718] [ERROR][$(basename $0)]: %s\033[0m\n" "$MESSAGE"
}

function print_warning() {
    local MESSAGE="$*"
    printf -- "\033[0;33m[\u26A0] [WARNING][$(basename $0)]: %s\033[0m\n" "$MESSAGE"
}

# Check for help
for arg in "$@"; do
    case $arg in
        -h|--help)
            show_help
            exit 0
            ;;
    esac
done

# Parse arguments
if [[ $# -lt 2 ]]; then
    print_error "Directory and at least one analysis option required."
    show_help
    exit 1
fi

dir="$1"
shift

if [[ ! -d "$dir" ]]; then
    print_error "Directory '$dir' does not exist."
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Check for required files
function check_common_inputs() {
    if ! ls "$dir"/adb_log*.csv 1> /dev/null 2>&1; then
        ls -l "$dir"/adb_log*.csv
        print_error "adb log not found in dir '$dir'. First run preprocess_dir.sh"
        exit 1
    fi
    if ! ls "$dir"/annotated_events.json 1> /dev/null 2>&1; then
        print_error "user_events json not found in dir '$dir'. First run preprocess_dir.sh"
        exit 1
    fi
}

ran_any=0
selected_flags=()
need_pt=0
need_imx471=0
run_imx471_spikes=0
run_first_last_pt=0
VERBOSE=""
for arg in "$@"; do
    case $arg in
        --umount_lap_to_sleep_lap)
            selected_flags+=("--umount_lap_to_sleep_lap")
            ran_any=1
            ;;
        --umount_lap_to_sleep_log)
            selected_flags+=("--umount_lap_to_sleep_log")
            ran_any=1
            ;;
        --umount_log_to_lap)
            selected_flags+=("--umount_log_to_lap")
            ran_any=1
            ;;
        --umount_log_to_sleep_log)
            selected_flags+=("--umount_log_to_sleep_log")
            ran_any=1
            ;;
        --umount_sleep_imx471)
            selected_flags+=("--umount_sleep_imx471")
            need_imx471=1
            ran_any=1
            ;;
        --umount_sleep_pt)
            selected_flags+=("--umount_sleep_pt")
            need_pt=1
            ran_any=1
            ;;
        --umount_to_sleep)
            selected_flags+=("--umount_to_sleep")
            ran_any=1
            ;;
        --imx471_spikes_csv)
            run_imx471_spikes=1
            ran_any=1
            ;;
        --first_last_pt_activations)
            run_first_last_pt=1
            ran_any=1
            ;;
        --verbose)
            VERBOSE="--verbose"
            ;;
        *)
            print_error "Unknown option: $arg"
            show_help
            exit 1
            ;;
    esac
done

# Preprocessing if needed
if [[ $need_pt -eq 1 ]]; then
    if ! ls "$dir"/passthrough_activations_intervals.csv 1> /dev/null 2>&1; then
        print_warning "passthrough_activations_intervals.csv not found in dir '$dir'. Running extract_pt_activations.py"
        python3 "$SCRIPT_DIR"/../analyze/extract_pt_activations.py "$dir" "$VERBOSE"
    fi
fi
if [[ $need_imx471 -eq 1 ]]; then
    if [[ ! -s "$dir"/imx471_activations_intervals.csv ]]; then
        print_warning "imx471_activations_intervals.csv not found or is empty in dir '$dir'. Running extract_imx471_activations.py"
        python3 "$SCRIPT_DIR"/../analyze/extract_imx471_activations.py "$dir" "$VERBOSE"
    fi
fi

# Run unified extraction if any selected
if [[ ${#selected_flags[@]} -gt 0 ]]; then
    check_common_inputs
    echo "[INFO] Running extract_durations.py with flags: ${selected_flags[*]}"
    python3 "$SCRIPT_DIR"/../analyze/extract_durations.py "$dir" "${selected_flags[@]}" "$VERBOSE"
fi

# Run imx471_spikes_csv independently if requested
if [[ $run_imx471_spikes -eq 1 ]]; then
    check_common_inputs
    echo "[INFO] Running extract_imx471_spikes.py on $dir/adb_log*.csv"
    python3 "$SCRIPT_DIR"/../analyze/extract_imx471_spikes.py "$dir"/adb_log*.csv $VERBOSE
fi

# Run first_last_pt_activations independently if requested
if [[ $run_first_last_pt -eq 1 ]]; then
    check_common_inputs
    echo "[INFO] Running first_last_pt_activations.py on $dir"
    python3 "$SCRIPT_DIR"/../analyze/first_last_pt_activations.py "$dir" $VERBOSE
fi

if [[ $ran_any -eq 0 ]]; then
    print_error "No analysis option selected."
    show_help
    exit 1
fi

echo "[INFO] All selected analyses completed."
