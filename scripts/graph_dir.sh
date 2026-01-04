#!/usr/bin/env bash

# ------------------------- EDIT BELOW AS NEEDED -------------------------

function show_help() {
    echo "Description:"
    echo "  Run graph.py on the specified directory containing log and annotation (laps) data after being preprocessed."
    echo
    echo "Usage: path/to/$(basename $0) [args] [options]" # Keep as it is
    echo
    echo "Arguments:"
    echo "  <dir>              Directory of log and annotation (laps) data"
    echo
    echo "Options:"
    echo "  --show_in_browser  Open the generated graph in a web browser"
    echo "  --include_video    Include timestamped video in the output HTML (if found inside the directory where the graph is going to be placed). Default: False"
    εψηο "  --skip_hmd_bound   Skip HMD through boundary calculation of times and output CSV"
    echo "  --skip_on_exist    Skip generating files that already exist in the subdirectory"
    echo "  --skip-traffic-analysis  Skip running traffic_analysis_script.sh"
    echo "  -h, --help         Show this help message and exit"
    echo
}

function main() {
    local dir="$1"
    if [[ -z "$dir" ]]; then
        print_error "Directory argument is required."
        exit 1
    fi
    # Check if the --show_in_browser option is provided
    local show_in_browser=''
    local include_video=''
    local skip_on_exist=false
    local skip_hmd_bound=false
    local skip_traffic_analysis=false
    for arg in "$@"; do
        case $arg in
            --show_in_browser)
                show_in_browser="--show_in_browser"
                ;;
            --include_video)
                include_video="--include_video"
                ;;
            --skip_hmd_bound)
                skip_hmd_bound=true
                ;;
            --skip_on_exist)
                skip_on_exist=true
                ;;
            --skip-traffic-analysis)
                skip_traffic_analysis=true
                ;;
        esac
    done

    # Add your main script logic here
    echo "Processing directory: $dir"

    # Check path of dir
    if [[ ! -d "$dir" ]]; then
        print_error "Directory '$dir' does not exist."
        exit 1
    fi

    # If preprocessing output is missing exit
    if ! ls "$dir"/adb_log*.csv 1> /dev/null 2>&1; then
        ls -l "$dir"/adb_log*.csv
        print_error "adb log not found in dir '$dir'. First run preprocess_dir.sh"
        exit 1
    fi
    if ! ls "$dir"/annotated_events.json 1> /dev/null 2>&1; then
        print_error "user_events json not found in dir '$dir'. First run preprocess_dir.sh"
        exit 1
    fi

    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    if [[ "${skip_traffic_analysis}" == true ]]; then
        echo "Skipping traffic analysis step (--skip-traffic-analysis set)."
    else
        bash "$SCRIPT_DIR/traffic_analysis_script.sh" "$dir/ip.json"

    fi

    no_html_files=$(find "$dir" -maxdepth 1 -type f -name "*.html" | wc -l)
    # Check if the directory contains HTML files and skip if skip_on_exist is true
    if [[ $no_html_files != 0 ]] && [[ $skip_on_exist == true ]]; then
      echo "HTML files already exist in the directory. Skipping graph generation."
    else
      python3 $SCRIPT_DIR/../analyze/graph.py "$dir"/adb_log*.csv \
        --user_events "$dir"/annotated_events.json \
        --traffic_csv "$dir"/traffic.csv \
        --ip_json "$dir"/ip.json \
        --hosts_out "$dir" \
        --include_traffic \
        --rate_window_ms 500 \
        --rate_step_ms 50
        $show_in_browser $include_video

    fi

    # Check if the directory contains CSV files and skip if skip_on_exist is true
    if [[ -f "$dir"/passthrough_activations_intervals.csv && ${skip_on_exist} == true ]]; then
      echo "Passthrough activations CSV already exists in the directory. Skipping passthrough activations extraction."
    else
      python3 $SCRIPT_DIR/../analyze/extract_pt_activations.py "$dir"
    fi

    # Check if the directory contains HMD through boundary CSV and skip if skip_on_exist is true
    if [[ -f "$dir"/hmd_through_boundary.csv && ${skip_on_exist} == true ]]; then
        echo "HMD through boundary CSV already exists in the directory. Skipping HMD through boundary calculation."
    else
      if [[ ${skip_hmd_bound} == true ]]; then
          echo "Skipping HMD through boundary calculation."
      else
          python3 $SCRIPT_DIR/../analyze/hmd_through_boundary.py "$dir" --output_file "$dir"/hmd_through_boundary.csv
      fi
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