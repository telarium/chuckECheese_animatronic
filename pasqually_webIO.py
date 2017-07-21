import os
import socket
import sys
import thread
import eventlet
from pydispatch import dispatcher
from multiprocessing import Process
from flask import Flask, render_template, url_for, request, jsonify, g
from flask_socketio import SocketIO, emit

app = app = Flask(__name__, static_folder='webpage')
app.config['SECRET_KEY'] = 'Big Whoop is an amusement park... or is it?!'
socketio = SocketIO(app)


class WebServer:
    @app.route("/")
    def index():
        return app.send_static_file('index.html')

    @app.route('/<path:path>')
    def static_proxy(path):
        # send_static_file will guess the correct MIME typen
        return app.send_static_file(path)

    @socketio.on('onConnect')
    def connectEvent(msg):
        dispatcher.send(signal='connectEvent')

    @socketio.on('onKeyPress')
    def webKeyEvent(data):
        dispatcher.send(signal="keyEvent",key=data["keyVal"], val=int(data["val"]))
        socketio.emit('systemInfo','hi',broadcast=True)
        return data["keyVal"]

    def __init__(self):
        thread.start_new_thread(lambda: socketio.run(app,host='0.0.0.0',port=80), ())
        # Enable webcam
        res = "480x360"
        framerate = 24
        cmd = "/home/pi/mjpg-streamer/mjpg_streamer -i \"/usr/lib/input_uvc.so -n -d /dev/video0 -r " + res + " -f " + str( framerate ) + "\" -o \"/usr/lib/output_http.so -w /home/pi/mjpg-streamer/www -n -p 8080\" -b >/dev/null 2>&1"
        os.system(cmd)
        self.socket = socketio

    def shutdown(self):
        os.system('kill -9 `pidof mjpg_streamer` > /dev/null 2>&1')
        self.socketio.shutdown(socketio.SHUT_RDWR)
        self.socketio = None
        self.server.terminate()
        self.server.join()
