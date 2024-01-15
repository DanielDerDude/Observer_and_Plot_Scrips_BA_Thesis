import sys
import serial
import matplotlib.pyplot as plt
import numpy as np
import collections
import time

#
# Run:
# `python ../python_utils/plot_data.py -obsv COMX -peer COMY` with COMX and COMY being the port of the observer and slave peer
#

def correlate_timestamp(timestamp):
    return int(time.perf_counter()*1e6)-timestamp 

def configure_serial(port):
    ser = serial.Serial()
    ser.baudrate = 115200
    ser.port = port
    ser.parity = 'N'
    ser.timeout = 0.1
    try:
        ser.open()
    except Exception as e:
        print(e)
        sys.exit()
    ser.reset_input_buffer()
    return ser

def process_obsv(line, measured_delta, first_timestamp, last_timestamp, new_cycle, measure_index):
    # parse line
    timestamp = int(line.split()[-1])

    if new_cycle:
        max_offset = abs(last_timestamp - first_timestamp)
        if max_offset != 0: measured_delta.append(max_offset)
        print('found delta t = ' + str(max_offset))
        print('------------------')
        measure_index += 1
        
        first_timestamp = timestamp
        new_cycle = False
    else:
        last_timestamp = timestamp

    return measured_delta, first_timestamp, last_timestamp, new_cycle, measure_index 

def process_peer(line, peer_offsets):
    parts = line.split()
    offset = int(parts[parts.index('with')+1])
    peer_offsets.append(offset)
    print('computed offset to master: '+str(offset))

def refresh_measure_plot(fig, line_ax, pd_ax, measured_delta):
    line_ax.clear()
    pd_ax.clear()
    
    y = np.asarray(measured_delta, dtype=np.int64)[1:]  # exclude the first element, it's garbage
    avg = 0
    
    if len(y) != 0:  # Check if there are data points before calculating the average
        avg = sum(y) / len(y)
    
    x_range = range(1, len(y)+1)
    
    # line plot in the first subplot (ax1)
    line_ax.set_title("Measured time deviation between peers")
    line_ax.plot(x_range, y, color='b')
    line_ax.axhline(avg, color='b', linestyle='--', label=f'avg: {int(avg)} us')
    line_ax.set_ylabel("\u0394t")
    line_ax.set_xlabel("Measure Index")
    line_ax.legend()
    line_ax.grid(True)

    # histogram in the second subplot (ax2)
    pd_ax.set_title("Probability Density")
    pd_ax.hist(y, bins=20, color='blue', cumulative=False, density=False, alpha=0.7)
    pd_ax.set_ylabel("PDF")
    pd_ax.set_xlabel("\u0394t")
    pd_ax.grid(True)

    fig.tight_layout()
    fig.canvas.flush_events()

def refresh_peer_plot(fig, sysoffs_ax, diff_ax,peer_comp_offsets, peer_real_offsets):
    sysoffs_ax.clear()
    diff_ax.clear()

    comp_offset = np.asarray(peer_comp_offsets, dtype=np.int64)[2:]  # exclude the first element, it's garbage
    #real_offset = np.asarray(peer_real_offsets, dtype=np.int64)[1:]

    comp_offset_range = range(1, len(comp_offset) + 1)
    #real_offset_range = range(1, len(real_offset) + 1)

    #diff_len = min([len(comp_offset), len(real_offset)])
    #diff = np.subtract(comp_offset[:diff_len], real_offset[:diff_len])
    #diff_range = range(1, diff_len + 1)
    
    #avg_deviation = sum(diff) / len(diff) if len(diff) != 0 else 0

    # line plot in the first subplot (line_ax)
    sysoffs_ax.set_title("Computed Systime-Offsets to oldest Peer")
    sysoffs_ax.plot(comp_offset_range, comp_offset, color='r', label='computed offset')
    #sysoffs_ax.plot(real_offset_range, real_offset, color='b', label='measured offset')
    #line_ax.axhline(avg, color='r', linestyle='--', label=f'avg: {int(avg)} us')
    sysoffs_ax.set_ylabel("\u0394t")
    sysoffs_ax.set_xlabel("Offset Index")
    sysoffs_ax.legend(loc = 'center right')
    sysoffs_ax.grid(True)
    
    """ diff_ax.set_title("Deviation of computed and measured Systime-Offset")
    diff_ax.plot(diff_range, diff, color='g', label='deviation')
    diff_ax.axhline(avg_deviation, color='g', linestyle='--', label=f'avg: {int(avg_deviation)} us')
    diff_ax.set_ylabel("\u0394t")
    diff_ax.set_xlabel("Offset Index")
    diff_ax.legend(loc = 'center right')
    diff_ax.grid(True) """

    fig.tight_layout()
    fig.canvas.flush_events()

