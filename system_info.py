from wifi_management import WifiManagement
from pydispatch import dispatcher
import os
import psutil
import eventlet
import subprocess

class SystemInfo:
	def __init__(self):
		self.wifiManagement = WifiManagement()
		self.update_thread = eventlet.spawn(self.update)
		self.latestInfo = None

	def get(self):
		return self.latestInfo

	def processInfo(self):
		try:
			self.latestInfo = {
				'cpu': int(psutil.cpu_percent()),
				'ram': int(psutil.virtual_memory().percent),
				'disk': self.get_disk_usage(),
				'temperature': self.get_temperature(),
				'wifi_ssid': self.wifiManagement.get_current_ssid(),
				'wifi_signal': self.wifiManagement.get_signal_strength()
			}
		except:
			print("Failed to get system info!")

	def update(self):
		# Broadcast the system info on a set interval
		while True:
			self.processInfo()
			dispatcher.send(signal="systemInfoUpdate")
			eventlet.sleep(2)

	def get_disk_usage(self):
		"""Get the disk usage percentage."""
		return int(psutil.disk_usage('/').percent)

	def get_temperature(self):
		"""Get the temperature of the CPU."""
		try:
			# For Raspberry Pi
			temp_file = '/sys/class/thermal/thermal_zone0/temp'
			if os.path.exists(temp_file):
				with open(temp_file, 'r') as f:
					temp = float(f.read()) / 1000
					return round(temp, 2)
		except Exception as e:
			print(f"Exception getting temperature: {e}")
		return None

