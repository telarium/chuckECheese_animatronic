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
from typing import Optional, List, Dict, Any

class WifiManagement:
	def __init__(self, config_file: str = "config.cfg") -> None:
		self.config: configparser.ConfigParser = self.load_config(config_file)
		self.cached_access_point: Optional[List[Dict[str, Any]]] = None

		self.ssid: str = self.config["Hotspot"]["HotspotSSID"]
		self.password: str = self.config["Hotspot"]["HotspotPassword"]
		self.channel: str = self.config["Hotspot"]["HotspotChannel"]

		# Automatically choose wlan1 if it exists and appears connected; otherwise, use wlan0.
		self.interface: str = self._get_preferred_interface()

		self.hostapd_conf_path: str = "/etc/hostapd/hostapd.conf"
		self.dnsmasq_conf_path: str = "/etc/dnsmasq.conf"

		# Initialize PyWiFi and retrieve the interface details.
		self.wifi: pywifi.PyWiFi = pywifi.PyWiFi()
		self.iface: str = self._get_interface()

	def load_config(self, config_file: str) -> configparser.ConfigParser:
		config_path: str = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)
		if not os.path.exists(config_path):
			raise FileNotFoundError(f"Configuration file not found: {config_path}")
		config = configparser.ConfigParser()
		config.read(config_file)
		return config

	def _get_preferred_interface(self) -> str:
		"""
		Checks if wlan1 exists and appears connected (has a non-empty SSID via iwgetid).
		If so, returns "wlan1"; otherwise, returns "wlan0".
		"""
		try:
			result = subprocess.run(
				["iwgetid", "--raw", "wlan1"],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				text=True
			)
			if result.returncode == 0 and result.stdout.strip() != "":
				return "wlan1"
		except Exception:
			pass
		return "wlan0"

	def _get_interface(self) -> str:
		"""Retrieve the Wi-Fi interface without using PyWiFi."""
		try:
			output: str = subprocess.check_output(['iw', 'dev'], universal_newlines=True)
		except FileNotFoundError:
			raise RuntimeError("The 'iw' command is not found. Please install wireless tools.")

		interfaces: List[str] = []
		for line in output.split('\n'):
			if line.strip().startswith('Interface'):
				iface_name = line.strip().split()[1]
				interfaces.append(iface_name)

		if not interfaces:
			raise RuntimeError("No Wi-Fi interfaces detected. Ensure the interface is enabled and in managed mode.")

		if self.interface in interfaces:
			return self.interface  # Return the interface name as a string
		else:
			raise ValueError(f"Interface '{self.interface}' not found among available interfaces: {interfaces}")

	def create_hostapd_conf(self) -> None:
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

	def create_dnsmasq_conf(self) -> None:
		"""Create a dnsmasq configuration file."""
		dnsmasq_conf = f"""
interface={self.interface}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
		"""
		with open(self.dnsmasq_conf_path, "w") as f:
			f.write(dnsmasq_conf.strip() + "\n")
		print("Dnsmasq configuration created.")

	def setup_interface(self) -> None:
		"""Configure the interface for AP mode."""
		subprocess.run(["systemctl", "stop", "wpa_supplicant"], check=True)
		subprocess.run(["systemctl", "stop", "NetworkManager"], check=True)

		subprocess.run(["ifconfig", self.interface, "down"], check=True)
		subprocess.run(["iw", "dev", self.interface, "set", "type", "__ap"], check=True)
		subprocess.run(["ifconfig", self.interface, "up"], check=True)

		subprocess.run(["ifconfig", self.interface, "192.168.4.1", "netmask", "255.255.255.0"], check=True)
		print(f"Configured {self.interface} with static IP.")

	def start_services(self) -> None:
		"""Start hostapd and dnsmasq services."""
		subprocess.run(["systemctl", "restart", "dnsmasq"], check=True)
		subprocess.run(["systemctl", "restart", "hostapd"], check=True)
		print("Access point started.")

	def stop_services(self) -> None:
		"""Stop hostapd and dnsmasq services."""
		subprocess.run(["systemctl", "stop", "hostapd"], check=True)
		subprocess.run(["systemctl", "stop", "dnsmasq"], check=True)
		subprocess.run(["ifconfig", self.interface, "down"], check=True)
		print("Access point stopped.")

	def deactivate_hotspot_and_reconnect(self) -> None:
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

	def ensure_hostapd_unmasked(self) -> None:
		try:
			subprocess.run(["systemctl", "unmask", "hostapd"], check=True)
			print("hostapd service unmasked.")
		except subprocess.CalledProcessError as e:
			print(f"Error unmasking hostapd: {e}")

	def activate_hotspot(self) -> None:
		"""Activate the access point."""
		self.ensure_hostapd_unmasked()
		self.create_hostapd_conf()
		self.create_dnsmasq_conf()
		self.setup_interface()
		self.start_services()
		print(f"Access point '{self.ssid}' is now running on {self.interface}.")

	def is_interface_in_ap_mode(self) -> bool:
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

	def is_hotspot_active(self) -> bool:
		"""Check if the hotspot is currently active: both services running and interface in AP mode."""
		try:
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

			interface_is_ap = self.is_interface_in_ap_mode()

			return services_active and interface_is_ap
		except Exception as e:
			print(f"Error checking hotspot status: {e}")
			return False

	def get_current_ssid(self) -> Optional[str]:
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

	def get_current_ip(self) -> Optional[str]:
		"""Get the current IP address of the connected Wi-Fi or Ethernet network."""
		interfaces = [self.interface]
		if "eth0" not in interfaces:
			interfaces.append("eth0")

		for iface in interfaces:
			try:
				result = subprocess.run(
					['ip', 'addr', 'show', iface],
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					text=True,
				)
				if result.returncode != 0:
					raise RuntimeError(f"Error getting IP address for {iface}: {result.stderr.strip()}")
				for line in result.stdout.splitlines():
					if line.strip().startswith("inet "):
						ip_address = line.split()[1].split('/')[0]
						if ip_address:
							return ip_address
			except Exception as e:
				print(f"Error getting IP address for {iface}: {e}")
		return None

	def is_internet_available(self, url: str = "https://www.google.com", timeout: int = 5) -> bool:
		"""Check if there is a valid internet connection."""
		try:
			response = requests.head(url, timeout=timeout)
			return response.status_code == 200
		except requests.RequestException:
			return False

	def get_wifi_access_points(self) -> Optional[List[Dict[str, Any]]]:
		return self.cached_access_point

	def scan_wifi_access_points(self, signal_threshold: int = 30) -> Optional[List[Dict[str, Any]]]:
		def wifi_scan() -> None:
			"""
			Retrieve available Wi-Fi access points above a signal threshold
			by calling 'iw dev <interface> scan' directly.
			"""
			try:
				cmd = ["iw", "dev", self.interface, "scan"]
				proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
				if proc.returncode != 0:
					print(f"Error scanning WiFi on {self.interface}: {proc.stderr.strip()}. Using cached list.")
					return

				lines = proc.stdout.splitlines()
				ap_list: List[Dict[str, Any]] = []
				current_ap: Dict[str, Any] = {}

				for line in lines:
					line = line.strip()
					bss_match = re.match(r"^BSS ([0-9A-Fa-f:]+)\(on", line)
					if bss_match:
						if current_ap:
							ap_list.append(current_ap)
						current_ap = {
							"bssid": bss_match.group(1),
							"freq": None,
							"signal_dbm": None,
							"ssid": None
						}

					freq_match = re.match(r"freq: (\d+)", line)
					if freq_match and current_ap:
						current_ap["freq"] = int(freq_match.group(1))

					signal_match = re.match(r"signal: ([-\d\.]+) dBm", line)
					if signal_match and current_ap:
						try:
							current_ap["signal_dbm"] = float(signal_match.group(1))
						except ValueError:
							current_ap["signal_dbm"] = None

					ssid_match = re.match(r"SSID: (.+)", line)
					if ssid_match and current_ap:
						current_ap["ssid"] = ssid_match.group(1)

				if current_ap:
					ap_list.append(current_ap)

				access_points: Dict[str, Dict[str, Any]] = {}
				min_dbm = -100  # Very weak
				max_dbm = -30   # Excellent

				for ap in ap_list:
					ssid = (ap["ssid"] or "").strip()
					if not ssid:
						continue
					if ap["signal_dbm"] is None:
						continue
					dbm = ap["signal_dbm"]
					signal_strength = int(((dbm - min_dbm) / (max_dbm - min_dbm)) * 100)
					signal_strength = max(0, min(100, signal_strength))
					if signal_strength < signal_threshold:
						continue
					if ssid not in access_points or signal_strength > access_points[ssid]["signal_strength"]:
						access_points[ssid] = {
							"ssid": ssid,
							"signal_strength": signal_strength,
							"bssid": ap["bssid"],
							"freq": ap["freq"],
							"signal_dbm": dbm
						}
				sorted_access_points = sorted(
					access_points.values(),
					key=lambda x: x["signal_strength"],
					reverse=True
				)
				self.cached_access_point = sorted_access_points
			except Exception as e:
				print(f"Error getting Wi-Fi access points: {e}")

		thread = threading.Thread(target=wifi_scan)
		thread.start()

	def connect_to_wifi(self, ssid: str, password: str) -> bool:
		"""Connect to a Wi-Fi network, ensuring the hotspot is deactivated if running."""
		result_container: List[bool] = []

		def wifi_task() -> None:
			try:
				current_ssid = self.get_current_ssid()
				if current_ssid == ssid:
					result_container.append(True)
					return
				if self.is_hotspot_active():
					print("Hotspot is active. Deactivating it before connecting to Wi-Fi...")
					self.deactivate_hotspot_and_reconnect()
				print("Waiting for interface to stabilize...")
				time.sleep(5)
				self.wifi = pywifi.PyWiFi()
				self.iface = self._get_interface()
				print(f"Attempting to connect to Wi-Fi network: {ssid} using {self.interface}")
				self.iface.disconnect()
				time.sleep(1)
				profile = pywifi.Profile()
				profile.ssid = ssid
				profile.auth = const.AUTH_ALG_OPEN
				profile.akm.append(const.AKM_TYPE_WPA2PSK)
				profile.cipher = const.CIPHER_TYPE_CCMP
				profile.key = password
				self.iface.remove_all_network_profiles()
				tmp_profile = self.iface.add_network_profile(profile)
				self.iface.connect(tmp_profile)
				start_time = time.time()
				while time.time() - start_time < 10:
					if self.iface.status() == const.IFACE_CONNECTED:
						print(f"Successfully connected to {ssid}")
						result_container.append(True)
						return
					time.sleep(1)
				print(f"Failed to connect to {ssid}")
				result_container.append(False)
			except Exception as e:
				print(f"Error connecting to Wi-Fi: {e}")
				result_container.append(False)

		thread = threading.Thread(target=wifi_task)
		thread.start()
		thread.join()
		return result_container[0] if result_container else False

	def get_signal_strength(self) -> Any:
		"""Get the WiFi signal strength as a percentage."""
		try:
			if self.is_hotspot_active():
				return 100
			result = subprocess.run(['iwconfig', self.interface], capture_output=True, text=True)
			output = result.stdout
			match = re.search(r'Signal level=(-?\d+)', output)
			if match:
				signal_dbm = int(match.group(1))
				min_dbm = -100
				max_dbm = -30
				percentage = max(0, min(100, int(((signal_dbm - min_dbm) / (max_dbm - min_dbm)) * 100)))
				return percentage
		except Exception as e:
			print(f"Exception getting WiFi signal strength: {e}")
		return "--"

# Example usage
if __name__ == "__main__":
	ap_manager = WifiManagement()
	try:
		print(f"Connected SSID: {ap_manager.get_current_ssid()}")
		print(f"Current IP: {ap_manager.get_current_ip()}")
		print("Internet is available." if ap_manager.is_internet_available() else "No internet access.")
		print("Available networks:")
		networks = ap_manager.scan_wifi_access_points(signal_threshold=30)
		if networks:
			for net in networks:
				print(net)
	except KeyboardInterrupt:
		ap_manager.deactivate_hotspot_and_reconnect()
