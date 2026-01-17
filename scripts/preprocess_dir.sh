#!/usr/bin/env bash

# ------------------------- EDIT BELOW AS NEEDED -------------------------

function show_help() {
    echo "Description:"
    echo "  Run preprocess python scripts on the specified directory containing log and annotation (laps) data."
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

    # Iterate args
    shift # Remove the first argument (directory)
    skip_on_exist=false # Default to not skipping when files exist
    VERBOSE_LITERAL="" # Default verbose mode
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE_LITERAL="--verbose"
                ;;
            --skip_on_exist)
                skip_on_exist=true # Set a flag to skip asking for files
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
        shift # Remove the processed argument
    done

    # Add your main script logic here
    echo "Processing directory: $dir"

    # Check path of dir
    if [[ ! -d "$dir" ]]; then
        print_error "Directory '$dir' does not exist."
        exit 1
    fi

    # If preprocessing input is missing exit
        if ! ls "$dir"/adb_log*.log 1> /dev/null 2>&1; then
            printf -- " - adb log not found in dir '$dir'. Searching for log files to use as a fallback...\n"
            # Checking if there are any log files in the directory to use as a fallback. User selection is required.
            if ! ls "$dir"/*.log 1> /dev/null 2>&1; then
                print_error "No log files found in dir '$dir'."
                exit 63 # Exit with code 63 to indicate no log files renamed
            else
              if [[ "${skip_asking:-false}" == true ]]; then
                  FILE=$(ls "$dir"/*.log | head -n 1) # Get the first log file
                  cp "$FILE" "$dir/adb_log_0.log"
                  echo "Using log file: $FILE"
              else
                FILES=()
                while IFS= read -r -d '' file; do
                    FILES+=("$file")
                done < <(find "$dir" -maxdepth 1 -type f -name "*.log" -print0)
                if [[ ${#FILES[@]} -eq 0 ]]; then
                    print_error "No log files found in dir '$dir'."
                    exit 63 # Exit with code 63 to indicate no log files renamed
                fi
                if [[ ${#FILES[@]} -eq 1 ]]; then
                    printf -- "Found 1 log file: %s\n" "${FILES[0]}. Using it as adb_log_0.log.\n"
                    cp "${FILES[0]}" "$dir/adb_log_0.log"
                else
                  printf -- "Found ${#FILES[@]} log files in dir '$dir':\n"
                  # If there are multiple log files, ask the user to select one
                  for (( i=0; i<${#FILES[@]}; i++ )); do
                    printf -- " $i %s\n" "${FILES[$i]}"
                  done
                  printf -- "Select number of the file to use for logs (0-%d): " $(( ${#FILES[@]} - 1 ))
                  read -r file_index
                  if [[ "$file_index" =~ ^[0-9]+$ ]] && (( file_index >= 0 && file_index < ${#FILES[@]} )); then
                      cp "${FILES[file_index]}" "$dir/adb_log_0.log"
                      echo "Using log file: ${FILES[file_index]}"
                  else
                      print_error "Invalid selection. Exiting."
                      exit 63 # Exit with code 63 to indicate no log files renamed
                  fi
                fi
              fi
            fi
        else
          print_success "Found adb log files in dir '$dir': $(ls "$dir"/adb_log*.log)"
        fi

        if ! ls "$dir"/laps.txt 1> /dev/null 2>&1; then
            print_error "user events 'laps.txt' file not found in dir '$dir'. Searching for laps files to use as a fallback...\n"
            # Checking if there are any txt files in the directory to use as a fallback. User selection is required.
            if ! ls "$dir"/*.txt 1> /dev/null 2>&1; then
                print_error "No txt (laps) files found in dir '$dir'."
                exit 64 # Exit with code 64 to indicate no laps files renamed
            else
              if [[ "$skip_asking" == true ]]; then
                  FILE=$(ls "$dir"/*.txt | head -n 1) # Get the first txt file
                  cp "$FILE" "$dir/laps.txt"
                  echo "Using laps file: $FILE"
              else
                FILES=()
                while IFS= read -r -d '' file; do
                    FILES+=("$file")
                done < <(find "$dir" -maxdepth 1 -type f -name "*.txt" -print0)
                if [[ ${#FILES[@]} -eq 0 ]]; then
                    print_error "No txt (laps) files found in dir '$dir'."
                    exit 64 # Exit with code 64 to indicate no laps files renamed
                fi
              if [[ ${#FILES[@]} -eq 1 ]]; then
                  printf -- "Found 1 laps file: %s\n" "${FILES[0]}. Using it as laps.txt.\n"
                  cp "${FILES[0]}" "$dir/laps.txt"
              else
                  print_error "Found ${#FILES[@]} txt files in dir '$dir':"
                  for (( i=0; i<${#FILES[@]}; i++ )); do
                      printf -- " $i %s\n" "${FILES[i]}"
                  done
                  printf -- "Select number of the file to use for laps (0-%d): " $(( ${#FILES[@]} - 1 ))
                  read -r file_index
                  if [[ "$file_index" =~ ^[0-9]+$ ]] && (( file_index >= 0 && file_index < ${#FILES[@]} )); then
                      cp "${FILES[file_index]}" "$dir/laps.txt"
                      echo "Using laps file: ${FILES[file_index]}"
                  else
                      print_error "Invalid selection. Exiting."
                      exit 64 # Exit with code 64 to indicate no log files renamed
                  fi
                fi
              fi
            fi
        else
          print_success "Found laps files in dir '$dir': $(ls "$dir"/laps.txt)"
        fi

    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

    no_adb_log_csv_files=$(find "$dir" -maxdepth 1 -type f -name "adb_log_*.csv" | wc -l)
    if [[ "$no_adb_log_csv_files" -ne 0 && "$skip_on_exist" == true ]]; then
      print_info "Skipping log_to_csv conversion as CSV files already exist in '$dir'."
    else
      python3 "$SCRIPT_DIR"/../file_converters/log_to_csv.py "$dir"/adb_log_*.log
    fi
    if [[ -f "$dir"/annotated_events.json && $skip_on_exist == true ]]; then
      print_info "Skipping laps_to_csv conversion as laps.csv already exists in '$dir'."
    else
      python3 "$SCRIPT_DIR"/../file_converters/states_to_json.py "$dir"/laps.txt "$dir"/adb_log_*.csv $VERBOSE_LITERAL
    fi
    echo "dir = $dir"
    echo "SCRIPT_DIR = $SCRIPT_DIR"

    if ls "$dir"/*.pcapng 1> /dev/null 2>&1; then
      python3 "$SCRIPT_DIR"/../file_converters/pcap_to_csv.py "$dir" $VERBOSE_LITERAL
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