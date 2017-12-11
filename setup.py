#!/usr/bin/env python
#

import os
import sys
import string

class Setup:
    def __init__(self):
	path = os.path.dirname(os.path.realpath(sys.argv[0]))
	os.system("sudo apt-get install git build-essential python python-dev python-pip flex bison dnsmasq python-blinker python-eventlet uvcdynctrl libv4l-dev python-dbus -y")
	os.system("sudo pip install flask flask-socketio gevent psutil PyDispatcher CHIP-IO")
	
	# Install mjpg-streamer
	os.system( "cd /tmp && git clone https://github.com/SaintGimp/mjpg-streamer" )
	os.system( "sudo apt-get install libjpeg62-turbo-dev imagemagick -y" )
	os.system( "cd /tmp/mjpg-streamer/mjpg-streamer-experimental && make USE_LIBV4L2=true && sudo make install" )

	# Install nmcli library
	os.system('cd /tmp && git clone https://github.com/seveas/python-networkmanager')
	os.system('cd /tmp/python-networkmanager && sudo python setup.py install')
    os.system('cp *.so ' + path)
	os.system('cd ' + path)	

	# TODO... store hours of operation here
        self.settingsFile = os.path.dirname(os.path.realpath(sys.argv[0])) + "/settings.txt" 
        if( not os.path.isfile( self.settingsFile ) ):
            f = open( self.settingsFile, "w" )
            f.write( "hi" )
            f.close()

	hostname = "pasqually"
        if( len(hostname)>0 and hostname != " " ):
            self.setHostname(hostname)

        apName = "Pasqually"
        if( len(apName)>0 and apName != " " ):
            self.setAccessPoint(apName)

    def setHostname(self,hostname):
	print("Setting hostname...")
        f = open( "temp","w" )
        currentHostName = open( "/etc/hostname", "r" ).read()
        f.write( hostname )
        f.close()
        os.system( "sudo rm /etc/hostname" )
        os.system( "sudo mv temp /etc/hostname" )

        f = open( "/etc/hosts" )
        contents = f.read()
        newContents = string.replace( contents, currentHostName, hostname + " " )
        
        f = open( "temp","w" )
        f.write( newContents )
        f.close()

        os.system( "sudo rm /etc/hosts" )
        os.system( "sudo mv temp /etc/hosts" )
	os.system( "sudo hostname " + hostname + " &" )

    def setAccessPoint(self,name):
	print("Setting access point...")
        os.system( "sudo rm /etc/dnsmasq.d/access_point.conf" )

        f = open( "temp", "w" )
        f.write( "interface=wlan1\nexcept-interface=wlan0\ndhcp-range=172.20.0.100,172.20.0.250,1h" )
        f.close()

        os.system( "sudo mv temp /etc/dnsmasq.d/access_point.conf" )

        if( os.path.isfile( "/etc/network/interfaces" ) ):
            os.system( "sudo rm /etc/network/interfaces" )

        f = open( "temp", "w" )
        f.write( "source-directory /etc/network/interfaces.d\nauto wlan1\niface wlan1 inet static\n  address 172.20.0.1\n  netmask 255.255.255.0" )
        f.close()

        os.system( "sudo mv temp /etc/network/interfaces" )
        os.system( "sudo /etc/init.d/dnsmasq restart &" )

        if( os.path.isfile( "/etc/hostapd.conf" ) ):
            os.system( "sudo rm /etc/hostapd.conf" )

        f = open( "temp", "w" )
        f.write( "interface=wlan1\ndriver=nl80211\nssid="+name+"\nchannel=1\nctrl_interface=/var/run/hostapd" )
        f.close()

        os.system( "sudo mv temp /etc/hostapd.conf" )
        os.system( "sudo hostapd /etc/hostapd.conf &" )

        if( os.path.isfile( "/lib/systemd/system/hostapd-systemd.service" ) ):
            os.system( "sudo rm /lib/systemd/system/hostapd-systemd.service" )

        f = open( "temp", "w" )
        f.write( "[Unit]\nDescription=hostapd service\nWants=network-manager.service\nAfter=network-manager.service\nWants=module-init-tools.service\nAfter=module-init-tools.service\nConditionPathExists=/etc/hostapd.conf\n\n[Service]\nExecStart=/usr/sbin/hostapd /etc/hostapd.conf\n\n[Install]\nWantedBy=multi-user.target" )
	f.close()
        
        os.system( "sudo mv temp /lib/systemd/system/hostapd-systemd.service" )
        os.system( "sudo update-rc.d hostapd disable" )
        os.system( "sudo systemctl daemon-reload" )
        os.system( "sudo systemctl enable hostapd-systemd" )
        os.system( "sudo systemctl start hostapd-systemd" )
        os.system( "systemctl status hostapd-systemd" )

install = Setup()
