#!/usr/bin/env bash

# ------------------------- EDIT BELOW AS NEEDED -------------------------

function show_help() {
    echo "Description:"
    echo "  Run a full processing of a dir with all scripts on the specified directory containing log and annotation (laps) data. All checks done by subcalls."
    echo
    echo "Usage: path/to/$(basename $0) [args] [options]" # Keep as it is
    echo
    echo "Arguments:"
    echo "  <dir>              Directory of log and annotation (laps) data"
    echo
    echo "Options:"
    echo "  --skip_on_exist   Skip asking for files if they already exist in the directory"
    echo "  -h, --help         Show this help message and exit" # Keep as it is
    echo "  -v, --verbose    Enable verbose output"
    echo
}

function main() {
    local dir="$1"
    if [[ -z "$dir" ]]; then
        print_error "Directory argument is required."
        exit 1
    fi

    shift # Remove the first argument (directory)
    skip_on_exist="" # Default to not skipping when files exist
    VERBOSE_LITERAL="" # Default verbose mode

    # Only accept known options, error otherwise
    while [[ $# -gt 0 ]]; do
        # Skip empty arguments
        if [[ -z "$1" ]]; then
            shift
            continue
        fi
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE_LITERAL="--verbose"
                shift
                ;;
            --skip_on_exist)
                skip_on_exist="--skip_on_exist"
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    
    "$SCRIPT_DIR"/preprocess_dir.sh "$dir" $VERBOSE_LITERAL
    "$SCRIPT_DIR"/graph_dir.sh "$dir" $VERBOSE_LITERAL
    "$SCRIPT_DIR"/hmd_umount_sleep_imx471_durations.sh "$dir"
    "$SCRIPT_DIR"/imx471_spikes_csv_dir.sh "$dir"
    "$SCRIPT_DIR"/hmd_umount_sleep_pt_durations.sh "$dir"
    "$SCRIPT_DIR"/hmd_umount_to_sleep_durations.sh "$dir"
    "$SCRIPT_DIR"/hmd_umount_lap_to_sleep_lap_durations.sh "$dir"
    "$SCRIPT_DIR"/hmd_umount_log_to_lap_durations.sh "$dir"

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

function print_success() {
    local MESSAGE="$*"
    printf -- "\033[0;32m[\u2714] [$(basename $0):${BASH_LINENO[0]}]: %s\033[0m\n" "$MESSAGE"
}

function print_info() {
    local MESSAGE="$*"
    printf -- "\033[0;34m[i] [$(basename $0):${BASH_LINENO[0]}]: %s\033[0m\n" "$MESSAGE"
}

trap 'EXIT_CODE=$?; printf -- "\n\033[0;33m[!] [INTERRUPT][$(basename $0)] Script was interrupted! (Exit Code: $EXIT_CODE)\033[0m\n"; exit $EXIT_CODE' INT TERM
trap '_on_exit $?' EXIT


# Main script
check_help "$@" # Check if -h or --help is present
main "$@"

# =========================================================================