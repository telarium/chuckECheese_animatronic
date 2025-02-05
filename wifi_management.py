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
		self.cached_access_point = None

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
		config.read(config_file)
		return config

	import subprocess

	def _get_interface(self):
		"""Retrieve the Wi-Fi interface without using PyWiFi."""
		try:
			# Execute the 'iw dev' command to list wireless interfaces
			output = subprocess.check_output(['iw', 'dev'], universal_newlines=True)
		except FileNotFoundError:
			raise RuntimeError("The 'iw' command is not found. Please install wireless tools.")

		interfaces = []
		current_iface = None
		for line in output.split('\n'):
			if line.strip().startswith('Interface'):
				current_iface = line.strip().split()[1]
				interfaces.append(current_iface)

		if not interfaces:
			raise RuntimeError("No Wi-Fi interfaces detected. Ensure the interface is enabled and in managed mode.")

		if self.interface in interfaces:
			return self.interface  # Return the interface name as a string
		else:
			raise ValueError(f"Interface '{self.interface}' not found among available interfaces: {interfaces}")

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

		# Re-initialize pywifi in managed mode
		self.wifi = pywifi.PyWiFi()
		self.iface = self._get_interface()

	def ensure_hostapd_unmasked(self):
		try:
			subprocess.run(["systemctl", "unmask", "hostapd"], check=True)
			print("hostapd service unmasked.")
		except subprocess.CalledProcessError as e:
			print(f"Error unmasking hostapd: {e}")


	def activate_hotspot(self):
		"""Activate the access point."""
		self.ensure_hostapd_unmasked()
		self.create_hostapd_conf()
		self.create_dnsmasq_conf()
		self.setup_interface()
		self.start_services()
		print(f"Access point '{self.ssid}' is now running on {self.interface}.")

	def is_interface_in_ap_mode(self):
		"""
		Returns True if self.interface is currently in AP mode
		based on 'iw dev <interface> info'.
		"""
		try:
			result = subprocess.run(
				["iw", "dev", self.interface, "info"],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				text=True,
				check=True
			)
			return "type AP" in result.stdout
		except subprocess.CalledProcessError as e:
			print(f"Error checking interface mode: {e}")
			return False

	def is_hotspot_active(self):
		"""Check if the hotspot is currently active: both services running and interface in AP mode."""
		try:
			# Check if hostapd and dnsmasq services are active
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

			services_active = (
				hostapd_status.stdout.strip() == "active" and
				dnsmasq_status.stdout.strip() == "active"
			)

			# Check if interface is in AP mode
			interface_is_ap = self.is_interface_in_ap_mode()

			return services_active and interface_is_ap
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
		"""
		Retrieve available Wi-Fi access points above a signal threshold
		by calling 'iw dev <interface> scan' directly. We parse the results,
		skip hidden SSIDs, keep only the strongest signal per SSID, and
		sort by signal strength descending.
		"""
		try:
			cmd = ["iw", "dev", self.interface, "scan"]
			proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
			if proc.returncode != 0:
				print(f"Error scanning WiFi on {self.interface}: {proc.stderr.strip()}. Using cached list.")
				return self.cached_access_point

			lines = proc.stdout.splitlines()

			# Temporary storage for each AP
			ap_list = []
			current_ap = {}

			for line in lines:
				line = line.strip()
				# Start of a new BSS block: "BSS <bssid>(on <interface>)"
				bss_match = re.match(r"^BSS ([0-9A-Fa-f:]+)\(on", line)
				if bss_match:
					# If we already have an AP dict in progress, add it first
					if current_ap:
						ap_list.append(current_ap)
					current_ap = {
						"bssid": bss_match.group(1),
						"freq": None,
						"signal_dbm": None,
						"ssid": None
					}

				# Frequency line: "freq: 2412"
				freq_match = re.match(r"freq: (\d+)", line)
				if freq_match and current_ap:
					current_ap["freq"] = int(freq_match.group(1))

				# Signal line: "signal: -52.00 dBm"
				signal_match = re.match(r"signal: ([-\d\.]+) dBm", line)
				if signal_match and current_ap:
					try:
						current_ap["signal_dbm"] = float(signal_match.group(1))
					except ValueError:
						current_ap["signal_dbm"] = None

				# SSID line: "SSID: SomeNetwork"
				ssid_match = re.match(r"SSID: (.+)", line)
				if ssid_match and current_ap:
					current_ap["ssid"] = ssid_match.group(1)

			# After the loop, add the last AP if present
			if current_ap:
				ap_list.append(current_ap)

			# We'll store the best AP (by signal) per SSID in a dict
			access_points = {}

			# dBm range for conversion to percentage
			min_dbm = -100  # Very weak
			max_dbm = -30   # Excellent

			for ap in ap_list:
				ssid = ap["ssid"] or ""
				ssid = ssid.strip()
				if not ssid:  # Skip hidden SSIDs
					continue

				if ap["signal_dbm"] is None:
					continue

				# Convert dBm to percentage
				dbm = ap["signal_dbm"]
				signal_strength = int(((dbm - min_dbm) / (max_dbm - min_dbm)) * 100)
				signal_strength = max(0, min(100, signal_strength))

				# Apply threshold
				if signal_strength < signal_threshold:
					continue

				# If this SSID not in dict or found a stronger signal, update
				if (ssid not in access_points or 
						signal_strength > access_points[ssid]["signal_strength"]):
					access_points[ssid] = {
						"ssid": ssid,
						"signal_strength": signal_strength,
						"bssid": ap["bssid"],
						"freq": ap["freq"],
						"signal_dbm": dbm
					}

			# Convert dict to a list and sort
			sorted_access_points = sorted(
				access_points.values(),
				key=lambda x: x["signal_strength"],
				reverse=True
			)
			self.cached_access_point = sorted_access_points
			return sorted_access_points

		except Exception as e:
			print(f"Error getting Wi-Fi access points: {e}")
			return self.cached_access_point

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
				# If the hotspot is running, we consider signal strength as 100% for the AP
				return 100

			result = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True)
			output = result.stdout

			# Use regex to find the signal level
			match = re.search(r'Signal level=(-?\d+)', output)
			if match:
				signal_dbm = int(match.group(1))

				# Define the range for dBm values
				min_dbm = -100  # Very weak
				max_dbm = -30   # Excellent

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
		# ap_manager.activate_hotspot()
		print(f"Connected SSID: {ap_manager.get_current_ssid()}")
		print(f"Current IP: {ap_manager.get_current_ip()}")
		print("Internet is available." if ap_manager.is_internet_available() else "No internet access.")
		# input("Hotspot is running. Press Enter to deactivate and reconnect to Wi-Fi...")
		# ap_manager.deactivate_hotspot_and_reconnect()

		# Example: scanning with the new 'iw' approach
		nets = ap_manager.get_wifi_access_points(signal_threshold=30)
		print("Found networks:")
		for net in nets:
			print(net)

	except KeyboardInterrupt:
		ap_manager.deactivate_hotspot_and_reconnect()
