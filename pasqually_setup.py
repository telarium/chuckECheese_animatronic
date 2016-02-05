#!/usr/bin/env python
#

import os
import sys
import string

class Setup:
    def __init__(self):
        self.settingsFile = os.path.dirname(os.path.realpath(sys.argv[0])) + "/settings.txt"
        if( not os.path.isfile( self.settingsFile ) ):
            hostname = raw_input("Enter hostname for Pasqually so you can easily identify him on your network?\nif unsure, just press enter: ")
            if( len(hostname)>0 and hostname != " " ):
                self.setHostname(hostname)

    def setHostname(self,hostname):
        f = open( "temp","w" )
        currentHostName = open( "/etc/hostname", "r" ).read()
        f.write( hostname )
        f.close()
        os.system( "sudo rm /etc/hostname" )
        os.system( "sudo mv temp /etc/hostname" )

        f = open( "/etc/hosts" )
        contents = f.read()
        newContents = string.replace( contents, currentHostName, hostname )
        
        f = open( "temp","w" )
        f.write( newContents )
        f.close()

        os.system( "sudo rm /etc/hosts" )
        os.system( "sudo mv temp /etc/hosts" )
