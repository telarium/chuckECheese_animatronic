import configparser
import os
import subprocess
import socket
import requests
import re


class WifiManagement:
	def __init__(self, interface="wlan0", config_file="config.cfg"):
		self.config = self.load_config(config_file)

		self.ssid = self.config["Hotspot"]["HotspotSSID"]
		self.password = self.config["Hotspot"]["HotspotPassword"]
		self.channel = self.config["Hotspot"]["HotspotChannel"]

		self.interface = interface
		self.hostapd_conf_path = "/etc/hostapd/hostapd.conf"
		self.dnsmasq_conf_path = "/etc/dnsmasq.conf"

	def load_config(self, config_file):
		config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)
		if not os.path.exists(config_path):
			raise FileNotFoundError(f"Configuration file not found: {config_path}")
		config = configparser.ConfigParser()
		config.read(config_path)
		return config

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
		try:
			# Run the scan command
			result = subprocess.run(
				['sudo', 'iwlist', self.interface, 'scan'],
				capture_output=True,
				text=True
			)
			output = result.stdout

			if result.returncode != 0:
				raise RuntimeError(f"Error scanning for Wi-Fi networks: {result.stderr.strip()}")

			# Define the range for dBm values
			min_dbm = -100  # Very weak signal
			max_dbm = -30   # Excellent signal

			# Parse the output
			access_points = []
			ssid = None
			signal_dbm = None

			for line in output.splitlines():
				line = line.strip()
				if "ESSID:" in line:
					ssid = line.split("ESSID:")[1].strip('"')
				if "Signal level=" in line:
					match = re.search(r"Signal level=(-?\d+)", line)
					if match:
						signal_dbm = int(match.group(1))
						# Convert dBm to percentage
						signal_strength = max(
							0,
							min(100, int(((signal_dbm - min_dbm) / (max_dbm - min_dbm)) * 100))
						)

				# If both SSID and signal strength are found, save the access point
				if ssid is not None and ssid != '' and signal_dbm is not None:
					if signal_strength > signal_threshold:  # Only include strong signals
						access_points.append({"ssid": ssid, "signal_strength": signal_strength})
					ssid = None  # Reset for the next AP
					signal_dbm = None

			return access_points
		except Exception as e:
			print(f"Error getting Wi-Fi access points: {e}")
			return []

	def connect_to_wifi(self, ssid, password):
		try:
			wpa_supplicant_path = "/etc/wpa_supplicant/wpa_supplicant.conf"

			# Create a temporary network configuration
			temp_config = f"""
	network={{
		ssid="{ssid}"
		psk="{password}"
		key_mgmt=WPA-PSK
	}}
			"""

			# Test the connection with wpa_cli directly (does not modify wpa_supplicant.conf)
			subprocess.run(["sudo", "wpa_cli", "-i", self.interface, "disconnect"], check=True)
			subprocess.run(["sudo", "wpa_cli", "-i", self.interface, "add_network"], check=True)
			subprocess.run(["sudo", "wpa_cli", "-i", self.interface, f"set_network", "0", f'ssid "{ssid}"'], check=True)
			subprocess.run(["sudo", "wpa_cli", "-i", self.interface, f"set_network", "0", f'psk "{password}"'], check=True)
			subprocess.run(["sudo", "wpa_cli", "-i", self.interface, "enable_network", "0"], check=True)
			subprocess.run(["sudo", "wpa_cli", "-i", self.interface, "reconnect"], check=True)

			# Check if connected to the SSID
			connected_ssid = self.get_current_ssid()
			if connected_ssid == ssid:
				print(f"Successfully connected to {ssid}.")

				# Read and update wpa_supplicant.conf
				with open(wpa_supplicant_path, "r") as f:
					lines = f.readlines()

				# Remove existing entry for the SSID
				new_lines = []
				in_network_block = False
				for line in lines:
					if line.strip().startswith("network={"):
						in_network_block = True
						current_block = []
					if in_network_block:
						current_block.append(line)
						if line.strip().endswith("}"):
							in_network_block = False
							if not any(f'ssid="{ssid}"' in block_line for block_line in current_block):
								new_lines.extend(current_block)
					else:
						new_lines.append(line)

				# Add the new network block
				new_lines.append(temp_config.strip() + "\n")

				# Write back the updated configuration
				with open(wpa_supplicant_path, "w") as f:
					f.writelines(new_lines)

				return True
			else:
				print(f"Failed to connect to {ssid}.")
				return False
		except Exception as e:
			print(f"Error connecting to Wi-Fi: {e}")
			return False

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
