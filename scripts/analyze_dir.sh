#!/usr/bin/env bash

# ------------------------- EDIT BELOW AS NEEDED -------------------------

function show_help() {
    echo "Description:"
    echo "  This is a template script for bash scripts. Use this as a starting point for your scripts."
    echo
    echo "Usage: path/to/$(basename $0) [args] [options]" # Keep as it is
    echo
    echo "Arguments:"
    echo "  <dir>              Directory of log and annotation (laps) data"
    echo
    echo "Options:"
    echo "  -h, --help         Show this help message and exit" # Keep as it is
    echo "  -v, --verbose      Enable verbose mode"
    echo
}

function main() {
    local dir="$1"
    if [[ -z "$dir" ]]; then
        echo "Error: Directory argument is required."
        exit 1
    fi

    # Add your main script logic here
    echo "Processing directory: $dir"

    # Check path of dir
    if [[ ! -d "$dir" ]]; then
        echo "Error: Directory '$dir' does not exist."
        exit 1
    fi

    # If preprocessing output is missing exit
    if [[ ! -f "$dir"/adb_log*.csv ]]; then
        echo "Error: adb_log not found in dir '$dir'. First run preprocess_dir.sh"
        exit 1
    fi
    if [[ ! -f "$dir"/*.json ]]; then
        echo "Error: app_events json not found in dir '$dir'. First run preprocess_dir.sh"
        exit 1
    fi

    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

    python3 $SCRIPT_DIR/../activity_graphs/analyze_logs.py "$dir"/adb_log*.csv "$dir"/*.json

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
    printf "\n\033[0;32m[\u2714]\033[0m [\033[0;32mEXIT\033[0m][$(basename $0)]: Script finished with no errors! (Exit Code: $EXIT_CODE)\n"
  elif [ $EXIT_CODE -eq 130 ] || [ $EXIT_CODE -eq 143 ]; then
    printf "\n\033[0;33m[!]\033[0m [\033[0;33mEXIT\033[0m][$(basename $0)]: Script interrupted! (Exit Code: $EXIT_CODE)\n"
  else
    printf "\n\033[0;31m[\u2718]\033[0m [\033[0;31mEXIT\033[0m][$(basename $0)]: Error occurred! (Exit Code: $EXIT_CODE)\n"
  fi
}

trap 'EXIT_CODE=$?; printf "\n\033[0;33m[!] [INTERRUPT][$(basename $0)] Script was interrupted! (Exit Code: $EXIT_CODE)\033[0m\n"; exit $EXIT_CODE' INT TERM
trap '_on_exit $?' EXIT


# Main script
check_help "$@" # Check if -h or --help is present
main "$@"

# =========================================================================