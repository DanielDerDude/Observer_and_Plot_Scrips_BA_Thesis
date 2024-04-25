import sys
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import collections
import os

relay_file = '.\\export\\coding_plot\\relay_values_final.txt'

def update_relay_coding_plot(fig_relay_coding_gain, RelTransAx, RelCodGainvAx, data):
    RelTransAx.clear()
    RelCodGainvAx.clear()

    colors = ['y', 'b', 'g']

    max_len = 0
    packet_range = 150
    patches = []

    for i, node_cnt in enumerate(data):
        transm = data[node_cnt]['transm'][:packet_range]
        x_transm = np.arange(1, len(transm)+1, 1, dtype=np.int64)
        
        cod_gain = data[node_cnt]['cod_gain'][:packet_range]
        x_cod_gain = np.arange(1, len(cod_gain)+1, 1, dtype=np.int64)
        #cod_gain_ideal = data[node_cnt]['cod_gain_ideal']

        RelTransAx.plot(x_transm, transm, linestyle='-', color=colors[i])
        #RelTransAx.plot(x_transm, x_transm/cod_gain_ideal, linestyle='--', color=colors[i])
        
        RelCodGainvAx.plot(x_cod_gain, cod_gain, linestyle='-', color=colors[i], label='measured')
        RelCodGainvAx.axhline(data[node_cnt]['cod_gain_ideal'], linestyle='--', color=colors[i])
        
        patches.append(mpatches.Patch(color=colors[i], label=f'{node_cnt} native nodes'))

        if max_len < len(transm): max_len = len(transm)
        if max_len < len(cod_gain): max_len = len(cod_gain)

    nocoding = np.arange(1, max_len+1, 1, dtype=np.int64)
    RelTransAx.plot(nocoding, nocoding, 'r--', label='nomal broadcasting')
    RelCodGainvAx.axhline(1, linestyle='--', color='r')

    RelTransAx.set_title('transmissions at the relay node')
    RelTransAx.set_ylabel('broadcast transmissions')
    RelTransAx.set_xlabel('number of encoded native packets')
    

    RelCodGainvAx.set_title('course of coding gain at relay node')
    RelCodGainvAx.set_ylabel('coding gain')
    RelCodGainvAx.set_xlabel('encoded native packets')
    
    patches.append(mpatches.Patch(color='r', label='no encoding'))

    RelCodGainvAx.legend(handles=patches, loc='upper right')
    RelTransAx.legend(handles=patches, loc='lower right')

    RelCodGainvAx.grid(True)
    RelTransAx.grid(True)

    fig_relay_coding_gain.tight_layout()
    fig_relay_coding_gain.canvas.flush_events()

def parse_values_from_file(filename):
    data = {}
    with open(filename, 'r') as file:
        lines = file.readlines()

    node_cnt = None
    for line in lines:
        if line.startswith("Values for"):
            node_cnt = int(line.split()[2])
            data[node_cnt] = {}
        elif line.strip() and node_cnt is not None:
            key, values = line.strip().split(":")
            if key in ["transm", "cod_gain"]:
                data[node_cnt][key] = np.fromstring(values, sep=',', dtype=float)
            elif key in ["cod_gain_avg", "cod_gain_ideal"]:
                data[node_cnt][key] = float(values)

    return data

def main():

    data = parse_values_from_file(relay_file)

    fig_relay_coding_gain , (RelTransAx, RelCodGainvAx) = plt.subplots(2, 1, figsize=(10, 6), sharex=False)

    update_relay_coding_plot(fig_relay_coding_gain, RelTransAx, RelCodGainvAx, data)

    try:
        plt.show()
    except KeyboardInterrupt:
        print('Done.')
        sys.exit()

if __name__ == '__main__':
    main()