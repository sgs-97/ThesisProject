#!/usr/bin/env bash

# Wrapper to run extract_durations.sh for all subdirectories of a parent directory

function show_help() {
    echo "Description:"
    echo "  Run analysis_script_runner.sh on each subdirectory of the specified parent directory."
    echo
    echo "Usage: path/to/$(basename $0) <parent_dir> [options]"
    echo
    echo "Arguments:"
    echo "  <parent_dir>       Directory containing subdirectories to process"
    echo
    echo "Options:"
    echo "  [options]          Any options to pass to analysis_script_runner.sh (e.g. --umount_lap_to_sleep_lap)"
    echo "  -h, --help         Show this help message and exit"
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
            # Also show extract_durations.sh help for convenience
            SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
            "$SCRIPT_DIR"/analysis_script_runner.sh -h
            exit 0
            ;;
    esac
done

if [[ $# -lt 2 ]]; then
    print_error "Parent directory and at least one analysis option required."
    show_help
    exit 1
fi

parent_dir="$1"
shift

if [[ ! -d "$parent_dir" ]]; then
    print_error "Parent directory '$parent_dir' does not exist."
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

sub_dir_count="$(find "$parent_dir" -mindepth 1 -maxdepth 1 -type d | sed '/^\s*$/d' | wc -l | xargs)"
echo "[INFO] Running analysis_script_runner.sh for $sub_dir_count subdirectories in $parent_dir"
sleep 1

number_ran=0
for sub_dir in "$parent_dir"/*/; do
    if [[ -d "$sub_dir" ]]; then
        echo "[INFO] Processing: $sub_dir"
        "$SCRIPT_DIR"/analysis_script_runner.sh "$sub_dir" "$@"
        if [[ $? -eq 0 ]]; then
            number_ran=$((number_ran + 1))
        else
            print_warning "analysis_script_runner.sh failed for $sub_dir. See above for details."
        fi
        echo
    fi
    # skip non-directories
done

if [[ $number_ran -eq 0 ]]; then
    print_error "No analyses completed successfully."
    exit 1
fi

echo "[INFO] $number_ran analyses completed for all ($sub_dir_count) subdirectories."

