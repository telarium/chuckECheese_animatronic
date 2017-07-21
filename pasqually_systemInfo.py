import os
import socket
import sys
import time
import threading
import eventlet
import psutil
from flask_socketio import SocketIO, emit

eventlet.monkey_patch()

class SystemInfo:
	def __init__(self,mysocket):
		self.socket = mysocket
		t = threading.Thread(target=self.update, args=())
		t.setDaemon(True)
		t.start()

	def update(self):
		while True:
			time.sleep(1)
			print psutil.cpu_percent()
			#print psutil.virtual_memory().percent

			self.socket.emit('systemInfo',{'cpu': str(psutil.cpu_percent()),'ram': str(psutil.virtual_memory().percent)},broadcast=True)