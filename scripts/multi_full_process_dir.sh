#!/usr/bin/env bash

# ------------------------- EDIT BELOW AS NEEDED -------------------------

function show_help() {
    echo "Description:"
    echo "  Run all multi processing scripts a given directory."
    echo
    echo "Usage: path/to/$(basename $0) <dir> [options]"
    echo
    echo "Arguments:"
    echo "  <dir>              Directory containing subdirectories to be preprocessed"
    echo
    echo "Options:"
    echo "  -h, --help         Show this help message and exit"
    echo "  --skip_on_exist    Skip asking for files if they already exist in the directory"
    echo "  --skip_first <N>   Skip the first N directories (default: 0)"
    echo "  --mt               Enable multithreading (default: off)"
    echo "  --threads N        Number of threads for multithreading (default: 4)"
    echo
}

function main() {
    local dir="$1"
    shift # Remove the first argument (directory) from the list
    if [[ -z "$dir" ]]; then
        print_error "Directory argument is required."
        exit 1
    fi

    # Check path of dir
    if [[ ! -d "$dir" ]]; then
        print_error "Directory '$dir' does not exist."
        exit 1
    fi

    # Default values
    local MULTITHREADING=0
    local MAX_THREADS=4
    local SKIP_FIRST=0
    local SKIP_ON_EXIST="" # Default value for skip_on_exist

    # Parse options
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --skip_on_exist)
                SKIP_ON_EXIST="--skip_on_exist"
                shift
                ;;
            --mt)
                MULTITHREADING=1
                shift
                ;;
            --threads)
                if [[ -n "${2:-}" && "$2" =~ ^[0-9]+$ ]]; then
                    MAX_THREADS="$2"
                    shift 2
                else
                    print_error "--threads requires a numeric argument"
                    exit 1
                fi
                ;;
            --skip_first)
                if [[ -n "${2:-}" && "$2" =~ ^[0-9]+$ ]]; then
                    SKIP_FIRST="$2"
                    shift 2
                else
                    print_error "--skip_first requires a numeric argument"
                    exit 1
                fi
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    local dir_count
    dir_count=$(find "$dir" -mindepth 1 -maxdepth 1 -type d | wc -l | sed 's/^ *//')

    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

    if [[ "$MULTITHREADING" -eq 1 ]]; then # TODO: Fix, multi-threaded not working
        local job_count=0
        local total_jobs=0
        declare -A pids
        for sub_dir in "$dir"/*/; do
            echo "[INFO] Starting: $SCRIPT_DIR/full_process_dir.sh \"$sub_dir\" (job $((total_jobs+1)))"
            # Redirect output to separate log files for each job to avoid mixed output
            log_file="$sub_dir/process.log"
            $SCRIPT_DIR/full_process_dir.sh "$sub_dir" "$SKIP_ON_EXIST" >"$log_file" 2>&1 &
            pid=$!
            pids[$pid]="$sub_dir"
            ((job_count++))
            ((total_jobs++))
            if (( job_count >= MAX_THREADS )); then
                finished_pid=$(wait -n)
                echo "[INFO] Job for '${pids[$finished_pid]}' finished. Remaining jobs: $((job_count-1)) running, $((total_jobs)) total started."
                unset pids[$finished_pid]
                ((job_count--))
            fi
        done
        # Wait for all remaining jobs to finish
        for pid in "${!pids[@]}"; do
            wait "$pid"
            echo "[INFO] Job for '${pids[$pid]}' finished. Remaining jobs: $((job_count-1)) running, $((total_jobs)) total started."
            ((job_count--))
        done
        echo "[INFO] All jobs finished."
    else
        i=1
        for sub_dir in "$dir"/*/; do
            if (( i <= SKIP_FIRST )); then
                echo -e "[\033[0;34mINFO\033[0m] Skipping: $i/$dir_count $sub_dir"
                ((i++))
                continue
            fi
            echo -e "[\033[0;34mINFO\033[0m] Running: $i/$dir_count $SCRIPT_DIR/full_process_dir.sh \"$sub_dir\""
            ((i++))
            "$SCRIPT_DIR"/full_process_dir.sh "$sub_dir" "$SKIP_ON_EXIST"
        done
