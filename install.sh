#!/bin/bash

ln -s /data/dbus-em24-47/serial-starter.conf /data/conf/serial-starter.d/dbus-em24-47.conf
ln -s /data/dbus-em24-47/serial-starter-template /opt/victronenergy/service-templates/dbus-em24-47

chmod +x /opt/victronenergy/service-templates/dbus-em24-47/run
chmod +x /opt/victronenergy/service-templates/dbus-em24-47/log/run

ln -s /data/dbus-em24-47 /opt/victronenergy/dbus-em24-47

chmod +x /opt/victronenergy/dbus-em24-47/service/run
chmod +x /opt/victronenergy/dbus-em24-47/service/log/run

serialstarter_path="/data/conf/serial-starter.d"
serialstarter_file="$serialstarter_path/dbus-em24-47.conf"

if [ -f "$serialstarter_path" ]; then
	rm -f "$serialstarter_path"
fi

if [ ! -d "$serialstarter_path" ]; then
	mkdir "$serialstarter_path"
fi

if [ ! -f "$serialstarter_file" ]; then
	{
		echo "service em2447	dbus-em24-47"
		echo "alias rs485 cgwacs:fzsonick:imt:modbus:em2447"
	} > "$serialstarter_file"
fi


