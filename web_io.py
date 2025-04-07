import os
import socket
import threading
import logging
from flask import Flask, request, Response
from flask_socketio import SocketIO
from pydispatch import dispatcher
from typing import Any

# Turn off extra log messages
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__, static_folder='webpage')
app.config['SECRET_KEY'] = 'Monkey Island is an amusement park.'

# Use threading mode for async
socketio = SocketIO(app, async_mode='threading', ping_timeout=30, logger=False, engineio_logger=False)


class WebServer:
	@app.route("/")
	def index() -> Response:
		return app.send_static_file('index.html')

	def broadcast(self, signal_id: str, data: Any) -> None:
		with app.app_context():
			try:
				socketio.emit(signal_id, data, broadcast=True)
			except Exception as e:
				print(f"Broadcast error: {e}")

	@app.route('/<path:path>')
	def static_proxy(path: str) -> Response:
		return app.send_static_file(path)

	@socketio.on('onConnect')
	def connect_event(msg: Any) -> None:
		ip = request.remote_addr
		dispatcher.send(signal='connectEvent', client_ip=ip)

	@socketio.on('showPlay')
	def show_play_event(show_name: str) -> None:
		dispatcher.send(signal='showPlay', show_name=show_name)

	@socketio.on('showStop')
	def show_stop_event() -> None:
		dispatcher.send(signal='showStop')

	@socketio.on('showPause')
	def show_pause_event() -> None:
		dispatcher.send(signal='showPause')

	@socketio.on('onMirroredMode')
	def mirrored_mode_event(bEnable: bool) -> None:
		dispatcher.send(signal='onMirroredMode', val=bEnable)

	@socketio.on('onRetroMode')
	def retro_mode_event(bEnable: bool) -> None:
		dispatcher.send(signal='onRetroMode', val=bEnable)

	@socketio.on('onHeadNodInverted')
	def head_nod_event(bEnable: bool) -> None:
		dispatcher.send(signal='onHeadNodInverted', val=bEnable)

	@socketio.on('onKeyPress')
	def web_key_event(data: dict) -> None:
		dispatcher.send(signal="keyEvent", key=data["keyVal"], val=int(data["val"]))

	@socketio.on('onConnectToWifi')
	def connect_to_wifi(data: dict) -> None:
		dispatcher.send(signal="connectToWifi", ssid=data["ssid"], password=data["password"])

	@socketio.on('onSetHotspot')
	def set_hotspot(bEnable: bool) -> None:
		print("Hotspot event triggered")
		dispatcher.send(signal="activateWifiHotspot", bActivate=bEnable)

	@socketio.on('onWebTTSSubmit')
	def web_tts_submit(inputText: str) -> None:
		dispatcher.send(signal="webTTSEvent", val=inputText)

	def __init__(self) -> None:
		# Create a thread for HTTP server only
		self.threads: list[threading.Thread] = []
		http_thread = threading.Thread(target=self.run_http, daemon=True)
		self.threads.append(http_thread)
		http_thread.start()

	def run_http(self) -> None:
		try:
			print("Starting HTTP server on port 80...")
			socketio.run(app, host='0.0.0.0', port=80)
		except Exception as e:
			print(f"Error running HTTP server: {e}")

	def shutdown(self) -> None:
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
