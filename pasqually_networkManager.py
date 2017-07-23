#https://github.com/seveas/python-networkmanager

import NetworkManager
c = NetworkManager.const

class NetworkManagement():
	def __init__(self):
		print("Network init")

	def getActiveConnection(self):
		for conn in NetworkManager.NetworkManager.ActiveConnections:
			settings = conn.Connection.GetSettings()['connection']
			print settings['id']

	def scanWifi(self):
		for dev in NetworkManager.NetworkManager.GetDevices():	
			if dev.DeviceType != NetworkManager.NM_DEVICE_TYPE_WIFI:
				continue
			for ap in dev.GetAccessPoints():
				print ap.Ssid
				print ap.Strength
