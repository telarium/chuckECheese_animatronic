import configparser
import os
import subprocess
import socket
import requests


class WifiManagement:
	def __init__(self, interface="wlan0", config_file="config.cfg"):
		self.config = self.load_config(config_file)

		# PicoVoice and Google Speech-to-Text keys
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

	def get_current_ssid(self):
		"""Get the current SSID name of the connected Wi-Fi network."""
		try:
			result = subprocess.run(
				['iwgetid', '--raw', self.interface],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				text=True,
			)
			
			if result.returncode == 0:
				ssid = result.stdout.strip()
				return ssid if ssid else None
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
