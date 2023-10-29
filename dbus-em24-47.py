#!/usr/bin/python

SCRIPT_HOME = "/opt/victronenergy/dbus-e24-47"

import logging
import dbus
import os
import sys
sys.path.insert(1, os.path.join(os.path.dirname(__file__), f"{SCRIPT_HOME}/ext"))

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
#from settableservice import SettableService
from vedbus import VeDbusService
from pymodbus.exceptions import ModbusException
from pymodbus.client.sync import ModbusSerialClient
from pymodbus.transaction import ModbusRtuFramer
from pymodbus.pdu import ExceptionResponse
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.constants import Endian
from sys import exit
import math

VERSION = "v1.0"
SERVICE_NAME = 'com.victronenergy.grid.em2447'
DEVICE_INSTANCE_ID = 1024
FIRMWARE_VERSION = 0
HARDWARE_VERSION = 0
CONNECTED = 1

VOLTAGE_TEXT = lambda path,value: "{:.2f}V".format(value)
CURRENT_TEXT = lambda path,value: "{:.3f}A".format(value)
POWER_TEXT = lambda path,value: "{:.2f}W".format(value)
ENERGY_TEXT = lambda path,value: "{:.2f}kWh".format(value)

class Unit:
	def __init__(self, gettextcallback=None):
		self.gettextcallback = gettextcallback

VOLTAGE = Unit(VOLTAGE_TEXT)
CURRENT = Unit(CURRENT_TEXT)
POWER = Unit(POWER_TEXT)
ENERGY = Unit(ENERGY_TEXT)
NO_UNIT = Unit()

class PathDefinition:
	def __init__(self, unit=NO_UNIT, aggregatorClass=None, defaultValue=None):
		self.unit = unit
		self.aggregatorClass = aggregatorClass
		self.defaultValue = defaultValue

ENERGYMETER_PATHS = {
	'/Ac/Energy/Forward': PathDefinition(ENERGY, defaultValue=0),
	'/Ac/Energy/Reverse': PathDefinition(ENERGY, defaultValue=0),
	'/Ac/Power': PathDefinition(POWER, defaultValue=0),
	'/Ac/Current': PathDefinition(CURRENT, defaultValue=0),
	'/Ac/Voltage': PathDefinition(VOLTAGE, defaultValue=0),
	'/Ac/L1/Current': PathDefinition(CURRENT, defaultValue=0),
	'/Ac/L1/Energy/Forward': PathDefinition(ENERGY, defaultValue=0),
	'/Ac/L1/Energy/Reverse': PathDefinition(ENERGY, defaultValue=0),
	'/Ac/L1/Power': PathDefinition(POWER, defaultValue=0),
	'/Ac/L1/Voltage': PathDefinition(VOLTAGE, defaultValue=0),
#	'/Ac/L2/Current': PathDefinition(CURRENT, defaultValue=0),
#	'/Ac/L2/Energy/Forward': PathDefinition(ENERGY, defaultValue=0),
#	'/Ac/L2/Energy/Reverse': PathDefinition(ENERGY, defaultValue=0),
#	'/Ac/L2/Power': PathDefinition(POWER, defaultValue=0),
#	'/Ac/L2/Voltage': PathDefinition(VOLTAGE, defaultValue=0),
#	'/Ac/L3/Current': PathDefinition(CURRENT, defaultValue=0),
#	'/Ac/L3/Energy/Forward': PathDefinition(ENERGY, defaultValue=0),
#	'/Ac/L3/Energy/Reverse': PathDefinition(ENERGY, defaultValue=0),
#	'/Ac/L3/Power': PathDefinition(POWER, defaultValue=0),
#	'/Ac/L3/Voltage': PathDefinition(VOLTAGE, defaultValue=0),
	'/DeviceType': PathDefinition(NO_UNIT, defaultValue=47),
	'/ErrorCode': PathDefinition(NO_UNIT, defaultValue=0),
}

PORT = sys.argv[1]

logging.basicConfig()
logger = logging.getLogger("EM2447")
logger.setLevel(logging.INFO)

def read32int(address, multiplier):

	rr = readholding(address, 2)

	if rr is not None:

		decoder = BinaryPayloadDecoder.fromRegisters(
			rr.registers,
			byteorder=Endian.Big,
			wordorder=Endian.Little,
		)

		return decoder.decode_32bit_int()*multiplier

def read32intTriple(address, multiplier=1):

	rr = readholding(address, 6)

	if rr is not None:

		decoder = BinaryPayloadDecoder.fromRegisters(
			rr.registers,
			byteorder=Endian.Big,
			wordorder=Endian.Little,
		)

		return (
			decoder.decode_32bit_int()*multiplier,
			decoder.decode_32bit_int()*multiplier,
			decoder.decode_32bit_int()*multiplier
		)

def write16uint(address, value):

	builder = BinaryPayloadBuilder(byteorder=Endian.Big,wordorder=Endian.Little)
	builder.add_16bit_uint(value)
	payload = builder.build()
	writeholding(address, payload)

def read16uint(address):

	rr = readholding(address, 1)
	
	if rr is not None:

		decoder = BinaryPayloadDecoder.fromRegisters(
			rr.registers,
			byteorder=Endian.Big,
			wordorder=Endian.Little,
		)

		return decoder.decode_16bit_uint()

	return

class SystemBus(dbus.bus.BusConnection):
	def __new__(cls):
		return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SYSTEM)

class SessionBus(dbus.bus.BusConnection):
	def __new__(cls):
		return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SESSION)

def dbusConnection():

	return SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else SystemBus()

