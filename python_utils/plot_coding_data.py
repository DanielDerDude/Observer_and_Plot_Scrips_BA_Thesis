import sys
import matplotlib.pyplot as plt
import numpy as np
import collections
import os
from subprocess import Popen, PIPE

#
# Run:
# `python ../python_utils/plot_coding_data.py -p COM1 COM2 COM3 ...            # -n followed by a list of the ports connected to the esp devboard
#

dequeue_len = 1000
baudrate    = 921600

relay_file = '.\\export\\coding_plot\\temp.txt'

class native_node:
    
    def __init__(self, port):
        self.port            = port
        self.process         = Popen(['python', 'read_port.py', port, str(baudrate)], stdin=PIPE, stdout=PIPE, stderr=PIPE)        
        self.send_natPckt    = collections.deque(maxlen=dequeue_len)       # sequence numbers of transmitted native packets
        self.recv_natPckt    = collections.deque(maxlen=dequeue_len)       # sequecne numbers of sucessfully decoded packets 
        self.encRcvCnt       = 0                                           # number of total received broadcasts
        self.decInstCnt      = 0                                           # number of instantly decoded packets
        self.decCashCnt      = 0                                           # number of decoded packets from cash
        self.decRedunCnt     = 0                                           # number of redundant decodings
        self.PcktCntInCash   = 0                                           # 
        self.PcktsMissing    = collections.deque(maxlen=dequeue_len)
        self.shutdown        = 0                                           # flag indicating if peer has shutdown
    
    def parse_values(self):
        try:
            
            line = self.process.stdout.readline().decode().strip()
            if line:
                #print(self.port + ': ' + line)
                return update_relay(self, line)
            
            error = self.process.stderr.readline().decode().strip()
            if error:    
                print('ERROR ' + self.port + ': ' + error)
        
        except Exception as e:
            return False

