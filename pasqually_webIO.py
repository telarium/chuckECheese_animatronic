import os
import socket
try:
    from flask import Flask
except:
    os.system( "sudo apt-get mjpgstreamer -y ")
    os.system( "sudo apt-get install python-pip -y")
    os.system( "sudo pip install flask")
    from flask import Flask

app = Flask(__name__)

class WebServer:
    @app.route("/")
    def hello():
        return "Hello World!"

    def __init__(self ):
        app.run(host='0.0.0.0')
            
        # Enable webcam
        res = "480x360"
        framerate = 24
        cmd = "/home/pi/mjpg-streamer/mjpg_streamer -i \"/usr/lib/input_uvc.so -n -d /dev/video0 -r " + res + " -f " + str( framerate ) + "\" -o \"/usr/lib/output_http.so -w /home/pi/mjpg-streamer/www -n -p 8080\" -b >/dev/null 2>&1"
        os.system(cmd)

    def shutdown(self):
        os.system('kill -9 `pidof mjpg_streamer`')
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()
