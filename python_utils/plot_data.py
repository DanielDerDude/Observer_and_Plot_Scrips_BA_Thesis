import sys
import time
from serial import Serial
import matplotlib.pyplot as plt
import numpy as np
import collections

#
# Run:
# `python ../python_utils/plot_data.py -p COMX` wiht X being the port of the observer
#

test_count = 100    # number of offsets to be measured 

# get port from arguments
args = sys.argv
port = ''
if '-p' in args:
    port = args[args.index('-p')+1]

#USB Port and serial configurations
ser  = Serial(port)
ser.close()

ser.baudrate=115200
ser.port=port
ser.bytesize=8
ser.parity='N'
ser.stopbits=1
ser.timeout=0.1

ser.open()
ser.reset_input_buffer()

# create figure for plotting
plt.ion()
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=False)
fig.canvas.draw()
ax1.set_ylim(bottom=0)
ax2.set_ylim(bottom=0)
plt.show(block=False)

# some variables
offsets = collections.deque(maxlen=test_count+1)
offset_index = 0
new_cycle = True
first_timestamp = 0
last_timestamp = 0

def process(res):
    global first_timestamp
    global last_timestamp
    global new_cycle
    global offset_index

    # parse line
    parts = res.split()
    #gpio = parts[0]
    timestamp = int(parts[-1])

    if new_cycle:
        max_offset = last_timestamp - first_timestamp
        offsets.append(max_offset)
        print('found delta t = ' + str(max_offset))
        print('------------------')
        offset_index += 1
        
        first_timestamp = timestamp
        new_cycle = False
    else:
        last_timestamp = timestamp
        

def refresh_offset_plot():
    ax1.clear()
    ax2.clear()
    
    y = np.asarray(offsets, dtype=np.int64)[1:]  # exclude the first element, it's garbage
    avg = 0
    
    if len(y) != 0:  # Check if there are data points before calculating the average
        avg = sum(y) / len(y)
    
    x_range = range(1, len(y) + 1)
    
    # line plot in the first subplot (ax1)
    ax1.set_title("\u0394t Line Plot")
    ax1.plot(x_range, y, color='b')
    ax1.axhline(avg, color='r', linestyle='--', label=f'avg: {int(avg)} us')
    ax1.set_ylabel("\u0394t")
    ax1.set_xlabel("")
    ax1.legend()
    ax1.grid(True)
    
    # add min max value
    #ax1.text(1.05, 0.8, f"Min: {min(y)} ms", transform=ax1.transAxes)
    #ax1.text(1.05, 0.75, f"Max: {max(y)} ms", transform=ax1.transAxes)

    # histogram in the second subplot (ax2)
    ax2.set_title("Probability Density")
    ax2.hist(y, bins=20, color='blue', cumulative=False, alpha=0.7)
    ax2.set_ylabel("PDF")
    ax2.set_xlabel("\u0394t")
    ax2.grid(True)

    plt.tight_layout()
    fig.canvas.flush_events()


while True:
    try:
        N = ser.in_waiting        
        line = ser.readline(-1)
        line = line.decode().strip()
        if 'RISING' in line:
            process(line)
            print(line)
        elif 'FALLING' in line:
            if offset_index <= test_count+1: 
                refresh_offset_plot()
            new_cycle = True
            
    except KeyboardInterrupt:
        break
    except Exception as ex:
        print(ex)
        pass

fig.show()
fig.savefig('./python_utils/export/test.png', dpi=500)
ser.close()