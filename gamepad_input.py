import eventlet
import evdev
from pydispatch import dispatcher
from evdev import InputDevice, categorize, ecodes, list_devices

class USBGamepadReader:
	def __init__(self):
		self.keyButtonMap = {
			"BTN_TL": 'q',  # Left bumper = eyes left
			"BTN_TR": 'e',  # Right bumper = eyes right
			"LEFT_STICK_LEFT": 'a', # Left stick left = neck left
			"LEFT_STICK_RIGHT": 'a', # Left stick right = neck right
			"LEFT_STICK_DOWN": 's', # Left stick down = neck down
			"RIGHT_STICK_LEFT": 'u', # Left stick left = neck left
			"RIGHT_STICK_RIGHT": 'o', # Left stick right = neck right
			"RIGHT_STICK_DOWN": 'j', # Left stick down = neck down
			"RIGHT_STICK_UP": 'l' # Left stick down = neck down
		}

		self.device = self._find_gamepad()
		if self.device:
			print(f"Gamepad detected: {self.device.name} ({self.device.path})")
			self.buttons = {}  # Dictionary to store the button states
			# Initialize stick positions and directions
			self.left_stick = {'x': 0, 'y': 0}
			self.right_stick = {'x': 0, 'y': 0}
			self.left_direction = 'neutral'
			self.right_direction = 'neutral'
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
				(ecodes.BTN_GAMEPAD in capabilities.get(ecodes.EV_KEY, []) or 
				 ecodes.BTN_JOYSTICK in capabilities.get(ecodes.EV_KEY, []))):
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
			print(f"Button {keycode} released.")
			self.buttons[keycode] = False
			self._dispatch_key_event(keycode, 0, False)

	def _process_abs_event(self, event):
		"""
		Processes joystick or trigger movements (absolute axis events) and
		prints them as D-pad-like directions.
		"""
		# Define axis codes for left and right sticks
		left_x = ecodes.ABS_X
		left_y = ecodes.ABS_Y
		right_x = ecodes.ABS_RX
		right_y = ecodes.ABS_RY

		stickPrefix = ""

		if event.event.code == left_x:
			self.left_stick['x'] = event.event.value
			new_direction = self.get_direction(self.left_stick['x'], self.left_stick['y'])
			if new_direction != self.left_direction:
				self.left_direction = new_direction
				stickPrefix = "LEFT_STICK_"
				
		elif event.event.code == left_y:
			self.left_stick['y'] = event.event.value
			new_direction = self.get_direction(self.left_stick['x'], self.left_stick['y'])
			if new_direction != self.left_direction:
				self.left_direction = new_direction
				stickPrefix = "LEFT_STICK_"
		elif event.event.code == right_x:
			self.right_stick['x'] = event.event.value
			new_direction = self.get_direction(self.right_stick['x'], self.right_stick['y'])
			if new_direction != self.right_direction:
				self.right_direction = new_direction
				stickPrefix = "RIGHT_STICK_"
		elif event.event.code == right_y:
			self.right_stick['y'] = event.event.value
			new_direction = self.get_direction(self.right_stick['x'], self.right_stick['y'])
			if new_direction != self.right_direction:
				self.right_direction = new_direction
				stickPrefix = "RIGHT_STICK_"
		else:
			# For other axes, retain existing behavior
			print(f"Joystick/Axis {event.event.code} moved to {event.event.value}.")

		direction = self.left_direction
		if "RIGHT" in stickPrefix:
			direction = self.right_direction

		if stickPrefix != "":
			print(stickPrefix)
			#print(f"Left Stick: {self.left_direction}")
			
			if "left" in direction:
				self._dispatch_key_event(stickPrefix + "LEFT", 1, False)
			else:
				self._dispatch_key_event(stickPrefix + "LEFT", 0, False)

			if "right" in direction:
				self._dispatch_key_event(stickPrefix + "RIGHT", 1, False)
			else:
				self._dispatch_key_event(stickPrefix + "RIGHT", 0, False)

			if "up" in direction:
				self._dispatch_key_event(stickPrefix + "UP", 1, False)
			else:
				self._dispatch_key_event(stickPrefix + "UP", 0, False)

			if "down" in direction:
				self._dispatch_key_event(stickPrefix + "DOWN", 1, False)
			else:
				self._dispatch_key_event(stickPrefix + "DOWN", 0, False)


	def get_direction(self, x, y):
		"""
		Converts raw analog stick values to D-pad-like directions.

		Args:
			x (int): The X-axis value.
			y (int): The Y-axis value.

		Returns:
			str: The direction as a string (e.g., 'up', 'down-left', 'neutral').
		"""
		# Normalize the axis values to a range of -1 to 1
		normalized_x = x / 32768.0
		normalized_y = y / 32768.0

		# Define a threshold to determine directional input
		threshold = 0.5  # Adjust as needed

		direction = ''

		if normalized_y > threshold:
			direction += 'down'
		elif normalized_y < -threshold:
			direction += 'up'

		if normalized_x > threshold:
			direction += '-right' if direction else 'right'
		elif normalized_x < -threshold:
			direction += '-left' if direction else 'left'

		if not direction:
			direction = 'neutral'

		return direction
