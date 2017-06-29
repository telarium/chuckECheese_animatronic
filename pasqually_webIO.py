import os
import socket
import sys
import thread
import eventlet
from pydispatch import dispatcher
from multiprocessing import Process
from flask import Flask, render_template, url_for, request, jsonify, g
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


class WebServer:
    @app.route("/")
    def index():
        url_for('static', filename='pasqually.js')
        url_for('static', filename='socket.io.min.js' )
        return render_template('index.html')

    @socketio.on('onKeyPress')
    def webKeyEvent(data):
        dispatcher.send(signal="keyEvent",key=data["keyVal"], val=int(data["val"]))
        return data["keyVal"]

    def __init__(self):
        print "Start?"
        thread.start_new_thread(lambda: socketio.run(app,host='0.0.0.0',port=80), ())
        #socketio.run(app,host='0.0.0.0',port=80)
        print "START!"
        # Enable webcam
        res = "480x360"
        framerate = 24
        cmd = "/home/pi/mjpg-streamer/mjpg_streamer -i \"/usr/lib/input_uvc.so -n -d /dev/video0 -r " + res + " -f " + str( framerate ) + "\" -o \"/usr/lib/output_http.so -w /home/pi/mjpg-streamer/www -n -p 8080\" -b >/dev/null 2>&1"
        os.system(cmd)

    def shutdown(self):
        os.system('kill -9 `pidof mjpg_streamer` > /dev/null 2>&1')
        self.server.terminate()
        self.server.join()
