import os
import sys
import time
from pydispatch import dispatcher
from web_io import WebServer
from system_info import SystemInfo
from gpio import GPIO
from animatronic_movements import Movement
from gamepad_input import USBGamepadReader

class Pasqually:
    def __init__(self):
        self.gpio = GPIO()
        self.movements = Movement(self.gpio)
        self.webServer = WebServer()
        self.systemInfo = SystemInfo(self.webServer)
        self.gamepad = USBGamepadReader()
        self.setDispatchEvents()
        self.isRunning = True

    def setDispatchEvents(self):
        dispatcher.connect(self.onKeyEvent, signal="keyEvent", sender=dispatcher.Any)
        dispatcher.connect(self.onConnectEvent, signal="connectEvent", sender=dispatcher.Any)

    def onSystemInfoEvent(self, cpu, ram):
        print(cpu)

    def onConnectEvent(self):
        self.webServer.broadcast('movementInfo', self.movements.getKeyboardKeys())

    def onKeyEvent(self, key, val):
        try:
            self.movements.executeMovement(str(key).lower(), val)
        except Exception as e:
            print(f"Invalid key: {e}")

    def run(self):
        try:
            while self.isRunning:
                time.sleep(0.01)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        if self.webServer:
            self.webServer.shutdown()

if __name__ == "__main__":
    animatronic = Pasqually()
    animatronic.run()
