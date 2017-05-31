import os
import socket
import sys
from pydispatch import dispatcher
from multiprocessing import Process
from flask import Flask, render_template, url_for, request, jsonify, g

app = Flask(__name__)

class WebServer:
    @app.route("/")
    def index():
	url_for('static', filename='pasqually.js')
        url_for('static', filename='jquery.js' )
        return render_template('index.html')

    @app.route('/onKeyPress', methods=['GET'])
    def webKeyEvent():
        dispatcher.send(signal="keyEvent",key=request.args.get('keyVal'), val=int(request.args.get('val' )))
            #message=request.args.get('keyVal'), arg2=int(request.args.get('val')), sender="web")
        return request.args.get('keyVal')

    @app.route('/startSession', methods=['GET', 'POST'])
    def startSession():
        return True

    def __init__(self):
        def run_server():
            app.run(host='0.0.0.0',port=80,threaded=True,debug=False)

        self.server = Process(target=run_server)
        self.server.start()
        
        # Enable webcam
        res = "480x360"
        framerate = 24
        cmd = "/home/pi/mjpg-streamer/mjpg_streamer -i \"/usr/lib/input_uvc.so -n -d /dev/video0 -r " + res + " -f " + str( framerate ) + "\" -o \"/usr/lib/output_http.so -w /home/pi/mjpg-streamer/www -n -p 8080\" -b >/dev/null 2>&1"
        os.system(cmd)

    def shutdown(self):
        os.system('kill -9 `pidof mjpg_streamer` > /dev/null 2>&1')
        self.server.terminate()
        self.server.join()
