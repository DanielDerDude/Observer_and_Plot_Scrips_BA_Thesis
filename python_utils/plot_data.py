import sys
import serial
import os
import matplotlib.pyplot as plt
import numpy as np
import collections
import time
from datetime import datetime

#
# Run:
# `python ../python_utils/plot_data.py -obsv COMX -peer COMY` with COMX and COMY being the port of the observer and slave peer
#

def correlate_timestamp(timestamp):
    return timestamp, int(time.perf_counter_ns()/1e3)

def configure_serial(port):
    ser = serial.Serial()
    ser.baudrate = 921600
    ser.port = port
    ser.parity = 'N'
    ser.timeout = 0.0000000001

    try:
        ser.open()
    except Exception as e:
        print(e)
        sys.exit()

    ser.reset_input_buffer()
    return ser

def compute_cycle_durations(first_timestamp_rising, last_timestamp_rising, first_timestamp_rising_last_cycle, last_timestamp_rising_last_cycle, peer1_cycle_durations, peer2_cycle_durations):
    
    if first_timestamp_rising == 0 or last_timestamp_rising == 0 or first_timestamp_rising_last_cycle == 0 or last_timestamp_rising_last_cycle == 0: return

    cycle_dur1 = first_timestamp_rising - first_timestamp_rising_last_cycle
    cycle_dur2 = last_timestamp_rising  - last_timestamp_rising_last_cycle

    peer1_cycle_durations.append(cycle_dur1)
    peer2_cycle_durations.append(cycle_dur2)

    print('cycle duration peer1: ' + str(cycle_dur1))
    print('cycle duration peer2: ' + str(cycle_dur2))

def process_obsv_deviation(line, measured_delta, first_timestamp, last_timestamp, first_timestamp_old, last_timestamp_old, new_cycle, measure_index):
    # parse line
    timestamp = int(line.split()[-1])

    if new_cycle:
        max_offset = abs(last_timestamp - first_timestamp)
        if max_offset != 0: measured_delta.append(max_offset)
        print('found delta t = ' + str(max_offset))
        print('------------------')
        measure_index += 1
        
        first_timestamp_old = first_timestamp
        last_timestamp_old  = last_timestamp

        first_timestamp = timestamp
        new_cycle = False
    else:
        last_timestamp = timestamp

    return measured_delta, first_timestamp, last_timestamp, first_timestamp_old, last_timestamp_old, new_cycle, measure_index 

def process_peer_comp_offset(line, peer_offsets, peer_comp_offsets_time):
    parts = line.split()
    offset = abs(int(parts[parts.index('with')+1]))
    peer_offsets.append(offset)
    peer_comp_offsets_time.append(int(time.perf_counter_ns()/1e3))
    print('computed offset to master: '+str(offset))

def refresh_deviation_plot(fig, line_ax, pd_ax, measured_delta):
    line_ax.clear()
    pd_ax.clear()
    
    if len(measured_delta) <= 1: return

    y = np.asarray(measured_delta, dtype=np.int64)[1:]  # exclude the first element, it's garbage
    
    y_avg = sum(y) / len(y)
    y_min = min(y)
    y_max = max(y)

    x_range = range(1, len(y)+1)
    
    # line plot in the first subplot (ax1)
    line_ax.set_title("measured time deviation between peers")
    line_ax.plot(x_range, y, color='b')
    line_ax.axhline(y_avg, color='b', linestyle='--', label=f'avg: {int(y_avg)} [\u00b5s]')
    line_ax.axhline(y_min, color='r', linestyle='--', label=f'min: {int(y_min)} [\u00b5s]')
    line_ax.axhline(y_max, color='g', linestyle='--', label=f'max: {int(y_max)} [\u00b5s]')
    line_ax.set_ylabel("\u0394t [\u00b5s]")
    line_ax.set_xlabel("cycle index")
    line_ax.legend()
    line_ax.grid(True)

    # histogram in the second subplot (ax2)
    pd_ax.set_title("peer-offset distribution")
    pd_ax.hist(y, bins=50, color='blue', cumulative=False, density=True, alpha=0.7)
    pd_ax.set_ylabel("probability density")
    pd_ax.set_xlabel("\u0394t [\u00b5s]")
    pd_ax.grid(True)

    fig.tight_layout()
    fig.canvas.flush_events()