#        python3 ./scripts/concat_multi_dir_csvs.py "$dir" 'hmd_umount_sleep_imx471_durations.csv'
#        python3 ./analyze/cdfs/hmd_umount_sleep_imx471_durations_cdf.py "$dir"/hmd_umount_sleep_imx471_durations_combined.csv all --graphing_tool matplotlib
#        python3 ./scripts/concat_multi_dir_csvs.py "$dir" 'hmd_umount_sleep_pt_durations.csv'
#        python3 ./analyze/cdfs/hmd_umount_sleep_pt_durations_cdf.py "$dir"/hmd_umount_sleep_pt_durations_combined.csv all --graphing_tool matplotlib
#        python3 ./scripts/concat_multi_dir_csvs.py "$dir" 'hmd_umount_to_sleep_durations.csv'
#        python3 ./analyze/cdfs/hmd_umount_to_sleep_durations_cdf.py "$dir"/hmd_umount_to_sleep_durations_combined.csv --graphing_tool matplotlib
#        python3 ./scripts/concat_multi_dir_csvs.py "$dir" 'hmd_umount_lap_to_sleep_lap_durations.csv'
#        python3 ./analyze/cdfs/hmd_umount_lap_to_sleep_lap_durations_cdf.py "$dir"/hmd_umount_lap_to_sleep_lap_durations_combined.csv --graphing_tool matplotlib --output "$dir"/hmd_umount_lap_to_sleep_lap_durations_cdf.png
#        python3 ./scripts/concat_multi_dir_csvs.py "$dir" 'hmd_umount_log_to_lap_durations.csv'
#        python3 ./analyze/cdfs/hmd_umount_log_to_lap_durations_cdf.py "$dir"/hmd_umount_log_to_lap_durations_combined.csv --graphing_tool matplotlib --output "$dir"/hmd_umount_log_to_lap_durations_cdf.png
#        python3 ./scripts/concat_multi_dir_csvs.py "$dir" 'imx471_spikes.csv'
#        python3 ./analyze/cdfs/imx471_spikes_cdf.py "$dir"/imx471_spikes_combined.csv --variable_for_cdf duration --graphing_tool matplotlib --output "$dir"/imx471_spikes_duration.png --remove_title
#        python3 ./analyze/cdfs/imx471_spikes_cdf.py "$dir"/imx471_spikes_combined.csv --variable_for_cdf period --graphing_tool matplotlib --output "$dir"/imx471_spikes_period.png --remove_title
#        python3 ./scripts/ovr_metrics_summary.py "$dir" --time-window 0 --columns all

    fi
}

# Add all cleanup functionality here
function cleanup {
    : # Add cleanup code here
}
function on_error { 
    : # Add additional trap code here
}


# ========================================================================


# ------------- DO NOT EDIT BELOW THIS POINT UNLESS NECESSARY -------------

ARGS=() # Arguments array

# Set options for both bash and zsh
if [ -n "${BASH_VERSION:-}" ]; then
    ORIGINAL_OPTS=$(set +o) # Save the original shell options
    set -o errexit # Exit immediately if a command exits with a non-zero status
    set -o nounset # Treat unset variables as an error
    set -o pipefail # Exit if any command in a pipeline fails
    set -o errtrace # Trap ERR in functions and subshells
    set -o functrace # Trap DEBUG and RETURN in functions
#elif [ -n "${ZSH_VERSION:-}" ];  then
#    ORIGINAL_OPTS=$(setopt)
#    setopt ERR_EXIT
#    setopt NO_UNSET
#    setopt PIPE_FAIL
#    setopt ERR_TRAP
#    setopt DEBUG_FUNCTIONS
else
    echo "Unsupported shell type. Use in Bash only."
    exit 1
fi

function _cleanup() {
  cleanup
  eval $ORIGINAL_OPTS # Reset the shell options
}

function check_help() {
    for arg in "$@"; do
        case $arg in
            -h|--help)
                show_help
                exit 0
                ;;
        esac
    done
}

function _on_exit() {
  local EXIT_CODE=$1
  _cleanup
  if [ $EXIT_CODE -eq 0 ]; then
    printf -- "\n\033[0;32m[\u2714]\033[0m [\033[0;32mEXIT\033[0m][$(basename $0)]: Script finished with no errors! (Exit Code: $EXIT_CODE)\n"
  elif [ $EXIT_CODE -eq 130 ] || [ $EXIT_CODE -eq 143 ]; then
    printf -- "\n\033[0;33m[!]\033[0m [\033[0;33mEXIT\033[0m][$(basename $0)]: Script interrupted! (Exit Code: $EXIT_CODE)\n"
  else
    printf -- "\n\033[0;31m[\u2718]\033[0m [\033[0;31mEXIT\033[0m][$(basename $0)]: Error occurred! (Exit Code: $EXIT_CODE)\n"
  fi
}

function print_error() {
    local MESSAGE="$*"
    printf -- "\033[0;31m[\u2718] [ERROR][$(basename $0):${BASH_LINENO[0]}]: %s\033[0m\n" "$MESSAGE"
}

function print_warning() {
    local MESSAGE="$*"
    printf -- "\033[0;33m[\u26A0] [WARNING][$(basename $0):${BASH_LINENO[0]}]: %s\033[0m\n" "$MESSAGE"
}

trap 'EXIT_CODE=$?; printf -- "\n\033[0;33m[!] [INTERRUPT][$(basename $0)] Script was interrupted! (Exit Code: $EXIT_CODE)\033[0m\n"; exit $EXIT_CODE' INT TERM
trap '_on_exit $?' EXIT


# Main script
check_help "$@" # Check if -h or --help is present
main "$@"

# =========================================================================