def writeholding(address, value):

	try:
		rr = client.write_registers(address, value, skip_encode=True, unit=1)
	except ModbusException as exc:
		print(f"Received ModbusException({exc}) from library")
		client.close()
		return

	if rr.isError():
		print(f"Received Modbus library error({rr})")
		client.close()
		return

def readholding(address, bytes):

	try:
		rr = client.read_holding_registers(address, bytes, unit=1)
	except ModbusException as exc:
		print(f"Received ModbusException({exc}) from library")
		client.close()
		return

	if rr.isError():
		print(f"Received Modbus library error({rr})")
		client.close()
		return

	if (isinstance(rr, ExceptionResponse)):
		print(f"Received Modbus library exception({rr}))")
		client.close()
		return

	return rr

client = ModbusSerialClient(
	method='rtu',
	port=PORT,
	baudrate=9600,
	bytesize=8,
	parity="N",
	stopbits=1,
)

class EM2447():
	def __init__(self, conn):
		super().__init__()
		self.service = VeDbusService(SERVICE_NAME, conn)
		self.service.add_mandatory_paths(
			__file__,
			VERSION,
			'dbus',
			DEVICE_INSTANCE_ID,
			0,
			"EM24 47 Energy Monitor",
			FIRMWARE_VERSION,
			HARDWARE_VERSION,
			CONNECTED
		)

		self._local_values = {}

		for path, defn in ENERGYMETER_PATHS.items():
			self.service.add_path(path, defn.defaultValue, gettextcallback=defn.unit.gettextcallback)

		client.connect()
		self.iterSinceNonPriority = 0

	def update(self):

		if self.iterSinceNonPriority > 10:
			forward = read32int(0x3E,1/10)
			if forward is not None:
				try:
					forward = forward #-self.forwardoffset
					print(f"Import: {forward}kWh")
					self._local_values["/Ac/Energy/Forward"] = forward
				except AttributeError:
					self.forwardoffset = forward

		voltage = read32intTriple(0x0,1/10)
		if voltage is not None:
			print(f"Voltage L1:{voltage[0]} L2:{voltage[1]} L3:{voltage[2]}")
			self._local_values["/Ac/L1/Voltage"] = voltage[0]
			if voltage[1]>0:
				self._local_values["/Ac/L2/Voltage"] = voltage[1]
			if voltage[2]>0:
				self._local_values["/Ac/L3/Voltage"] = voltage[2]

			amperage = read32intTriple(0xC,1/1000)
			if amperage is not None:
				print(f"Amperage L1:{amperage[0]} L2:{amperage[1]} L3:{amperage[2]}")
				self._local_values["/Ac/L1/Current"] = amperage[0]
				if voltage[1]>0:
					self._local_values["/Ac/L2/Current"] = amperage[1]
				if voltage[2]>0:
					self._local_values["/Ac/L3/Current"] = amperage[2]

			wattage = read32intTriple(0x12,1/10)
			if wattage is not None:
				wattageTotal = math.fsum(wattage)
				print(f"Wattage L1:{wattage[0]} L2:{wattage[1]} L3:{wattage[2]} Total:{wattageTotal}")
				self._local_values["/Ac/L1/Power"] = wattage[0]
				if voltage[1]>0:
					self._local_values["/Ac/L2/Power"] = wattage[1]
				if voltage[2]>0:
					self._local_values["/Ac/L3/Power"] = wattage[2]
				self._local_values["/Ac/Power"] = wattageTotal

			if self.iterSinceNonPriority > 10:
				kwh = read32intTriple(0x46,1/10)
				if kwh is not None:
					try:
						kwh0 = kwh[0] #-self.kwh0offset
						kwh1 = kwh[1] #-self.kwh1offset
						kwh2 = kwh[2] #-self.kwh2offset
						print(f"kWh L1:{kwh0} L2:{kwh1} L3:{kwh2}")
						self._local_values["/Ac/L1/Energy/Forward"] = kwh0
						if voltage[1]>0:
							self._local_values["/Ac/L2/Energy/Forward"] = kwh1
						if voltage[2]>0:
							self._local_values["/Ac/L3/Energy/Forward"] = kwh2
					except AttributeError:
						self.kwh0offset = kwh[0]
						self.kwh1offset = kwh[1]
						self.kwh2offset = kwh[2]
	
				reverse = read32int(0x5C,1/10)
				if reverse is not None:
					try:
						reverse = reverse #-self.reverseoffset
						print(f"Export: {reverse}kWh")
						phases = 1
						if voltage[1]>0:
							phases = phases+1
						if voltage[2]>0:
							phases = phases+1
						self._local_values["/Ac/Energy/Reverse"] = reverse
						self._local_values["/Ac/L1/Energy/Reverse"] = reverse/phases
						if voltage[1]>0:
							self._local_values["/Ac/L2/Energy/Reverse"] = reverse/phases
						if voltage[2]>0:
							self._local_values["/Ac/L3/Energy/Reverse"] = reverse/phases
					except AttributeError:
						self.reverseoffset = reverse

				self.iterSinceNonPriority = 0

			self.iterSinceNonPriority = self.iterSinceNonPriority + 1

		sys.stdout.flush()

	def publish(self):
		self.update()
		for k, v in self._local_values.items():
			self.service[k] = v
		return True

def run_em24():

	DBusGMainLoop(set_as_default=True)
	client.connect()

	rr = read16uint(0x000B)

	client.close()

	if rr is not None:
		if rr == 47:
			print("Valid EM24 Device Found")
		else:
			print("Attached device is not EM24 47")
			exit()
	else:
		exit()

	em24 = EM2447(dbusConnection())
	GLib.timeout_add(50, em24.publish)
	mainloop = GLib.MainLoop()
	mainloop.run()

	
if __name__ == "__main__":
	run_em24()