def refresh_offset_drift_plot(fig_offset, peer_systime_ax, diff_ax, peer_comp_offsets, peer_comp_offsets_time, peer1_systime, peer2_systime, fig_drift, drift_ax):
    peer_systime_ax.clear()
    diff_ax.clear()
    drift_ax.clear()
    
    if len(peer_comp_offsets) <= 1 or len(peer_comp_offsets_time) <= 1 or len(peer1_systime) <= 1 or len(peer2_systime) <= 1: return

    time_reference_point = peer1_systime[0][1] if peer1_systime[0][1] <= peer2_systime[0][1] else peer2_systime[0][1]

    p1_systime = np.asarray([x[0] for x in peer1_systime], dtype=np.int64)
    p2_systime = np.asarray([x[0] for x in peer2_systime], dtype=np.int64)
    p1_range   = np.asarray([y[1] for y in peer1_systime], dtype=np.int64) - time_reference_point
    p2_range   = np.asarray([y[1] for y in peer2_systime], dtype=np.int64) - time_reference_point

    p1_systime_lin_reg = np.poly1d(np.polyfit(p1_range, p1_systime, 1))
    p2_systime_lin_reg = np.poly1d(np.polyfit(p2_range, p2_systime, 1))

    if p1_systime_lin_reg[0] >= p2_systime_lin_reg[0]:                  # basically abs
        estim_offset_lin_reg = p1_systime_lin_reg - p2_systime_lin_reg 
    else:
        estim_offset_lin_reg = p2_systime_lin_reg - p1_systime_lin_reg 
    
    comp_offset       = np.asarray(peer_comp_offsets, dtype=np.int64)
    comp_offset_range = np.asarray(peer_comp_offsets_time, dtype=np.int64) - time_reference_point
    comp_lin_reg      = np.poly1d(np.polyfit(comp_offset_range, comp_offset, 1))

    cycle_durations   = [comp_offset_range[i+1] - comp_offset_range[i] for i in range(len(comp_offset_range)-1)]
    avg_cycle_duration= int(sum(cycle_durations)/len(cycle_durations))
    print('average cycle duration '+str(avg_cycle_duration))

    peer_systime_ax.set_title("Systime-Offsets to oldest Peer")
    peer_systime_ax.plot(comp_offset_range/1e6, comp_offset/1e3, 'r-', label='computed offset')
    #peer_systime_ax.plot(comp_offset_range, comp_lin_reg(comp_offset_range), 'r--', label='linear regression')
    peer_systime_ax.plot(comp_offset_range/1e6, estim_offset_lin_reg(comp_offset_range)/1e3, 'g--', label='estimiated offset')
    """ peer_systime_ax.plot(p1_range, p1_systime, 'or-', label='peer1 systime')
    peer_systime_ax.plot(p2_range, p2_systime, 'ob-', label='peer2 systime')
    peer_systime_ax.plot(p1_lin_reg, 'r--' , label='linear regression')
    peer_systime_ax.plot(p2_systime, 'ob-', label='peer1 systime')
    peer_systime_ax.plot(p2_lin_reg, 'b--' , label='linear regression') """
    peer_systime_ax.set_ylabel("\u0394t [ms]")
    peer_systime_ax.set_xlabel("time [s]")
    peer_systime_ax.legend(loc = 'lower right')
    peer_systime_ax.grid(True)
    
    estim_comp_difference = (comp_offset-estim_offset_lin_reg(comp_offset_range))/1e3

    diff_ax.set_title("Deviation Distribustion")
    #diff_ax.plot(comp_offset_range/1e6, abs(estim_offset_lin_reg(comp_offset_range)-comp_offset), color='g', label='time drift')
    diff_ax.hist(estim_comp_difference, bins=50, color='blue', cumulative=False, density=True, alpha=0.7)
    diff_ax.set_ylabel("probability density")
    diff_ax.set_xlabel("\u0394t [ms]")
    #diff_ax.legend()
    
    peer1_drift = (p1_systime_lin_reg[1]/p1_systime_lin_reg[0])*1e6
    peer2_drift = (p2_systime_lin_reg[1]/p2_systime_lin_reg[0])*1e6
    added_drift = peer1_drift + peer2_drift
    estim_drift = estim_offset_lin_reg[1]
    comp_drift  = comp_lin_reg[1]
    
    origin     = ['peer1', 'peer2', 'added', 'estimated', 'computed']
    drift_values  = [peer1_drift, peer2_drift, added_drift, estim_drift, comp_drift]
    
    for i in drift_values:
        print(str(i))

    drift_ax.set_title('clock drift comparison')
    drift_ax.bar(origin, drift_values)
    drift_ax.set_ylabel('clock drift [ppm]')
    
    fig_offset.tight_layout()
    fig_offset.canvas.flush_events()
    fig_drift.canvas.flush_events()

