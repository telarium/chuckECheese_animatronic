import os
import psutil
import eventlet
import subprocess
import re

class SystemInfo:
    def __init__(self, webServer):
        self.webServer = webServer
        self.update_thread = eventlet.spawn(self.update)

    def update(self):
        while True:
            try:
                eventlet.sleep(3)

                info = {
                    'cpu': int(psutil.cpu_percent()),
                    'ram': int(psutil.virtual_memory().percent),
                    'disk': self.get_disk_usage(),
                    'temperature': self.get_temperature(),
                    'wifi_signal': self.get_signal_strength()
                }

                self.webServer.broadcast('systemInfo', info)

            except Exception as e:
                print(f"Exception in update thread: {e}")

    def get_disk_usage(self):
        """Get the disk usage percentage."""
        return int(psutil.disk_usage('/').percent)

    def get_temperature(self):
        """Get the temperature of the CPU."""
        try:
            # For Raspberry Pi
            temp_file = '/sys/class/thermal/thermal_zone0/temp'
            if os.path.exists(temp_file):
                with open(temp_file, 'r') as f:
                    temp = float(f.read()) / 1000
                    return round(temp, 2)
        except Exception as e:
            print(f"Exception getting temperature: {e}")
        return None

    def get_signal_strength(self):
	    """Get the WiFi signal strength."""
	    try:
	        # Replace 'wlan0' with your actual WiFi interface name if different
	        result = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True)
	        output = result.stdout

	        # Use regex to find the signal level
	        match = re.search(r'Signal level=(-?\d+)', output)
	        if match:
	            return int(match.group(1))
	    except Exception as e:
	        print(f"Exception getting WiFi signal strength: {e}")
	    return None
