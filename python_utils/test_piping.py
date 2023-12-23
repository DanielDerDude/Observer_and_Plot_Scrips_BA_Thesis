import sys
import time
from read_stdin import readline

#
# Ayo this something here hahaaaa
#
# Run:
# `idf.py monitor -p COMX | python ../python_utils/test_piping.py`
#

interval_start_time = 0

#
# Start Evaluation
#
print("Start Evaluation")
while True:
    line = readline()
    if "EDGE" in line:
    #if time.time() - interval_start_time > 1.0:
        print("readline: "+line)
        #interval_start_time = time.time()
