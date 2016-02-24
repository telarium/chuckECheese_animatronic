import os
import socket
import sys
from multiprocessing import Process

try:
    from flask import Flask, render_template, url_for
except:
    os.system( "sudo apt-get install python-pip -y")
    os.system( "sudo pip install flask")
    from flask import Flask, render_template, url_for

if( not os.path.isdir( os.path.dirname(os.path.realpath(sys.argv[0])) + "/mjpg-streamer" ) ):
    path = os.path.dirname(os.path.realpath(sys.argv[0]))
    os.system( "wget http://lilnetwork.com/download/raspberrypi/mjpg-streamer.tar.gz -P " + path )
    os.system( "tar xvzf " + path + "/mjpg-streamer.tar.gz && sudo rm " + path + "/mjpg-streamer.tar.gz" )
    os.system( "sudo apt-get install libjpeg62-turbo-dev imagemagick -y" )
    os.system( "cd " + path + "/mjpg-streamer/mjpg-streamer && make" )

app = Flask(__name__)

class WebServer:
    @app.route("/")
    def index():
	url_for('static', filename='pasqually.js')
        return render_template('index.html')

    def __init__(self ):
        def run_server():
            app.run(host='0.0.0.0',debug=False)

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
