import os
import sys
import time
import threading
import psutil
from pydispatch import dispatcher

class SystemInfo:
	def __init__(self):
		t = threading.Thread(target=self.update, args=())
		t.setDaemon(True)
		t.start()

	def update(self):
		while True:
			time.sleep(1)
			cpu = int(psutil.cpu_percent())
			ram = int(psutil.virtual_memory().percent)
			dispatcher.send(signal='systemInfoEvent',cpu=cpu,ram=ram)