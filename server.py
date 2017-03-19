import socket
import select
import struct
import time
import json, requests
from math import sqrt
from bokeh.client import push_session
from bokeh.driving import cosine
from bokeh.plotting import figure, curdoc
from bokeh.models import ColumnDataSource
import logging as log
import datetime

UDP_IP = "0.0.0.0"
UDP_PORT = 6666
ACCEL_INTERVAL = 0.1 # s
GET_STREAM_INTERVAL = ACCEL_INTERVAL * 1000 / 2 # ms
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

# plotting
fig_accel_time = figure(height=300, width=1024, x_axis_label="time s", y_axis_label="acceleration m/s^2")
fig_accel_time_l1 = fig_accel_time.line([i/10.0 for i in range(-100, 1)], [0 for i in range(101)], color="firebrick")

fig_speed_time = figure(height=300, width=1024, x_axis_label="time s", y_axis_label="speed m/s")
fig_speed_time_l1 = fig_speed_time.line([i/10.0 for i in range(-100, 1)], [0 for i in range(101)], color="blue")

session = push_session(curdoc())

# logging
logFile = open("log.txt", "a")

def get_log_ts():
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S ')

class Checkpoint:
    def __init__(self, ride_id, geo_coord, timestamp, accel_x_mg, accel_y_mg, accel_z_mg, accel_delta, ts_delta):
        self.ride_id = ride_id
        self.geo_coord = geo_coord
        self.timestamp = timestamp
        self.ts_delta = ts_delta

        g = 9.8
        self.accel_x_mps = abs(accel_x_mg * g / 1000)
        self.accel_y_mps = abs(accel_y_mg * g / 1000)
        self.accel_z_mps = abs(accel_z_mg * g / 1000)

        self.accel_overall = sqrt(self.accel_x_mps**2 + self.accel_y_mps**2)
        self.accel_overall = sqrt(self.accel_overall**2 + self.accel_z_mps**2)

        self.speed = self.accel_overall
        self.accel_delta = accel_delta

    def __str__(self):
        return "[chkpt] ride_id=%d geo: n=%.2f e=%.2f ; ts=%ds accel m/s2: X=%.2f Y=%.2f Z=%.2f ; accel_overall=%.2fm/s2 accel=%.2fm/s2 speed=%.2fm/s" % (self.ride_id, self.geo_coord[0], self.geo_coord[1], self.timestamp, self.accel_x_mps, self.accel_y_mps, self.accel_z_mps, self.accel_overall, self.accel_delta, self.speed)

class Drive:
    def __init__(self, checkpoints):
        self.avgspeed = sum(map(lambda c: c.speed, checkpoints)) / len(checkpoints) # m/s
        self.avgaccel = sum(map(lambda c: c.accel_delta, checkpoints)) / len(checkpoints) # m/s2
        self.starttime = checkpoints[0].timestamp # s
        self.endtime = checkpoints[-1].timestamp  # s
        self.kilometers = float((self.endtime - self.starttime) * self.avgspeed) / 1000 # km

    def __str__(self):
        return "[drive] avgspeed=%fm/s avgaccel=%fm/s2 kilometers=%fkm starttime=%ds endtime=%ds" % (self.avgspeed, self.avgaccel, self.kilometers, self.starttime, self.endtime)

def get_data():
    global stream_buffer
    global checkpoints

    next_y_accel = fig_accel_time_l1.data_source.data["y"][-1]
    next_y_speed = fig_speed_time_l1.data_source.data["y"][-1]

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
            accel_delta = 0

            g = 9.8
            accel_x_mps = abs(accel_x_mg * g / 1000)
            accel_y_mps = abs(accel_y_mg * g / 1000)
            accel_z_mps = abs(accel_z_mg * g / 1000)

            accel_overall = sqrt(accel_x_mps**2 + accel_y_mps**2)
            accel_overall = sqrt(accel_overall**2 + accel_z_mps**2)

            if len(checkpoints) > 0:
                prev_chkpt = checkpoints[-1]
                i = len(checkpoints) - 1 # index of prev_chkpt in checkpoints
                while i > 0 and ts_delta - prev_chkpt.ts_delta < 1000:
                    i = i - 1
                    prev_chkpt = checkpoints[i]
                    accel_delta = abs(accel_overall - prev_chkpt.accel_overall)

            checkpoint = Checkpoint(ride_id, geo_coord, timestamp,
                            accel_x_mg, accel_y_mg, accel_z_mg, accel_delta, ts_delta)
            checkpoints.append(checkpoint)
            print checkpoint
            logFile.write(get_log_ts() + str(checkpoint))

            next_y_accel = checkpoint.accel_delta
            next_y_speed = checkpoint.speed

            stream_buffer = ""
    except:
        if len(checkpoints) > 0 and int(time.time()) - checkpoints[-1].timestamp > 5:
            # end drive
            if len(checkpoints) > 1:
                drive = Drive(checkpoints)
                drives.append(drive)
                print drive
                logFile.write(get_log_ts() + str(drive))

                fake_data = True

                # send the data
                carAddress = json.loads(requests.get(url='https://insureride.net/api/v1/user').text)["1"]["CarAddress"]

                fakeEndTime = drive.endtime # s
                fakeAvgSpeed = drive.avgspeed * 3600.0 / 1000.0 # km/h
                fakeAvgAccel = drive.avgaccel # m/s2

                if fake_data:
                    fakeEndTime = drive.endtime + (drive.endtime - drive.starttime) * 1000 # s
                    fakeAvgSpeed = fakeAvgSpeed * 2 # km/h
                    fakeAvgAccel = fakeAvgAccel * 2 # m/s2

                print requests.post("https://insureride.net/api/v1/car/" + carAddress + "/drive", data = json.dumps({
                    "Kilometers": fakeAvgSpeed * (fakeEndTime - drive.starttime) / 3600.0, # km
                    "Avgspeed": fakeAvgSpeed, # km/h
                    "Avgaccel": fakeAvgAccel, # m/s2
                    "Starttime": drive.starttime,
                    "Endtime": fakeEndTime
                })).text

            # clear data points
            checkpoints = []
            logFile.write(get_log_ts() + "[clear_checkpoints]")

    fig_accel_time_l1.data_source.data["y"] = \
        fig_accel_time_l1.data_source.data["y"][1:] + [next_y_accel]

    fig_speed_time_l1.data_source.data["y"] = \
        fig_speed_time_l1.data_source.data["y"][1:] + [next_y_speed]

# receive streamed data
curdoc().add_periodic_callback(get_data, GET_STREAM_INTERVAL)

# open the bokeh document in a browser
session.show(fig_accel_time)
session.show(fig_speed_time)
session.loop_until_closed()
