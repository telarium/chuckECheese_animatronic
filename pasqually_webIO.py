import os
import socket
import sys
import threading

try:
    from flask import Flask
except:
    os.system( "sudo apt-get install python-pip -y")
    os.system( "sudo pip install flask")
    from flask import Flask

if( not os.path.isdir( os.path.dirname(os.path.realpath(sys.argv[0])) + "/mjpg-streamer" ) ):
    path = os.path.dirname(os.path.realpath(sys.argv[0]))
    os.system( "wget http://lilnetwork.com/download/raspberrypi/mjpg-streamer.tar.gz -P " + path )
    os.system( "tar xvzf " + path + "/mjpg-streamer.tar.gz && sudo rm " + path + "/mjpg-streamer.tar.gz" )
    os.system( "sudo apt-get install libjpeg62-turbo-dev imagemagick -y" )
    os.system( "cd " + path + "/mjpg-streamer/mjpg-streamer && make" )

app = Flask(__name__)

class WebServer:
    @app.route("/")
    def hello():
        return "Hello World!"

    def __init__(self ):
        def start(self):
            app.run(host='0.0.0.0')

        t = threading.Thread(name='start', target=start)
            
        # Enable webcam
        res = "480x360"
        framerate = 24
        cmd = "/home/pi/mjpg-streamer/mjpg_streamer -i \"/usr/lib/input_uvc.so -n -d /dev/video0 -r " + res + " -f " + str( framerate ) + "\" -o \"/usr/lib/output_http.so -w /home/pi/mjpg-streamer/www -n -p 8080\" -b >/dev/null 2>&1"
        os.system(cmd)

    def shutdown(self):
        os.system('kill -9 `pidof mjpg_streamer`')
        try:
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            else:
                func()
        except:
            print( "Shutdown" )
