#!/usr/bin/env python
#

import os
import sys
import string

class Setup:
    def __init__(self):
        self.settingsFile = os.path.dirname(os.path.realpath(sys.argv[0])) + "/settings.txt"
        if( not os.path.isfile( self.settingsFile ) ):
            f = open( self.settingsFile, "w" )
            f.write( "hi" )
            f.close()

            hostname = raw_input("Enter hostname for Pasqually so you can easily identify him on your network?\nif unsure, just press enter: ")
            if( len(hostname)>0 and hostname != " " ):
                self.setHostname(hostname)

            apName = raw_input("Enter a name to create Pasqually's own wifi network?\nif unsure, just press enter: ")
            if( len(apName)>0 and apName != " " ):
                self.setAccessPoint(apName)

    def setHostname(self,hostname):
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
	os.system( "sudo hostname " + hostname )

    def setAccessPoint(self,name):
        if( not os.path.isfile( "/etc/dnsmasq.d/access_point.conf" ) ):
            os.system( "sudo apt-get install dnsmasq" )
        else:
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
        os.system( "sudo /etc/init.d/dnsmasq restart" )

        if( os.path.isfile( "/etc/hostapd.conf" ) ):
            os.system( "sudo rm /etc/hostapd.conf" )

        f = open( "temp", "w" )
        f.write( "interface=wlan1\ndriver=nl80211\nssid="+name+"\nchannel=1\nctrl_interface=/var/run/hostapd" )
        f.close()

        os.system( "sudo mv temp /etc/hostapd.conf" )
        os.system( "sudo hostapd /etc/hostapd.conf" )

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
