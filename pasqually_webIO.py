import os
import socket
import webiopi
if os.name != "nt":
    import fcntl
    import struct

class WebServer:
    macroFunc1 = None
    macroFunc2 = None

    def __init__(self, func1, func2 ):
        macroFunc1 = func1
        macroFunc2 = func2
        try:
            self.webio = webiopi.Server(port=8000, configfile="/etc/webiopi/config")
            self.webio.addMacro( macroFunc1 )
            self.webio.addMacro( macroFunc2 )
        except:
            print( "unable to start webiopi" )
            
        # Enable webcam
        res = "480x360"
        framerate = 24
        cmd = "/home/pi/mjpg-streamer/mjpg_streamer -i \"/usr/lib/input_uvc.so -n -d /dev/video0 -r " + res + " -f " + str( framerate ) + "\" -o \"/usr/lib/output_http.so -w /home/pi/mjpg-streamer/www -n -p 8080\" -b >/dev/null 2>&1"
        os.system(cmd)
        
    def get_interface_ip(self,ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])
    
    def getIP(self):
        ip = socket.gethostbyname(socket.gethostname())
        if ip.startswith("127.") and os.name != "nt":
            interfaces = [
                "eth0",
                "eth1",
                "eth2",
                "wlan0",
                "wlan1",
                "wifi0",
                "ath0",
                "ath1",
                "ppp0",
                ]
            for ifname in interfaces:
                try:
                    ip = self.get_interface_ip(ifname)
                    break
                except IOError:
                    pass
        return ip
        
    def shutdown(self):
        os.system('kill -9 `pidof mjpg_streamer`')
        self.webio.stop()