def refresh_send_recv_plot(fig, send_ax, recv_ax, peer1_send_offsets, peer2_send_offsets, peer1_recv_offsets, peer2_recv_offsets):
    send_ax.clear()
    recv_ax.clear()

    p1_send = np.asarray(peer1_send_offsets, dtype=np.int64)
    p2_send = np.asarray(peer2_send_offsets, dtype=np.int64)
    p1_recv = np.asarray(peer1_recv_offsets, dtype=np.int64)
    p2_recv = np.asarray(peer2_recv_offsets, dtype=np.int64)

    p1_send_range = range(1, len(p1_send) + 1)
    p2_send_range = range(1, len(p2_send) + 1)
    p1_recv_range = range(1, len(p1_recv) + 1)
    p2_recv_range = range(1, len(p2_recv) + 1)

    # line plot of send offsets
    send_ax.set_title("per-cycle average send offsets")
    send_ax.plot(p1_send_range, p1_send, color='r', label='peer 1')
    send_ax.plot(p2_send_range, p2_send, color='b', label='peer 2')
    send_ax.set_ylabel("t in us")
    send_ax.set_xlabel("Index")
    send_ax.legend(loc='center right')
    send_ax.grid(True)
    # line plot of receive offsets
    recv_ax.set_title("per-cycle average receive offsets")
    recv_ax.plot(p1_recv_range, p1_recv, color='r', label='peer 1')
    recv_ax.plot(p2_recv_range, p2_recv, color='b', label='peer 2')
    recv_ax.set_ylabel("t in us")
    recv_ax.set_xlabel("Index")
    recv_ax.legend(loc='center right')
    recv_ax.grid(True)

    fig.tight_layout()
    fig.canvas.flush_events()

def main():

    args = sys.argv
    port_obsv   = args[args.index('-obsv')+1]    if '-obsv'  in args else ''
    port_peer1   = args[args.index('-peer1')+1]  if '-peer1' in args else ''
    port_peer2   = args[args.index('-peer2')+1]  if '-peer2' in args else ''
    measure_cnt = int(args[args.index('-measure')+1]) if '-measure'  in args else 100

    ser_obsv  = configure_serial(port_obsv)
    ser_peer1 = configure_serial(port_peer1)
    ser_peer2 = configure_serial(port_peer2)

    plt.ion()
    fig_obsv, (obsv_line_ax, obsv_pd_ax)   = plt.subplots(2, 1, figsize=(10, 6), sharex=False)
    fig_peer, (peer_line_ax, peer_diff_ax) = plt.subplots(2, 1, figsize=(10, 6), sharex=False)
    fig_send_recv, (send_ax, recv_ax)      = plt.subplots(2, 1, figsize=(10, 6), sharex=False)

    measured_delta = collections.deque(maxlen=measure_cnt)
    measure_index = 0
    new_cycle = True
    first_timestamp = 0
    last_timestamp = 0

    peer_comp_offsets = collections.deque(maxlen=measure_cnt)
    peer_real_offsets = collections.deque(maxlen=measure_cnt)

    systime1 = 0
    systime2 = 0

    peer1_send_offsets = collections.deque(maxlen=measure_cnt)
    peer2_send_offsets = collections.deque(maxlen=measure_cnt)

    peer1_recv_offsets = collections.deque(maxlen=measure_cnt)
    peer2_recv_offsets = collections.deque(maxlen=measure_cnt)

    while True:
        try:
            obsv_line = ser_obsv.readline(-1).decode().strip()
            if 'RISING' in obsv_line:
                measured_delta, first_timestamp, last_timestamp, new_cycle, measure_index = process_obsv(obsv_line, measured_delta, first_timestamp, last_timestamp,new_cycle, measure_index)
                print(obsv_line)
            if 'FALLING' in obsv_line:
                refresh_measure_plot(fig_obsv, obsv_line_ax, obsv_pd_ax, measured_delta)
                new_cycle = True
                """ if systime1 != 0 and systime2 != 0:
                    peer_real_offsets.append(abs(systime1 - systime2))
                    refresh_peer_plot(fig_peer, peer_line_ax, peer_diff_ax, peer_comp_offsets, peer_real_offsets)
                    systime1 = systime2 = 0 """
                refresh_peer_plot(fig_peer, peer_line_ax, peer_diff_ax, peer_comp_offsets, peer_real_offsets)
                refresh_send_recv_plot(fig_send_recv, send_ax, recv_ax, peer1_send_offsets, peer2_send_offsets, peer1_recv_offsets, peer2_recv_offsets)
                
            peer1_line = ser_peer1.readline(-1).decode().strip()
            if 'Offset to master with' in peer1_line:
                process_peer(peer1_line, peer_comp_offsets)
            """ if 'Current systime' in peer1_line:
                parts = peer1_line.split()
                systime1 = correlate_timestamp(int(parts[parts.index('systime')+1])) """
            if 'avg_send_offset = ' in peer1_line:
                parts = peer1_line.split()
                peer1_send_offsets.append(int(parts[parts.index('=')+1]) )
            if 'avg_recv_offset = ' in peer1_line:
                parts = peer1_line.split()
                peer1_recv_offsets.append(int(parts[parts.index('=')+1]) )

            peer2_line = ser_peer2.readline(-1).decode().strip()
            if 'Offset to master with' in peer2_line:
                process_peer(peer2_line, peer_comp_offsets)
            """ if 'Current systime' in peer2_line:
                parts = peer2_line.split()
                systime2 = correlate_timestamp(int(parts[parts.index('systime')+1])) """
            if 'avg_send_offset = ' in peer2_line:
                parts = peer2_line.split()
                peer2_send_offsets.append(int(parts[parts.index('=')+1]) )
            if 'avg_recv_offset = ' in peer2_line:
                parts = peer2_line.split()
                peer2_recv_offsets.append(int(parts[parts.index('=')+1]) )

        except KeyboardInterrupt:
            break
        except Exception as ex:
            print(ex)
            pass

    fig_obsv.savefig('./python_utils/export/figure_measure.png')
    fig_peer.savefig('./python_utils/export/figure_peer.png')
    fig_send_recv.savefig('./python_utils/export/send_receive_delays.png')
    plt.close(fig_obsv)
    plt.close(fig_peer)
    plt.close(fig_send_recv)
    ser_obsv.close()
    ser_peer1.close()
    ser_peer2.close()

if __name__ == "__main__":
    main()