class relay_node:
    
    def __init__(self, port):
        self.port               = port
        self.process            = Popen(['python', 'read_port.py', port, str(baudrate)], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        self.enc_natPckt        = collections.deque(maxlen=dequeue_len)     # sequence numbers of received native packets
        self.EncTransPerNat     = collections.deque(maxlen=dequeue_len)     # list with number of encoded broadcasts per natural packet
        self.recv_natPckt       = collections.deque(maxlen=dequeue_len)
        self.encCnt             = 0                                         # number of encoded packets
        self.encCntPerBrd       = collections.deque(maxlen=dequeue_len)
        self.retransCnt         = 0                                         # retransmission counter
        self.EncMissing         = collections.deque(maxlen=dequeue_len)
        self.BloomSize          = collections.deque(maxlen=dequeue_len)
        self.CumulSize          = collections.deque(maxlen=dequeue_len)
        self.ReportSavings      = 0
        self.shutdown           = 0                                         # flag indicating if peer has shutdown

    def parse_values(self):
        try:
            
            line = self.process.stdout.readline().decode().strip()
            if line:
                #print(self.port + ': ' + line)
                return update_relay(self, line)
            
            error = self.process.stderr.readline().decode().strip()
            if error:    
                print('ERROR ' + self.port + ': ' + error)
        
        except Exception as e:
            return False

def update_relay(self, line):
    if not isinstance(self, relay_node):
        raise TypeError('self is not an instance native node')

    if 'Received native packet' in line:
        parts = line.split()
        seqnum = abs(int(parts[parts.index('packet')+1]))
        self.recv_natPckt.append(seqnum)
        self.EncMissing.append(seqnum)
        return True
    
    if 'Encoded packets [' in line:
        parts = line.split()
        self.encCnt+=1
        
        seqnum1 = abs(int(parts[parts.index('[')+1]))
        seqnum2 = abs(int(parts[parts.index('[')+2]))
        if seqnum1 not in self.enc_natPckt:
            self.enc_natPckt.append(seqnum1)
            self.EncTransPerNat.append(self.encCnt)
        if seqnum2 not in self.enc_natPckt:
            self.enc_natPckt.append(seqnum2)
            self.EncTransPerNat.append(self.encCnt)

        self.encCntPerBrd.append(len(self.enc_natPckt))

        if seqnum1 in self.EncMissing:
            self.EncMissing.remove(seqnum1)
        
        if seqnum2 in self.EncMissing:
            self.EncMissing.remove(seqnum2)

        return True

    if 'Number of retransmissions:' in line:
        parts = line.split()
        cnt = abs(int(parts[parts.index('retransmissions:')+1]))
        self.retransCnt += cnt
        return True
    
    if 'Received reception report -' in line:
        parts = line.split()
        bytes_bloom  = abs(int(parts[parts.index('data_lenght')+1]))
        packet_count = abs(int(parts[parts.index('packet_count')+1]))
        bytes_normal_report = 1 + packet_count*2 + 2
        self.BloomSize.append(bytes_bloom)
        self.CumulSize.append(bytes_normal_report)
        self.ReportSavings += (bytes_normal_report - bytes_bloom)
        return True

    if 'initiating shutdown task' in line:
        self.shutdown = 1
    
    return False

def update_native(self, line):
    if not isinstance(self, native_node):
        raise TypeError('self is not an instance native node')
    
    if 'Received encoded packet' in line:
        self.encRcvCnt += 1
        return True

    if 'Commissioned native packet' in line:
        parts = line.split()
        seqnum = abs(int(parts[parts.index('packet')+1]))
        self.send_natPckt.append(seqnum)
        return True

    if 'Decoded packet' in line:
        parts = line.split()
        seqnum = abs(int(parts[parts.index('packet')+1]))

        self.recv_natPckt.append(seqnum)
        self.decInstCnt += 1
        return True
    
    if 'Decoded cashed packet' in line:
        parts = line.split()
        seqnum = abs(int(parts[parts.index('packet')+1]))
        self.recv_natPckt.append(seqnum)
        self.decCashCnt += 1
        self.PcktCntInCash -= 1
        return True
    
    if 'Decoding redundant' in line:
        self.decRedunCnt += 1
        return True
    
    if 'Decoding failed - missing packets' in line:
        self.PcktCntInCash += 1

    if 'initiating shutdown task' in line:
        self.shutdown = 1

    return False

def update_relay_coding_plot(fig_relay_coding_gain, RelTransAx, RelCodGainvAx, relay, native_cnt):
    RelTransAx.clear()
    RelCodGainvAx.clear()

    x_trans = np.arange(1, len(relay.EncTransPerNat)+1, 1, dtype=np.int64)
    y_trans = np.asarray(relay.EncTransPerNat, dtype=np.int64)

    x_cod_gain = np.arange(1, len(relay.encCntPerBrd)+1, 1, dtype=np.int64)
    y_cod_gain = np.asarray(relay.encCntPerBrd, dtype=np.float32) / np.arange(1, len(relay.encCntPerBrd)+1, 1, dtype=np.int64)

    cod_gain_avg = 0 if len(y_cod_gain)== 0 else sum(y_cod_gain) / len(y_cod_gain)
    cod_gain_ideal = native_cnt/(native_cnt-1)

    RelTransAx.set_title('transmissions at the relay node with ' + str(native_cnt) + ' native nodes')
    RelTransAx.plot(x_trans, y_trans, 'b-', label='measured')
    RelTransAx.plot(x_trans, x_trans/cod_gain_ideal, 'g--', label='ideal')
    RelTransAx.plot(x_trans, x_trans, 'r--', label='no encoding')
    RelTransAx.set_ylabel('broadcast transmissions')
    RelTransAx.set_xlabel('number of encoded native packets')
    RelTransAx.legend(loc='lower right')
    RelTransAx.grid(True)
    
    RelCodGainvAx.set_title('course of coding gain at relay node with ' + str(native_cnt) + ' native nodes')
    RelCodGainvAx.plot(x_cod_gain, y_cod_gain, 'b-', label='measured')
    #RelCodGainvAx.axhline(cod_gain_avg, color='r', linestyle='--', label=f'average = {round(cod_gain_avg, 2)}')
    RelCodGainvAx.axhline(cod_gain_ideal, color='g', linestyle='--', label=f'ideal = {round(cod_gain_ideal, 2)}')
    RelCodGainvAx.set_ylabel('coding gain')
    RelCodGainvAx.set_xlabel('encoded native packets')
    RelCodGainvAx.legend(loc='upper right')
    RelCodGainvAx.grid(True)

    fig_relay_coding_gain.tight_layout()
    fig_relay_coding_gain.canvas.flush_events()

def update_relay_report_plot(fig_relay_recep_rep , RecepTransAx, relay, native_cnt):
    RecepTransAx.clear()
    RecepTransAx.set_title('reception report savings over one cycle with ' + str(native_cnt) + ' native nodes')

    descr = ['average bloom filter\nreception report size', 'average cumulative\nreception report size', 'total savings\nover one cycle']
    bar_color = ['tab:blue', 'tab:red', 'tab:green']

    avg_size_bloom = round( sum(relay.BloomSize) / len(relay.BloomSize), 2)
    avg_size_cumul = round( sum(relay.CumulSize) / len(relay.CumulSize), 2)

    data = (avg_size_bloom, avg_size_cumul, relay.ReportSavings)

    rects = RecepTransAx.bar(descr, data, width=0.5, color=bar_color)
    RecepTransAx.bar_label(rects)
    #saving = relay.ReportData[1]-relay.ReportData[0]

    #RecepTransAx.bar(descr[0], saving, width=0.5, color='tab:orange', label='savings', bottom =relay.ReportData[0])
    RecepTransAx.set_ylabel('size [bytes]')

    fig_relay_recep_rep.tight_layout()
    fig_relay_recep_rep.canvas.flush_events()

def update_native_bar_plot(fig_native_bar_plot, NatBarAx, native_nodes):
    NatBarAx.clear()

    NatBarAx.set_title('reception statistics of native peers')

    x = np.arange(len(native_nodes))
    width = 0.2

    attributes       = ['encRcvCnt', 'decInstCnt', 'decCashCnt', 'decRedunCnt', 'PcktCntInCash']
    attribute_labels = ['received broadcasts', 'decoded instantly', 'decoded from cash', 'decoding redundant', 'decoding pending']
    colors           = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red','tab:purple']

    for i, attribute in enumerate(attributes):
            data = [getattr(node, attribute) for node in native_nodes]
            offset = width * i
            rects = NatBarAx.bar(x + offset, data, width, label=attribute_labels[i], color=colors[i])
            NatBarAx.bar_label(rects, padding=3)

    NatBarAx.set_ylabel('count')
    NatBarAx.set_xticks(x + width * (len(attributes) - 1) / 2)
    NatBarAx.set_xticklabels([f'node {i+1}' for i in range(len(native_nodes))])
    NatBarAx.legend(loc='upper right')

    fig_native_bar_plot.tight_layout()
    fig_native_bar_plot.canvas.flush_events()

def save_relay_values_to_file(relay, native_cnt):

    transm = np.asarray(relay.EncTransPerNat, dtype=np.int64)
    cod_gain      = np.asarray(relay.encCntPerBrd, dtype=np.float32) / np.arange(1, len(relay.encCntPerBrd)+1, 1, dtype=np.int64)

    cod_gain_avg = 0 if len(cod_gain)== 0 else sum(cod_gain) / len(cod_gain)
    cod_gain_ideal = native_cnt/(native_cnt-1)

    write_values_to_file(relay_file, transm, cod_gain, cod_gain_avg, cod_gain_ideal, native_cnt)

def write_values_to_file(filename, transm, cod_gain, cod_gain_avg, cod_gain_ideal, native_cnt):
    if not os.path.exists(filename):
        with open(filename, 'w') as file:
            file.write("")

    with open(filename, 'r') as file:
        lines = file.readlines()

    start_index = None
    for i, line in enumerate(lines):
        if f"Values for {native_cnt} native nodes:" in line:
            start_index = i
            break

    if start_index is not None:
        end_index = start_index
        while end_index < len(lines) and "Values for " not in lines[end_index]:
            end_index += 1
        del lines[start_index:end_index]

    with open(filename, 'w') as file:
        file.writelines(lines)

        file.write(f"Values for {native_cnt} native nodes:\n")

        file.write("\ntransm: ")
        np.savetxt(file, transm.reshape(1, -1), delimiter=',', fmt='%d')
        file.write("\ncod_gain: ")
        np.savetxt(file, cod_gain.reshape(1, -1), delimiter=',', fmt='%.6f')
        file.write("\ncod_gain_avg: %.6f\n" % cod_gain_avg)
        file.write("cod_gain_ideal: %.6f\n\n" % cod_gain_ideal)

def main():

    args = sys.argv
    ports   = args[args.index('-p')+1 :]  if '-p' in args else ''

    node_cnt = len(ports)

    relay = relay_node(ports[0])

    native_nodes = []
    for port in ports:
        if port != ports[0]:  # exclude the port used by the relay node
            native = native_node(port)
            native_nodes.append(native)

    print('\nPress the reset button on one of the ESP32 boards...')

    # plots
    plt.ion()
    fig_relay_coding_gain , (RelTransAx, RelCodGainvAx) = plt.subplots(2, 1, figsize=(10, 6), sharex=False)
    fig_relay_recep_rep , RecepTransAx = plt.subplots(figsize=(10, 6))
    fig_native_coding_gain, NatBarAx  = plt.subplots(figsize=(10, 6))

    start = False       
    last = 0

    while True:
        try:
            if relay.parse_values():
                update_relay_coding_plot(fig_relay_coding_gain, RelTransAx, RelCodGainvAx, relay, len(native_nodes))
                if not start:
                    print('\nStarting to collect data')
                    start = True
                
                if last < relay.ReportSavings:
                    update_relay_report_plot(fig_relay_recep_rep, RecepTransAx, relay, len(native_nodes))
                    last = relay.ReportSavings
                if relay.shutdown:
                    break
            
            shutdown_cnt = relay.shutdown

            """ native_parse_hit = True
            for native in native_nodes:
                hit = native.parse_values()
                native_parse_hit = native_parse_hit and hit
                shutdown_cnt += native.shutdown

            if native_parse_hit:
                update_native_bar_plot(fig_native_coding_gain, NatBarAx, native_nodes) """

            if shutdown_cnt == node_cnt-1:            # every node has shut down
                #update_relay_coding_plot(fig_relay_coding_gain, RelTransAx, RelCodGainvAx, relay, , len(native_nodes))
                #update_native_bar_plot(fig_native_coding_gain, NatBarAx, native_nodes)
                break

        except KeyboardInterrupt:
            print('Aborted data collection')
            break
        except Exception as ex:
            print(ex)
            pass

    print('\n Cycle finished.')

    while True:
        try:
            plt.show(block=True)
        except KeyboardInterrupt:
            break

    relay.process.terminate()
    for node in native_nodes:
        node.process.terminate() 

    save_relay_values_to_file(relay, len(native_nodes))

    print('Done.')
    
    sys.exit()

if __name__ == '__main__':
    main()