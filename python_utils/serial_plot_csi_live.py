import sys
import matplotlib.pyplot as plt
import numpy as np
import collections
from wait_timer import WaitTimer
from read_stdin import readline


# Wait Timers. Change these values to increase or decrease the rate of `print_stats` and `render_plot`.
print_stats_wait_timer = WaitTimer(1.0)
render_plot_wait_timer = WaitTimer(0.2)

# Deque definition
offsets = collections.deque(maxlen=100)

# some stuff here
offset_index = 0
last_gpio = 0
last_timestamp = 0

# Create figure for plotting
plt.ion()
fig = plt.figure()
ax = fig.add_subplot(111)
fig.canvas.draw()
plt.show(block=False)


def carrier_plot(os):
    plt.clf()
    y = np.asarray(os, dtype=np.int64)
    plt.plot(range(1, len(y), 1), y, color='r')
    plt.xlabel("offset index")
    plt.ylabel("delta t")
    #plt.xlim(0, 100)
    plt.title("Test yoyoyoooo")
    # to flush the GUI events
    fig.canvas.flush_events()
    plt.show()


def process(res):
    # Parser
    parts = res.split()
    gpio = parts[0]

    if (gpio != last_gpio and last_gpio != 0):      #only compute offsets if gpios are not identical
        timestamp = int(parts[-1])
        offsets.append(timestamp-last_timestamp)
        offset_index + 1

    last_gpio = gpio


while True:
    line = readline()
    if "EDGE RISING" in line:           # only intrested in rising edges
        process(line)

        #if print_stats_wait_timer.check():
        #    print_stats_wait_timer.update()

        #if render_plot_wait_timer.check() and len(offsets) > 2:
        #    render_plot_wait_timer.update()
        #    carrier_plot(offsets)
