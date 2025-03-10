import os
import socket
import threading
import logging
from flask import Flask, request
from flask_socketio import SocketIO
from pydispatch import dispatcher

# Turn off extra log messages
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__, static_folder='webpage')
app.config['SECRET_KEY'] = 'Big Whoop is an amusement park... or is it?!'

# Use threading mode for async
socketio = SocketIO(app, async_mode='threading', ping_timeout=30, logger=False, engineio_logger=False)

class WebServer:
	@app.route("/")
	def index():
		return app.send_static_file('index.html')

	def broadcast(self, id, data):
		with app.app_context():
			try:
				socketio.emit(id, data, broadcast=True)
			except Exception as e:
				print(f"Broadcast error: {e}")

	@app.route('/<path:path>')
	def static_proxy(path):
		return app.send_static_file(path)

	@socketio.on('onConnect')
	def connectEvent(msg):
		ip = request.remote_addr
		dispatcher.send(signal='connectEvent', client_ip=ip)

	@socketio.on('showPlay')
	def showPlayEvent(show_name):
		dispatcher.send(signal='showPlay', showName=show_name)

	@socketio.on('showStop')
	def showStopEvent():
		dispatcher.send(signal='showStop')

	@socketio.on('showPause')
	def showPauseEvent():
		dispatcher.send(signal='showPause')

	@socketio.on('onMirroredMode')
	def mirroredModeEvent(bEnable):
		dispatcher.send(signal='onMirroredMode', val=bEnable)

	@socketio.on('onRetroMode')
	def retroModeEvent(bEnable):
		dispatcher.send(signal='onRetroMode', val=bEnable)

	@socketio.on('onHeadNodInverted')
	def headNodEvent(bEnable):
		dispatcher.send(signal='onHeadNodInverted', val=bEnable)

	@socketio.on('onKeyPress')
	def webKeyEvent(data):
		dispatcher.send(signal="keyEvent", key=data["keyVal"], val=int(data["val"]))

	@socketio.on('onConnectToWifi')
	def connectToWifi(data):
		dispatcher.send(signal="connectToWifi", ssid=data["ssid"], password=data["password"])

	@socketio.on('onSetHotspot')
	def setHotspot(bEnable):
		print("Hotspot event triggered")
		dispatcher.send(signal="activateWifiHotspot", bActivate=bEnable)

	@socketio.on('onWebTTSSubmit')
	def webTTSSubmit(inputText):
		dispatcher.send(signal="webTTSEvent", val=inputText)

	def __init__(self):
		# Create a thread for HTTP server only
		self.threads = []
		http_thread = threading.Thread(target=self.run_http, daemon=True)
		self.threads.append(http_thread)
		http_thread.start()

	def run_http(self):
		try:
			print("Starting HTTP server on port 80...")
			socketio.run(app, host='0.0.0.0', port=80)
		except Exception as e:
			print(f"Error running HTTP server: {e}")

	def shutdown(self):
		print("Shutting down server...")
		# Implement shutdown logic if needed.

if __name__ == "__main__":
	import time
	server = WebServer()
	try:
		while True:
			time.sleep(0.01)
	except KeyboardInterrupt:
		server.shutdown()
