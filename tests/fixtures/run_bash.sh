#!/bin/bash

# Just return the exit code
echo "Processing run_bash.sh"
if [ -n "$1" ]; then
  exit "$1"
fi
