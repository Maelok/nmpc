import math
import socket
import sys
import time
import ctypes

import nmpc
nmpc.init()
from nmpc import _cnmpc, state

import pygame
pygame.init()

pygame.joystick.init()
print pygame.joystick.get_count()
joystick = pygame.joystick.Joystick(0)
joystick.init()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 51000))
sock.sendall("sub sim/operation/override/override_planepath\n")
sock.sendall("set sim/operation/override/override_planepath [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]\n")
sock.sendall("sub sim/flightmodel/position/psi\n")  # yaw
sock.sendall("sub sim/flightmodel/position/theta\n")  # pitch
sock.sendall("sub sim/flightmodel/position/phi\n")  # roll
sock.sendall("sub sim/flightmodel/position/local_x\n")
sock.sendall("sub sim/flightmodel/position/local_y\n")
sock.sendall("sub sim/flightmodel/position/local_z\n")
sock.sendall("extplane-set update_interval 0.02\n")

sock.recv(1024)
sock.sendall("world-set -37.8136 144.9 200\n")
position_offset = [0, 0, 0]
time.sleep(1.0)
response = sock.recv(1024)
for line in response.split("\n"):
    if line.find("local_x") >= 0:
        position_offset[1] = float(line.split(" ")[-1])
    elif line.find("local_y") >= 0:
        position_offset[2] = -float(line.split(" ")[-1])
    elif line.find("local_z") >= 0:
        position_offset[0] = -float(line.split(" ")[-1])

print position_offset

TIMESTEP = 1.0/500.0  # 50Hz updates.
_cnmpc.nmpc_fixedwingdynamics_set_position(0, 0, 0)
_cnmpc.nmpc_fixedwingdynamics_set_velocity(20, 0, 0)
_cnmpc.nmpc_fixedwingdynamics_set_attitude(1, 0, 0, 0)
_cnmpc.nmpc_fixedwingdynamics_set_angular_velocity(0, 0, 0)
_cnmpc.nmpc_fixedwingdynamics_get_state(state)

control_vec = [0, 0, 0]

while 1:
    keys = pygame.event.get()
    axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
    axes[0] = -0.5*(axes[0]+0.239)
    axes[1] = -0.5*(axes[1]+0.239)
    control_vec = [
        (-(axes[3] - 0.35) * 0.8) * 19000,
        axes[1] - axes[0],
        axes[1] + axes[0]]

    # print control_vec

    nmpc.integrate(TIMESTEP, (ctypes.c_double * 3)(*control_vec))

    update = ""
    update += "set sim/flightmodel/position/local_x %.9f\n" \
        % (state.position[1] + position_offset[1])
    update += "set sim/flightmodel/position/local_y %.9f\n" \
        % -(state.position[2] + position_offset[2])
    update += "set sim/flightmodel/position/local_z %.9f\n" \
        % -(state.position[0] + position_offset[0])

    print repr(state)
    q = (state.attitude[3], -state.attitude[0], -state.attitude[1], -state.attitude[2])
    yaw = math.atan2(2.0 * (q[0] * q[3] + q[1] * q[2]), 1.0 - 2.0 * (q[2] ** 2.0 + q[3] ** 2.0))
    pitch = math.asin(2.0 * (q[0] * q[2] - q[3] * q[1]))
    roll = math.atan2(2.0 * (q[0] * q[1] + q[2] * q[3]), 1.0 - 2.0 * (q[1] ** 2.0 + q[2] ** 2.0))

    update += "set sim/flightmodel/position/psi %.6f\n" % math.degrees(yaw)
    update += "set sim/flightmodel/position/theta %.6f\n" % math.degrees(pitch)
    update += "set sim/flightmodel/position/phi %.6f\n" % math.degrees(roll)

    sock.sendall(update)
    time.sleep(TIMESTEP)
