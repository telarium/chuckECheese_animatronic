import os
import socket
import sys
import thread
import eventlet
import logging
import SocketServer

from wsgiref import handlers
from pydispatch import dispatcher
from multiprocessing import Process
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, url_for, request, jsonify, g
from flask_uploads import UploadSet, configure_uploads, DOCUMENTS, IMAGES

# Patch system modules to be greenthread-friendly
eventlet.monkey_patch()

# Another monkey patch to avoid annoying (and useless?) socket pipe warnings when users disconnect
SocketServer.BaseServer.handle_error = lambda *args, **kwargs: None
handlers.BaseHandler.log_exception = lambda *args, **kwargs: None

app = app = Flask(__name__, static_folder='webpage')
app.config['SECRET_KEY'] = 'Big Whoop is an amusement park... or is it?!'
socketio = SocketIO(app)

# Turn off more annoying log messages that aren't helpful.
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Configure server to accept uploads of MIDI files
#docs = UploadSet('midi', ('midi'))
#configure_uploads(app, docs)

class WebServer:
    @app.route("/")
    def index():
        return app.send_static_file('index.html')

    # Guess the correct MIME type for static files
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
        return data["keyVal"]

    @socketio.on('onGamepadButton')
    def webGamepadEvent(data):
        dispatcher.send(signal="gamepadEvent",buttonNum=data["buttonVal"], val=int(data["val"]))
        return data["buttonVal"]

    def __init__(self):
        thread.start_new_thread(lambda: socketio.run(app,host='0.0.0.0',port=80), ())
        # Enable webcam  
        try:
            res = "320x240"
            framerate = 30
            cmd = "mjpg_streamer -i \"./input_uvc.so -y -n -d /dev/video0 -r " + res + " -f " + str( framerate ) + "\" -o \"./output_http.so -n -p 8080\" &"
            os.system("sudo pkill -9 mjpg_streamer > /dev/null 2>&1')")
            os.system("uvcdynctrl -f")
            os.system(cmd)
        except:
            print("mjpg_streamer did not start")

        self.socket = socketio

    def shutdown(self):
        os.system('sudo pkill -9 mjpg_streamer > /dev/null 2>&1')
        self.socketio.shutdown(socketio.SHUT_RDWR)
        self.socketio = None
        self.server.terminate()
        self.server.join()
