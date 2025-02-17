from wifi_management import WifiManagement
from pydispatch import dispatcher
import os
import psutil
import subprocess
import spidev
import threading
import time

class SystemInfo:
	def __init__(self, bStartThread=True):
		self.wifiManagement = WifiManagement()
		self.latestInfo = None
		if bStartThread:
			self.update_thread = threading.Thread(target=self.update)
			self.update_thread.start()

	def get(self):
		return self.latestInfo

	def processInfo(self):
		try:
			self.latestInfo = {
				'cpu': int(psutil.cpu_percent()),
				'ram': int(psutil.virtual_memory().percent),
				'disk': self.get_disk_usage(),
				'temperature': self.get_temperature(),
				'psi': self.get_psi(),
				'wifi_ssid': self.wifiManagement.get_current_ssid(),
				'wifi_signal': self.wifiManagement.get_signal_strength(),
				'hotspot_status': self.wifiManagement.is_hotspot_active()
			}
		except Exception as e:
			print(f"Error getting system info: {e}")

	def update(self):
		# Broadcast the system info on a set interval
		while True:
			self.processInfo()
			dispatcher.send(signal="systemInfoUpdate")
			time.sleep(2)

	def get_psi(self):
		# Read PSI from the ABPDANV150PGSA3 sensor
		try:
			spi = spidev.SpiDev()
			spi.open(0, 0)
			spi.max_speed_hz = 500000      # Adjust the speed as needed
			spi.mode = 0b00                # SPI mode (clock polarity and phase)
			response = spi.xfer2([0x00, 0x00])
			raw_value = (response[0] << 8) | response[1]
			spi.close()
			offset = 1600
			span = 9339 - offset  # 9339 - 1600 = 7739 counts
			scale = 90.0 / span   # ≈ 0.01163 PSI per count
			psi = (raw_value - offset) * scale
			return int(round(psi))
		except Exception as e:
			print(f"Exception getting PSI: {e}")
			return "---"

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
