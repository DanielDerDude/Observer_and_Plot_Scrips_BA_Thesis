import sys
import matplotlib.pyplot as plt
#import math
import numpy as np
import collections
from wait_timer import WaitTimer
from read_stdin import readline


# Wait Timers. Change these values to increase or decrease the rate of `print_stats` and `render_plot`.
print_stats_wait_timer = WaitTimer(1.0)
render_plot_wait_timer = WaitTimer(0.2)

# Deque definition
temp_edges = collections.deque(maxlen=3)
perm_amp = collections.deque(maxlen=100)
perm_phase = collections.deque(maxlen=100)

# Variables to store CSI statistics
offset_count = 0

# Create figure for plotting
plt.ion()
fig = plt.figure()
ax = fig.add_subplot(111)
fig.canvas.draw()
plt.show(block=False)


def carrier_plot(amp):
    plt.clf()
    df = np.asarray(amp, dtype=np.int32)
    # Can be changed to df[x] to plot sub-carrier x only (set color='r' also)
    plt.plot(range(100 - len(amp), 100), df[:, subcarrier], color='r')
    plt.xlabel("Time")
    plt.ylabel("Amplitude")
    plt.xlim(0, 100)
    plt.title(f"Amplitude plot of Subcarrier {subcarrier}")
    # to flush the GUI events
    fig.canvas.flush_events()
    plt.show()


def process(res):
    # Parser
    parts = res.split()
    timestamp = int(parts[-1])
    temp_edges.append(timestamp)
    diff1 = temp_edges[0] - temp_edges[1]
    diff2 = temp_edges[0] - temp_edges[1]

while True:
    line = readline()
    if "EDGE RISING" in line:
        process(line)

        #if print_stats_wait_timer.check():
        #    print_stats_wait_timer.update()

        if render_plot_wait_timer.check() and len(perm_amp) > 2:
            render_plot_wait_timer.update()
            carrier_plot(perm_amp)