def refresh_api_plot(fig, send_ax, recv_ax, peer1_send_offsets, peer2_send_offsets, peer1_recv_offsets, peer2_recv_offsets):
    send_ax.clear()
    recv_ax.clear()

    p1_send = np.asarray(peer1_send_offsets, dtype=np.int64)[1:]
    p2_send = np.asarray(peer2_send_offsets, dtype=np.int64)[1:]
    p1_recv = np.asarray(peer1_recv_offsets, dtype=np.int64)[1:]
    p2_recv = np.asarray(peer2_recv_offsets, dtype=np.int64)[1:]

    p1_send_range = range(1, len(p1_send) + 1)
    p2_send_range = range(1, len(p2_send) + 1)
    p1_recv_range = range(1, len(p1_recv) + 1)
    p2_recv_range = range(1, len(p2_recv) + 1)

    # line plot of send offsets
    send_ax.set_title("per-cycle average send offsets")
    send_ax.plot(p1_send_range, p1_send, color='r', label='peer 1')
    send_ax.plot(p2_send_range, p2_send, color='b', label='peer 2')
    send_ax.set_ylabel("t [\u00b5s]")
    send_ax.set_xlabel("Cycle Index")
    send_ax.legend(loc='center right')
    send_ax.grid(True)
    # line plot of receive offsets
    recv_ax.set_title("per-cycle average receive offsets")
    recv_ax.plot(p1_recv_range, p1_recv, color='r', label='peer 1')
    recv_ax.plot(p2_recv_range, p2_recv, color='b', label='peer 2')
    recv_ax.set_ylabel("t [\u00b5s]")
    recv_ax.set_xlabel("Cycle Index")
    recv_ax.legend(loc='center right')
    recv_ax.grid(True)

    fig.tight_layout()
    fig.canvas.flush_events()

