import configparser
import os
import subprocess
import socket
import requests
import re
import threading
import pywifi
import time
from pywifi import const


class WifiManagement:
	def __init__(self, interface="wlan0", config_file="config.cfg"):
		self.config = self.load_config(config_file)

		self.ssid = self.config["Hotspot"]["HotspotSSID"]
		self.password = self.config["Hotspot"]["HotspotPassword"]
		self.channel = self.config["Hotspot"]["HotspotChannel"]

		self.interface = interface
		self.hostapd_conf_path = "/etc/hostapd/hostapd.conf"
		self.dnsmasq_conf_path = "/etc/dnsmasq.conf"

		# Initialize PyWiFi and retrieve the interface
		self.wifi = pywifi.PyWiFi()
		self.iface = self._get_interface()

	def load_config(self, config_file):
		config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)
		if not os.path.exists(config_path):
			raise FileNotFoundError(f"Configuration file not found: {config_path}")
		config = configparser.ConfigParser()
		config.read(config_path)
		return config

	def _get_interface(self):
		"""Retrieve the Wi-Fi interface using PyWiFi."""
		interfaces = self.wifi.interfaces()
		if not interfaces:
			raise RuntimeError("No Wi-Fi interfaces detected. Ensure the interface is enabled and in managed mode.")
		for iface in interfaces:
			if iface.name() == self.interface:
				return iface
		raise ValueError(f"Interface {self.interface} not found.")

	def create_hostapd_conf(self):
		"""Create a hostapd configuration file."""
		hostapd_conf = [
			f"interface={self.interface}",
			"driver=nl80211",
			f"ssid={self.ssid}",
			"hw_mode=g",
			f"channel={self.channel}",
			"auth_algs=1",
			"wpa=2",
			f"wpa_passphrase={self.password}",
			"wpa_key_mgmt=WPA-PSK",
			"wpa_pairwise=CCMP",
			"rsn_pairwise=CCMP"
		]
		with open(self.hostapd_conf_path, "w") as f:
			f.write("\n".join(hostapd_conf) + "\n")
		print("Hostapd configuration created.")

	def create_dnsmasq_conf(self):
		"""Create a dnsmasq configuration file."""
		dnsmasq_conf = f"""
interface={self.interface}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
		"""
		with open(self.dnsmasq_conf_path, "w") as f:
			f.write(dnsmasq_conf.strip() + "\n")
		print("Dnsmasq configuration created.")

	def setup_interface(self):
		"""Configure the wlan0 interface for AP mode."""
		subprocess.run(["systemctl", "stop", "wpa_supplicant"], check=True)
		subprocess.run(["systemctl", "stop", "NetworkManager"], check=True)

		subprocess.run(["ifconfig", self.interface, "down"], check=True)
		subprocess.run(["iw", "dev", self.interface, "set", "type", "__ap"], check=True)
		subprocess.run(["ifconfig", self.interface, "up"], check=True)

		subprocess.run(["ifconfig", self.interface, "192.168.4.1", "netmask", "255.255.255.0"], check=True)
		print(f"Configured {self.interface} with static IP.")

	def start_services(self):
		"""Start hostapd and dnsmasq services."""
		subprocess.run(["systemctl", "restart", "dnsmasq"], check=True)
		subprocess.run(["systemctl", "restart", "hostapd"], check=True)
		print("Access point started.")

	def stop_services(self):
		"""Stop hostapd and dnsmasq services."""
		subprocess.run(["systemctl", "stop", "hostapd"], check=True)
		subprocess.run(["systemctl", "stop", "dnsmasq"], check=True)
		subprocess.run(["ifconfig", self.interface, "down"], check=True)
		print("Access point stopped.")

	def deactivate_hotspot_and_reconnect(self):
		"""Deactivate hotspot and connect to the appropriate SSID using wpa_supplicant."""
		print("Deactivating hotspot and reconnecting to Wi-Fi...")
		self.stop_services()
		
		# Bring the interface back to managed mode
		subprocess.run(["ifconfig", self.interface, "down"], check=True)
		subprocess.run(["iw", "dev", self.interface, "set", "type", "managed"], check=True)
		subprocess.run(["ifconfig", self.interface, "up"], check=True)

		# Restart wpa_supplicant and NetworkManager to connect based on priority
		subprocess.run(["systemctl", "restart", "wpa_supplicant"], check=True)
		subprocess.run(["systemctl", "restart", "NetworkManager"], check=True)

	def activate_hotspot(self):
		"""Activate the access point."""
		self.create_hostapd_conf()
		self.create_dnsmasq_conf()
		self.setup_interface()
		self.start_services()
		print(f"Access point '{self.ssid}' is now running on {self.interface}.")

	def is_hotspot_active(self):
		"""Check if the hotspot is currently active."""
		try:
			# Check if hostapd service is active
			hostapd_status = subprocess.run(
				["systemctl", "is-active", "hostapd"],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				text=True
			)
			dnsmasq_status = subprocess.run(
				["systemctl", "is-active", "dnsmasq"],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				text=True
			)

			# If both services are active, the hotspot is active
			return hostapd_status.stdout.strip() == "active" and dnsmasq_status.stdout.strip() == "active"
		except Exception as e:
			print(f"Error checking hotspot status: {e}")
			return False

	def get_current_ssid(self):
		"""Get the current SSID name of the connected Wi-Fi network."""
		try:
			if self.is_hotspot_active():
				return self.ssid

			result = subprocess.run(
				['iwgetid', '--raw', self.interface],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				text=True,
			)

			if result.returncode == 0:
				ssid = result.stdout.strip()
				return ssid if ssid else "None"
			return None
		except Exception as e:
			print(f"Error getting SSID: {e}")
			return None

	def get_current_ip(self):
		"""Get the current IP address of the connected Wi-Fi or Ethernet network."""
		interfaces = ['wlan0', 'eth0']  # First try wlan0, then eth0

		for interface in interfaces:
			try:
				result = subprocess.run(
					['ip', 'addr', 'show', interface],
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					text=True,
				)
				if result.returncode != 0:
					raise RuntimeError(f"Error getting IP address for {interface}: {result.stderr.strip()}")

				# Scan through the output for the IP address
				for line in result.stdout.splitlines():
					if line.strip().startswith("inet "):  # Look for the IPv4 address
						ip_address = line.split()[1].split('/')[0]
						if ip_address:
							return ip_address
				# If no IP is found for this interface, continue to the next one
			except Exception as e:
				print(f"Error getting IP address for {interface}: {e}")

		# If no IP is found on both interfaces, return None
		return None

	def is_internet_available(self, url="https://www.google.com", timeout=5):
		"""Check if there is a valid internet connection."""
		try:
			response = requests.head(url, timeout=timeout)
			return response.status_code == 200
		except requests.RequestException:
			return False

	def get_wifi_access_points(self, signal_threshold=30):
		"""Retrieve available Wi-Fi access points above a signal threshold using PyWiFi."""
		try:
			# Start scanning for Wi-Fi networks
			self.iface.scan()
			time.sleep(2)  # Allow time for scanning
			results = self.iface.scan_results()

			# Define the range for dBm values
			min_dbm = -100  # Very weak signal
			max_dbm = -30   # Excellent signal

			# Parse the scan results
			access_points = {}
			for ap in results:
				# Skip networks with no name (hidden SSIDs)
				if not ap.ssid.strip():
					continue

				# Convert dBm to percentage
				signal_strength = max(
					0,
					min(100, int(((ap.signal - min_dbm) / (max_dbm - min_dbm)) * 100))
				)

				# Only include strong signals above the threshold
				if signal_strength >= signal_threshold:
					if ap.ssid not in access_points:
						# Add new SSID to the dictionary
						access_points[ap.ssid] = {"ssid": ap.ssid, "signal_strength": signal_strength}
					else:
						# Update if the new signal is stronger
						if signal_strength > access_points[ap.ssid]["signal_strength"]:
							access_points[ap.ssid] = {"ssid": ap.ssid, "signal_strength": signal_strength}

			# Convert dictionary to sorted list
			sorted_access_points = sorted(
				access_points.values(),
				key=lambda x: x["signal_strength"],
				reverse=True
			)

			return sorted_access_points

		except Exception as e:
			print(f"Error getting Wi-Fi access points: {e}")
			return []

	def _get_interface(self):
		"""Retrieve the Wi-Fi interface using PyWiFi."""
		interfaces = self.wifi.interfaces()
		if not interfaces:
			raise RuntimeError("No Wi-Fi interfaces detected. Ensure the interface is enabled and in managed mode.")
		for iface in interfaces:
			if iface.name() == self.interface:
				return iface
		raise ValueError(f"Interface {self.interface} not found.")

	def connect_to_wifi(self, ssid, password):
		"""Connect to a Wi-Fi network, ensuring the hotspot is deactivated if running."""
		def wifi_task():
			try:
				# Check if already connected to the desired SSID
				current_ssid = self.get_current_ssid()
				if current_ssid == ssid:
					return True

				# Deactivate hotspot if it's active
				if self.is_hotspot_active():
					print("Hotspot is active. Deactivating it before connecting to Wi-Fi...")
					self.deactivate_hotspot_and_reconnect()

				# Wait for the interface to stabilize after transition
				print("Waiting for interface to stabilize...")
				time.sleep(5)  # Adjust if needed based on system behavior

				# Reinitialize PyWiFi to ensure it detects the interface
				self.wifi = pywifi.PyWiFi()
				self.iface = self._get_interface()

				# Initialize connection process
				print(f"Attempting to connect to Wi-Fi network: {ssid}")
				self.iface.disconnect()
				time.sleep(1)

				# Create a new Wi-Fi profile
				profile = pywifi.Profile()
				profile.ssid = ssid
				profile.auth = const.AUTH_ALG_OPEN
				profile.akm.append(const.AKM_TYPE_WPA2PSK)
				profile.cipher = const.CIPHER_TYPE_CCMP
				profile.key = password

				self.iface.remove_all_network_profiles()
				tmp_profile = self.iface.add_network_profile(profile)

				# Attempt to connect
				self.iface.connect(tmp_profile)
				start_time = time.time()

				while time.time() - start_time < 10:  # Timeout after 10 seconds
					if self.iface.status() == const.IFACE_CONNECTED:
						print(f"Successfully connected to {ssid}")
						return True
					time.sleep(1)

				print(f"Failed to connect to {ssid}")
				return False

			except Exception as e:
				print(f"Error connecting to Wi-Fi: {e}")
				return False

		# Run Wi-Fi connection logic in a separate thread
		thread = threading.Thread(target=wifi_task)
		thread.start()
		thread.join()

	def get_signal_strength(self):
		"""Get the WiFi signal strength as a percentage."""
		try:
			if self.is_hotspot_active():
				return 100

			result = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True)
			output = result.stdout

			# Use regex to find the signal level
			match = re.search(r'Signal level=(-?\d+)', output)
			if match:
				signal_dbm = int(match.group(1))

				# Define the range for dBm values
				min_dbm = -100  # Minimum signal level (very weak)
				max_dbm = -30   # Maximum signal level (excellent)

				# Calculate percentage
				percentage = max(0, min(100, int(((signal_dbm - min_dbm) / (max_dbm - min_dbm)) * 100)))
				return percentage
		except Exception as e:
			print(f"Exception getting WiFi signal strength: {e}")
		return "--"

# Example usage
if __name__ == "__main__":
	ap_manager = WifiManagement()
	try:
		#ap_manager.activate_hotspot()
		print(f"Connected SSID: {ap_manager.get_current_ssid()}")
		print(f"Current IP: {ap_manager.get_current_ip()}")
		print("Internet is available." if ap_manager.is_internet_available() else "No internet access.")
		#input("Hotspot is running. Press Enter to deactivate and reconnect to Wi-Fi...")
		#ap_manager.deactivate_hotspot_and_reconnect()
	except KeyboardInterrupt:
		ap_manager.deactivate_hotspot_and_reconnect()
