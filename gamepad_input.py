import eventlet
import evdev
from pydispatch import dispatcher
from evdev import InputDevice, categorize, ecodes, list_devices

class USBGamepadReader:
	def __init__(self):
		self.keyButtonMap = {
			"BTN_TL": 'a', # Left bumper = eyes left
			"BTN_TR": 'd', # Right bumper = eyes right
		}


		self.device = self._find_gamepad()
		if self.device:
			print(f"Gamepad detected: {self.device.name} ({self.device.path})")
			self.buttons = {}  # Dictionary to store the button states
			self.update_thread = eventlet.spawn(self.read_inputs)
		else:
			print("No gamepad detected. Please connect a gamepad.")

	def _find_gamepad(self):
		devices = [InputDevice(path) for path in list_devices()]
		for device in devices:
			# Filter out devices with 'hdmi' in their name, because Raspberry Pi weirdness.
			if 'hdmi' in device.name.lower():
				continue

			# Check device name for common gamepad-related keywords
			if any(keyword in device.name.lower() for keyword in ['gamepad', 'joystick', 'controller']):
				return device

			# Check for gamepad-specific event codes
			capabilities = device.capabilities()
			if (ecodes.ABS_X in capabilities.get(ecodes.EV_ABS, []) and 
				ecodes.BTN_GAMEPAD in capabilities.get(ecodes.EV_KEY, []) or 
				ecodes.BTN_JOYSTICK in capabilities.get(ecodes.EV_KEY, [])):
				return device
		return None

	def read_inputs(self):
		if not self.device:
			print("No gamepad device available to read inputs from.")
			return

		print(f"Listening for inputs on {self.device.name}...")

		try:
			for event in self.device.read_loop():
				# Process event only if it is a key press (button or joystick movement)
				if event.type == ecodes.EV_KEY:
					button_event = categorize(event)
					self._process_button_event(button_event)
				elif event.type == ecodes.EV_ABS:
					abs_event = categorize(event)
					self._process_abs_event(abs_event)
		except KeyboardInterrupt:
			print("\nStopping gamepad input listener.")

	def _dispatch_key_event(self, eventCode, value, bAnalog):
		processedValue = value
		keyCode = ''

		if eventCode in self.keyButtonMap:
			dispatcher.send(signal="keyEvent", key=self.keyButtonMap[eventCode], val=processedValue)

	def _process_button_event(self, event):
		keycode = event.keycode[0] if isinstance(event.keycode, list) else event.keycode  # Use the first keycode if it's a list

		if event.keystate == 1:  # Button press
			print(f"Button {keycode} pressed.")
			self.buttons[keycode] = True
			self._dispatch_key_event(keycode, 1, False)
		elif event.keystate == 0:  # Button release
			print(keycode)
			self.buttons[keycode] = False
			self._dispatch_key_event(keycode, 0, False)

	def _process_abs_event(self, event):
		"""
		Processes joystick or trigger movements (absolute axis events).
		"""
		print(f"Joystick/Axis {event.event.code} moved to {event.event.value}.")