""" def refresh_cycle_drift_plot(fig, ax_cycle_dur, ax_drift, peer_real_offsets, peer1_cycle_durations, peer2_cycle_durations):
    ax_cycle_dur.clear()
    ax_drift.clear()

    if len(peer_real_offsets) <= 1 or len(peer1_cycle_durations) <= 1 or len(peer2_cycle_durations) <= 1: return
    
    p1_cycle_durs = np.asarray(peer1_cycle_durations, dtype=np.int64)
    p2_cycle_durs = np.asarray(peer2_cycle_durations, dtype=np.int64)
    p1_range = range(1, len(p1_cycle_durs) + 1)
    p2_range = range(1, len(p2_cycle_durs) + 1)
    p1_avg_cycle_duration = sum(p1_cycle_durs) / len(p1_cycle_durs)
    p2_avg_cycle_duration = sum(p2_cycle_durs) / len(p2_cycle_durs)
    
    total_avg_cycle_duration = int(( sum(peer1_cycle_durations)+sum(peer1_cycle_durations) ) / ( len(peer1_cycle_durations)+len(peer1_cycle_durations) ))
    real_offset_range = range(total_avg_cycle_duration, total_avg_cycle_duration*(len(peer_real_offsets)+1), total_avg_cycle_duration)
    
    coeff           = np.polyfit(real_offset_range, peer_real_offsets, 1)                             #linear regression of systime offsets between devices
    slope, intercept= np.polyfit(real_offset_range, peer_real_offsets, 1)
    lin_approx_func = np.poly1d(coeff)        

    print('slope =' + str((slope*1e6/intercept)*1e6))

    # line plot
    ax_cycle_dur.set_title("cycle durations of peers")
    ax_cycle_dur.plot(p1_range, p1_cycle_durs, color='r', label='peer 1')
    ax_cycle_dur.plot(p2_range, p2_cycle_durs, color='b', label='peer 2')
    ax_cycle_dur.axhline(total_avg_cycle_duration, color='r', linestyle='--', label=f'peer 1 avg: {int(total_avg_cycle_duration)} [\u00b5s]')
    ax_cycle_dur.axhline(p2_avg_cycle_duration, color='b', linestyle='--', label=f'peer 2 avg: {int(p2_avg_cycle_duration)} [\u00b5s]')
    ax_cycle_dur.set_ylabel("t [\u00b5s]")
    ax_cycle_dur.set_xlabel("Cycle Index")
    ax_cycle_dur.legend()
    ax_cycle_dur.grid(True)
    # line plot
    ax_drift.set_title("estimated clock drift")
    ax_drift.plot(real_offset_range, lin_approx_func(real_offset_range), color='r', label='peer 1')
    ax_drift.set_ylabel("ppm")
    ax_drift.set_xlabel("Cycle Index")
    ax_drift.legend(loc='center right')
    ax_drift.grid(True)

    fig.tight_layout()
    fig.canvas.flush_events() """

