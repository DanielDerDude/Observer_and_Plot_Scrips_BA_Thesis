import sys
import serial
import re

# idea was taken from: https://stackoverflow.com/questions/27484250/python-pyserial-read-data-form-multiple-serial-ports-at-same-time

def configure_serial(port, baudrate):
    ser = serial.Serial()
    ser.baudrate = 115200
    ser.port = port
    ser.parity = 'N'
    ser.timeout = 0.0001
    
    try:
        ser.open()
    except Exception as e:
        sys.stderr.write(e)
        return None

    ser.baudrate = baudrate
    return ser

def escape_ansi(line):
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)

ser = None
while True:
    ser = configure_serial(sys.argv[1], sys.argv[2])
    if ser != None:
        break
    ser.close()

while True:  # The program never ends... will be killed when master is over.

    line = ser.readline()
    if line:
        try:
            line = line.decode().strip()            # read line
        except Exception as e:
            continue
        
        output = escape_ansi(line)              # clean from ansi escape codes
        if output:
            sys.stdout.write(output+ '\n')          # write output to stdout
            sys.stdout.flush()                      # flush output
