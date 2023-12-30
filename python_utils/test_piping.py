import sys
import time
from serial import Serial
import matplotlib.pyplot as plt
import numpy as np
import collections

#
# Ayo this something here hahaaaa
#
# Run:
# `idf.py monitor -p COMX | python ../python_utils/test_piping.py`
#

#USB Port and serial configurations
port = 'COM16'
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
fig = plt.figure()
ax1 = fig.add_subplot(111)
fig.canvas.draw()
plt.show(block=False)

# some variables
offsets = collections.deque(maxlen=100)
offset_index = 0
new_cycle = True
first_timestamp = 0
last_timestamp = 0

def get_avg_offset():
    sum = 0
    for i in offsets:
        sum += i
    
    return sum/(offset_index+1)

def process(res):
    global first_timestamp
    global last_timestamp
    global new_cycle
    global offset_index

    # parse line
    parts = res.split()
    #gpio = parts[0]
    timestamp = int(parts[-1])

    if (new_cycle):
        max_offset = last_timestamp-first_timestamp
        offsets.append(max_offset)
        print('found delta t = '+str(max_offset))
        print('------------------')
        offset_index += 1
        
        first_timestamp = timestamp
        new_cycle = False
    else:
        last_timestamp = timestamp
        

def refresh_offset_plot():
    plt.clf()
    y = np.asarray(offsets, dtype=np.int64)
    #plt.hist(y, offset_index, facecolor='blue')
    plt.plot(range(1, offset_index), y[1:], color='b')
    plt.axhline(y=get_avg_offset(), color='r', linestyle='-')
    plt.xlabel("offset index")
    plt.ylabel("delta t")
    #plt.xlim(0, 100)
    plt.title("Test yoyoyoooo")
    # to flush the GUI events
    fig.canvas.flush_events()
    plt.show()


while True:
    try:
        N = ser.in_waiting        
        line = ser.readline(-1)
        line = line.decode().strip()
        if 'RISING' in line:
            process(line)
            print(line)
        elif 'FALLING' in line:
            refresh_offset_plot()
            new_cycle = True
            
    except KeyboardInterrupt:
        break
    except Exception as ex:
        print(ex)
        pass

ser.close()