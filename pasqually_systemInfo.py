import os
import socket
import sys
import thread
import eventlet
from flask_socketio import SocketIO, emit

class SystemInfo:
	def __init__(self,mysocket):
		self.socket = mysocket

	def myTest(self):
		self.socket.emit('my_response',{'data': 'Connected', 'count': 0},broadcast=True)


