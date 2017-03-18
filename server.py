import socket
import select
import struct
import time
from math import sqrt

UDP_IP = "0.0.0.0"
UDP_PORT = 6666

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(0)
sock.settimeout(5)
sock.bind((UDP_IP, UDP_PORT))

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

        self.speed = 0

    def __str__(self):
        return "[chkpt] ride_id=%d geo: n=%f e=%f ; ts=%ds accel m/s2: X=%.2f Y=%.2f Z=%.2f ; accel_overall=%.2fm/s2" % (self.ride_id, self.geo_coord[0], self.geo_coord[1], self.timestamp, self.accel_x_mps, self.accel_y_mps, self.accel_z_mps, self.accel_overall)

class Drive:
    def __init__(self, avgspeed, avgaccel, kilometers, starttime, endtime):
        self.avgspeed = avgspeed
        self.avgaccel = avgaccel
        self.kilometers = kilometers
        self.starttime = starttime
        self.endtime = endtime

    def __str__(self):
        return "[drive] avgspeed=%fm/s avgaccel=%fm/s2 kilometers=%fkm starttime=%ds endtime=%ds" % (self.avgspeed, self.avgaccel, self.kilometers, self.starttime, self.endtime)

accel_interval = 1 # s
checkpoints = []
drives = []

while True:
    numvals = 7 # values
    intsize = 4 # bytes per value

    try:
        data, addr = sock.recvfrom(numvals * intsize)

        [ts_delta, counter, accel_x_mg, accel_y_mg, accel_z_mg, ride_counter, ride_id] = [struct.unpack("i", data[(i*intsize):(i*intsize+intsize)])[0] for i in range(len(data)/intsize)]

        geo_coord = (47.25, 9.22) # N,E for St. Gallen
        timestamp = int(time.time())

        checkpoint = Checkpoint(ride_id, geo_coord, timestamp, accel_x_mg, accel_y_mg, accel_z_mg)
        print checkpoint
        checkpoints.append(checkpoint)
    except socket.timeout:
        # end drive
        if len(checkpoints) >= 2:
            # update speeds
            for ci in range(0, len(checkpoints)):
                checkpoints[ci].speed = checkpoints[ci].accel_overall * accel_interval

            avgspeed = sum(map(lambda x: x.speed, checkpoints)) / len(checkpoints) # m/s
            avgaccel = sum(map(lambda x: x.accel_overall, checkpoints)) / len(checkpoints) # m/s2
            starttime = checkpoints[0].timestamp # s
            endtime = checkpoints[-1].timestamp  # s
            kilometers = float((endtime - starttime) * avgspeed) / 1000 # km

            drive = Drive(avgspeed, avgaccel, kilometers, starttime, endtime)
            print drive
            drives.append(drive)

        # clear
        checkpoints = []
