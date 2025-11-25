#!/bin/bash

echo "Testing timemachine save functionality"
cd ~/recordings

# Clean up any old test files
rm -f test-*.wav

# Start timemachine
echo "Starting timemachine..."
timemachine -c 2 -n TMTest -t 5 -p test- -f wav system:capture_1 system:capture_2 > /tmp/tm_test.log 2>&1 &
TM_PID=$!
echo "Timemachine PID: $TM_PID"

# Wait a bit for it to initialize
sleep 2

# Check if it's still running
if ! ps -p $TM_PID > /dev/null; then
    echo "ERROR: Timemachine died immediately"
    cat /tmp/tm_test.log
    exit 1
fi

echo "Timemachine is running, waiting 3 seconds..."
sleep 3

# Trigger save
echo "Sending SIGUSR1 to save buffer..."
kill -SIGUSR1 $TM_PID

# Wait a moment for save to complete
sleep 2

# Check if process is still alive
if ps -p $TM_PID > /dev/null; then
    echo "Timemachine is still running"
else
    echo "Timemachine has exited"
fi

# Show output
echo -e "\n=== Timemachine output ==="
cat /tmp/tm_test.log

# List files created
echo -e "\n=== Files in ~/recordings ==="
ls -lh ~/recordings/

# Clean up
kill $TM_PID 2>/dev/null
