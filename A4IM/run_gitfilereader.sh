#!/bin/bash
# run_gitfilereader.sh

# Set Qt platform plugin path
export QT_PLUGIN_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/PyQt5/Qt/plugins"

# Set library path
export LD_LIBRARY_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd ):$LD_LIBRARY_PATH"

# Run the application
./GitFileReader