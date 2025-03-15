# Instructions for writing a user-friendly Shell Script

1. Comprehensive Error Handling and Input Validation
Clear error messages are crucial for a good UX. Implement error handling and input validation throughout the script. For example:

```bash
if [ -z "$1" ] 
  then 
    echo "Usage: evaluate.sh <fork name> (<fork name 2> ...)" 
    echo " for each fork, there must be a 'calculate_average_<fork name>.sh' script and an optional 'prepare_<fork name>.sh'." 
    exit 1 
fi
```

This approach helps users quickly identify and resolve issues, saving them time and frustration.

2. Clear and Colorful Output
Use ANSI color codes to highlight important information, warnings, and errors. For instance:

```bash
BOLD_RED='\033[1;31m'
RESET='\033[0m'
echo -e "${BOLD_RED}ERROR${RESET}: ./calculate_average_$fork.sh does not exist." >&2
```
This visual distinction helps users quickly grasp the nature of each message.

3. Detailed Progress Reporting
Users should understand exactly what the script is doing at each step. Implement a function that prints each command before executing it:

```bash
function print_and_execute() {
  echo "+ $@" >&2 
  "$@" 
}
```

This matches the output format of Bash's builtin set -x tracing, but gives the script author more granular control of what is printed.

This level of transparency not only keeps users informed but also aids in debugging if something goes wrong.

4. Strategic Error Handling with "set -e" and "set +e"
Ensure the script will exit immediately if there was an error in the script itself, but allow it to continue running if individual forks encountered issues. Use the Bash options "set -e" and "set +e" strategically throughout the script. Here's how I implemented this technique:

```bash
# At the beginning of the script
set -eo pipefail

# Before running tests and benchmarks for each fork
for fork in "$@"; do
  set +e # we don't want prepare.sh, test.sh or hyperfine failing on 1 fork to exit the script early

  # Run prepare script (simplified)
  print_and_execute source "./prepare_$fork.sh"

  # Run the test suite (simplified)
  print_and_execute $TIMEOUT ./test.sh $fork

  # ... (other fork-specific operations)
done
set -e  # Re-enable exit on error after the fork-specific operations
```
This approach gives the script author fine-grained control over which errors cause the script to exit and which can be handled in other ways.

5. Platform-Specific Adaptations
Users might run this script on different operating systems, so add logic to detect the OS and adjust the script's behavior accordingly:

```bash
if [ "$(uname -s)" == "Linux" ]; then 
  TIMEOUT="timeout -v $RUN_TIME_LIMIT" 
else # Assume MacOS 
  if [ -x "$(command -v gtimeout)" ]; then 
    TIMEOUT="gtimeout -v $RUN_TIME_LIMIT"
  else 
    echo -e "${BOLD_YELLOW}WARNING${RESET} gtimeout not available, install with `brew install coreutils` or benchmark runs may take indefinitely long." 
  fi
fi
```
This ensures a consistent experience across different environments. Many #1BRC participants were developing on MacOS while the evaluation machine ran linux for example.

6. Timestamped File Outputs for Multiple Runs
To support multiple benchmark runs without overwriting previous results, implement a system of timestamped file outputs. This allows users to run the script multiple times and keep a historical record of all results. Here's how I did it:

```bash
filetimestamp=$(date +"%Y%m%d%H%M%S")

# ... (in the loop for each fork)
HYPERFINE_OPTS="--warmup 0 --runs $RUNS --export-json $fork-$filetimestamp-timing.json --output ./$fork-$filetimestamp.out"

# ... (after the benchmarks)
echo "Raw results saved to file(s):"
for fork in "$@"; do
  if [ -f "$fork-$filetimestamp-timing.json" ]; then
      cat $fork-$filetimestamp-timing.json >> $fork-$filetimestamp.out
      rm $fork-$filetimestamp-timing.json
  fi

  if [ -f "$fork-$filetimestamp.out" ]; then
    echo "  $fork-$filetimestamp.out"
  fi
done
```
This ensures that users can run the script multiple times and keep a historical record of all results.

7. Warnings, Errors, Final Success
Support these messages, to make visible

```bash
# Function to print error and exit
function error_exit() {
    echo -e "${BOLD_RED}❌ ERROR${RESET}: $1" >&2
    exit 1
}
```

```bash
# Function to print success
function success() {
    echo -e "${BOLD_GREEN}✅ SUCCESS${RESET}: $1"
}
```

```bash
# Function to print warning
function warning() {
    echo -e "${BOLD_YELLOW}⚠️ WARNING${RESET}: $1"
}
```

8. Organization
Make it easy to read and parse, by seperating out function definitions with:

##########################################################
# Defining dependencies
##########################################################

and 

##########################################################
# Starting main steps
##########################################################