def main():

    args = sys.argv
    port_obsv   = args[args.index('-obsv')+1]    if '-obsv'  in args else ''
    port_peer1   = args[args.index('-peer1')+1]  if '-peer1' in args else ''
    port_peer2   = args[args.index('-peer2')+1]  if '-peer2' in args else ''
    measure_cnt = int(args[args.index('-measure')+1]) if '-measure'  in args else 100
    save_plots = True if '-save' in args else False

    ser_obsv  = configure_serial(port_obsv)
    ser_peer1 = configure_serial(port_peer1)
    ser_peer2 = configure_serial(port_peer2)

    plt.ion()
    fig_obsv, (obsv_line_ax, obsv_pd_ax)   = plt.subplots(2, 1, figsize=(10, 6), sharex=False)
    fig_peer, (peer_line_ax, peer_diff_ax) = plt.subplots(2, 1, figsize=(10, 6), sharex=False)
    fig_send_recv, (send_ax, recv_ax)      = plt.subplots(2, 1, figsize=(10, 6), sharex=False)
    fig_drift, drift_ax                    = plt.subplots(1, 1, figsize=(10, 6))

    measured_delta = collections.deque(maxlen=measure_cnt)
    measure_index = 0
    new_cycle = True
    first_timestamp_rising = 0
    last_timestamp_rising = 0

    first_timestamp_rising_last_cycle = 0
    last_timestamp_rising_last_cycle  = 0

    """ peer1_cycle_durations = collections.deque(maxlen=measure_cnt)
    peer2_cycle_durations = collections.deque(maxlen=measure_cnt) """

    peer_comp_offsets      = collections.deque(maxlen=measure_cnt)
    peer_comp_offsets_time = collections.deque(maxlen=measure_cnt)
    
    peer1_systime = collections.deque(maxlen=measure_cnt)
    peer2_systime = collections.deque(maxlen=measure_cnt)

    peer1_send_offsets = collections.deque(maxlen=measure_cnt)
    peer2_send_offsets = collections.deque(maxlen=measure_cnt)

    peer1_recv_offsets = collections.deque(maxlen=measure_cnt)
    peer2_recv_offsets = collections.deque(maxlen=measure_cnt)

    once = True
    subdir = ''

    while True:
        try:
            obsv_line = ser_obsv.readline(-1).decode().strip()
            if 'RISING' in obsv_line:
                measured_delta, first_timestamp_rising, last_timestamp_rising, first_timestamp_rising_last_cycle, last_timestamp_rising_last_cycle, new_cycle, measure_index = process_obsv_deviation(obsv_line, measured_delta, first_timestamp_rising, last_timestamp_rising, first_timestamp_rising_last_cycle, last_timestamp_rising_last_cycle, new_cycle, measure_index)
                print(obsv_line)
            if 'FALLING' in obsv_line:
                refresh_deviation_plot(fig_obsv, obsv_line_ax, obsv_pd_ax, measured_delta)                
                
                if not new_cycle: refresh_offset_drift_plot(fig_peer, peer_line_ax, peer_diff_ax, peer_comp_offsets, peer_comp_offsets_time, peer1_systime, peer2_systime, fig_drift, drift_ax)
                
                new_cycle = True
                refresh_api_plot(fig_send_recv, send_ax, recv_ax, peer1_send_offsets, peer2_send_offsets, peer1_recv_offsets, peer2_recv_offsets)
                
                """ if systime1 != 0 and systime2 != 0:
                    measure_time_diff = abs(systime1_measure_timestamp - systime2_measure_timestamp)
                    if systime1_measure_timestamp > systime2_measure_timestamp:
                        corrected_offset = abs((systime1 - measure_time_diff)- systime2)
                    else:
                        corrected_offset = abs(systime1- (systime2 - measure_time_diff))
                    peer_real_offsets.append(corrected_offset)
                    time_measured = systime1_measure_timestamp
                    peer_real_offsets_time.append(time_measured)
                    
                    systime1 = systime2 = 0 """


            peer1_line = ser_peer1.readline(-1).decode().strip()
            if 'Offset to master with' in peer1_line:
                process_peer_comp_offset(peer1_line, peer_comp_offsets, peer_comp_offsets_time)
            if 'Systime at' in peer1_line:
                parts = peer1_line.split()
                peer1_systime.append(correlate_timestamp(int(parts[parts.index('at')+1])))
            if 'avg_send_offset = ' in peer1_line:
                parts = peer1_line.split()
                peer1_send_offsets.append(int(parts[parts.index('=')+1]) )
            if 'avg_recv_offset = ' in peer1_line:
                parts = peer1_line.split()
                peer1_recv_offsets.append(int(parts[parts.index('=')+1]) )

            peer2_line = ser_peer2.readline(-1).decode().strip()
            if 'Offset to master with' in peer2_line:
                process_peer_comp_offset(peer2_line, peer_comp_offsets, peer_comp_offsets_time)
            if 'Systime at' in peer2_line:
                parts = peer2_line.split()
                peer2_systime.append(correlate_timestamp(int(parts[parts.index('at')+1])))
            if 'avg_send_offset = ' in peer2_line:
                parts = peer2_line.split()
                peer2_send_offsets.append(int(parts[parts.index('=')+1]) )
            if 'avg_recv_offset = ' in peer2_line:
                parts = peer2_line.split()
                peer2_recv_offsets.append(int(parts[parts.index('=')+1]) )

            if 'CONFIG: ' in peer1_line and once:
                parts = peer1_line.split()
                subdir = parts[parts.index('CONFIG:')+1]
                print("\nFetched CONFG: "+subdir+'\n')
            if 'RESETTING NETWORK' in peer1_line:
                plt.close(fig_obsv)
                plt.close(fig_peer)
                plt.close(fig_send_recv)
                ser_obsv.close()
                ser_peer1.close()
                ser_peer2.close()
                print('\nReset detected - aborting script\n')
                quit()

        except KeyboardInterrupt:
            break
        except Exception as ex:
            print(ex)
            pass
    
    if save_plots:
        parentdir = '.\\python_utils\\export'
        subdir += '_'+datetime.today().strftime('%Y-%m-%d')
        subdir = os.path.join(parentdir, subdir)
        if not os.path.exists(subdir):
            os.makedirs(subdir)
        fig_obsv.savefig(os.path.join(subdir, 'figure_measure.png'))
        fig_peer.savefig(os.path.join(subdir, 'figure_peer.png'))
        fig_send_recv.savefig(os.path.join(subdir, 'send_receive_delays.png'))
    plt.close(fig_obsv)
    plt.close(fig_peer)
    plt.close(fig_send_recv)
    ser_obsv.close()
    ser_peer1.close()
    ser_peer2.close()

if __name__ == "__main__":
    main()