#!/usr/bin/env python
#

import os
import sys
import string

class Setup:
    def __init__(self):
	path = os.path.dirname(os.path.realpath(sys.argv[0]))
	os.system("sudo apt-get install git build-essential python-dev flex bison dnsmasq python3-smbus python3-mido python3-rtmidi -y")
	os.system("sudo apt-get install python3-flask python3-flask-socketio python3-flask-talisman python3-eventlet python3-psutil python3-pydispatch")
    os.system("git clone https://github.com/maxcountryman/flask-uploads.git")
    os.system("cd flask-uploads")
    os.system("sudo python3 setup.py install")
    os.system("cd ../")
    os.system("sudo rm -rf flask-updloads")
    
install = Setup()
