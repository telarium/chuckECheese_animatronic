#https://github.com/seveas/python-networkmanager

from pydispatch import dispatcher
import json
import threading
import NetworkManager
c = NetworkManager.const

class NetworkManagement():
	def __init__(self):
		print("Network init")
		self.networkCache = None

	def getActiveConnection(self):
		for conn in NetworkManager.NetworkManager.ActiveConnections:
			settings = conn.Connection.GetSettings()['connection']
			print settings['id']

	def scanWifi(self):
		if self.networkCache != None:
			dispatcher.send(signal="wifiScan",data=self.networkCache)

		def scan():
			jsonData = '{"networks": ['
			for dev in NetworkManager.NetworkManager.GetDevices():
				if dev.DeviceType != NetworkManager.NM_DEVICE_TYPE_WIFI:
					continue
				for ap in dev.GetAccessPoints():
					ssid = ap.Ssid.decode('utf-8')
					jsonData = jsonData + '{"ssid":"' + ssid + '","strength":"' + str(ap.Strength) + '"},'
					#connections = [x.GetSettings() for x in NetworkManager.Settings.ListConnections()]
					#connections = dict([(x['connection']['id'], x) for x in connections])
					#try:
					#	conn = connections["ssid"]
					#except:
					#	pass

			jsonData = jsonData[:-1]
			jsonData = jsonData + ']}'
			self.networkCache = json.loads(jsonData)
			dispatcher.send(signal="wifiScan",data=self.networkCache)

		t = threading.Thread(target=scan, args=())
		t.setDaemon(True)
		t.start()