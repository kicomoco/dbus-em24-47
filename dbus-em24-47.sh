#!/bin/bash

# remove comment for easier troubleshooting
#set -x

. /opt/victronenergy/serial-starter/run-service.sh

# start -x -s $tty
app="python /opt/victronenergy/dbus-em24-47/dbus-em24-47.py"
args="/dev/$tty"
start $args
