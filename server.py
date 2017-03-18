import socket
import select
import struct
import time
from math import sqrt
import threading

UDP_IP = "0.0.0.0"
UDP_PORT = 6666
ACCEL_INTERVAL = 1 # s
NUM_STREAMED_VALS = 7 # values
STREAMED_VAL_SIZE = 4 # bytes per value

# socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(0)
sock.bind((UDP_IP, UDP_PORT))
stream_buffer = ""

# data
checkpoints = []
drives = []

class Checkpoint:
    def __init__(self, ride_id, geo_coord, timestamp, accel_x_mg, accel_y_mg, accel_z_mg):
        self.ride_id = ride_id
        self.geo_coord = geo_coord
        self.timestamp = timestamp

        g = 9.8
        self.accel_x_mps = abs(accel_x_mg * g / 1000)
        self.accel_y_mps = abs(accel_y_mg * g / 1000)
        self.accel_z_mps = abs(accel_z_mg * g / 1000)

        self.accel_overall = sqrt(self.accel_x_mps**2 + self.accel_y_mps**2)
        self.accel_overall = sqrt(self.accel_overall**2 + self.accel_z_mps**2)

        self.speed = self.accel_overall * ACCEL_INTERVAL

    def __str__(self):
        return "[chkpt] ride_id=%d geo: n=%.2f e=%.2f ; ts=%ds accel m/s2: X=%.2f Y=%.2f Z=%.2f ; accel_overall=%.2fm/s2" % (self.ride_id, self.geo_coord[0], self.geo_coord[1], self.timestamp, self.accel_x_mps, self.accel_y_mps, self.accel_z_mps, self.accel_overall)

class Drive:
    def __init__(self, avgspeed, avgaccel, kilometers, starttime, endtime):
        self.avgspeed = avgspeed
        self.avgaccel = avgaccel
        self.kilometers = kilometers
        self.starttime = starttime
        self.endtime = endtime

    def __str__(self):
        return "[drive] avgspeed=%fm/s avgaccel=%fm/s2 kilometers=%fkm starttime=%ds endtime=%ds" % (self.avgspeed, self.avgaccel, self.kilometers, self.starttime, self.endtime)

def set_interval(func, sec):
    def func_wrapper():
        set_interval(func, sec)
        func()
    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t

def get_data():
    global stream_buffer
    global checkpoints

    try:
        buffer_size = NUM_STREAMED_VALS * STREAMED_VAL_SIZE
        data, addr = sock.recvfrom(buffer_size - len(stream_buffer))
        stream_buffer += data

        if len(stream_buffer) == buffer_size:
            [ts_delta, counter, accel_x_mg, accel_y_mg, accel_z_mg, ride_counter, ride_id] = [ \
                struct.unpack("i", stream_buffer[(i*STREAMED_VAL_SIZE):(i*STREAMED_VAL_SIZE+STREAMED_VAL_SIZE)])[0] \
                    for i in range(len(stream_buffer)/STREAMED_VAL_SIZE) \
            ]

            geo_coord = (47.25, 9.22) # N,E for St. Gallen
            timestamp = int(time.time())

            checkpoint = Checkpoint(ride_id, geo_coord, timestamp, accel_x_mg, accel_y_mg, accel_z_mg)
            checkpoints.append(checkpoint)
            print checkpoint

            stream_buffer = ""
    except:
        # end drive
        if len(checkpoints) > 0 and int(time.time()) - checkpoints[-1].timestamp > 5:
            avgspeed = sum(map(lambda x: x.speed, checkpoints)) / len(checkpoints) # m/s
            avgaccel = sum(map(lambda x: x.accel_overall, checkpoints)) / len(checkpoints) # m/s2
            starttime = checkpoints[0].timestamp # s
            endtime = checkpoints[-1].timestamp  # s
            kilometers = float((endtime - starttime) * avgspeed) / 1000 # km

            drive = Drive(avgspeed, avgaccel, kilometers, starttime, endtime)
            drives.append(drive)
            print drive

            # clear
            checkpoints = []

# receive streamed data
set_interval(get_data, 1)
