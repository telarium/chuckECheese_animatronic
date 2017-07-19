import os
import socket
import sys
import time
import threading
import eventlet
import psutil
from flask_socketio import SocketIO, emit

class SystemInfo:
	def __init__(self,mysocket):
		self.socket = mysocket
		t = threading.Thread(target=self.update, args=())
		t.setDaemon(True)
		t.start()

	def update(self):
		while True:
			time.sleep(1)
			#print int(psutil.cpu_percent())
			#print int(psutil.virtual_memory().percent)
			self.socket.emit('systemInfo',{'cpu': int(psutil.cpu_percent()),'ram': int(psutil.virtual_memory().percent)},broadcast=True)