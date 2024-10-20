import eventlet
import evdev
from pydispatch import dispatcher
from evdev import InputDevice, categorize, ecodes, list_devices
from enum import Enum
from dataclasses import dataclass, field

class Button(Enum):
	# Bumpers
	LEFT_BUMPER = 'q'               # eyes left
	RIGHT_BUMPER = 'e'              # eyes right

	# Left Stick Directions
	LEFT_STICK_LEFT = 'a'           # neck left
	LEFT_STICK_RIGHT = 'd'          # neck right
	LEFT_STICK_DOWN = 's'           # neck down

	# Right Stick Directions
	RIGHT_STICK_LEFT = 'i'          # both shoulders move out
	RIGHT_STICK_RIGHT = 'i'         # both shoulders move out (duplicate)
	RIGHT_STICK_DOWN = 'k'          # both arms down

	# Triggers mapped to 'z' and 'x'
	LEFT_TRIGGER = 'z'              # mustache
	RIGHT_TRIGGER = 'x'             # mouth

	# Additional Buttons
	BTN_A = 'j'                     # left arm down
	BTN_B = 'l'                     # right arm down
	BTN_NORTH = 'u'                 # left shoulder out
	BTN_WEST = 'o'                  # right shoulder out

	# Hat (analog stick button)
	BTN_THUMBL = 'w'                # blink
	BTN_THUMBR = 'w'                # blink

	# D-pad
	DPAD_LEFT = 'a'					# neck left
	DPAD_RIGHT = 'd'				# neck right
	DPAD_DOWN = 's'					# head down
	DPAD_UP = 'w'					# blink

class Direction(Enum):
	NEUTRAL = 'neutral'
	UP = 'up'
	DOWN = 'down'
	LEFT = 'left'
	RIGHT = 'right'
	UP_LEFT = 'up-left'
	UP_RIGHT = 'up-right'
	DOWN_LEFT = 'down-left'
	DOWN_RIGHT = 'down-right'

@dataclass
class StickState:
	direction: Direction = Direction.NEUTRAL
	x: int = 0
	y: int = 0

@dataclass
class GamepadState:
	buttons: dict = field(default_factory=dict)
	left_stick: StickState = field(default_factory=StickState)
	right_stick: StickState = field(default_factory=StickState)

class USBGamepadReader:
	def __init__(self):
		# Mapping of event codes to Button Enum using ecodes constants
		self.keyButtonMap = {
			# Bumpers
			ecodes.BTN_TL: Button.LEFT_BUMPER,
			ecodes.BTN_TR: Button.RIGHT_BUMPER,

			# Triggers mapped to their scancodes
			ecodes.BTN_TL2: Button.LEFT_TRIGGER,  # 312
			ecodes.BTN_TR2: Button.RIGHT_TRIGGER, # 313

			# Additional Buttons
			ecodes.BTN_A: Button.BTN_A,
			ecodes.BTN_B: Button.BTN_B,
			ecodes.BTN_WEST: Button.BTN_WEST,
			ecodes.BTN_NORTH: Button.BTN_NORTH,
			ecodes.BTN_THUMBL: Button.BTN_THUMBL,  # 317
			ecodes.BTN_THUMBR: Button.BTN_THUMBR,  # 318
			# You can add more mappings here if needed
		}

		self.device = self._find_gamepad()
		if self.device:
			print(f"Gamepad detected: {self.device.name} ({self.device.path})")
			self.buttons = {}  # Dictionary to store the button states
			# Retrieve axis ranges
			self.abs_ranges = self._get_abs_ranges()
			# Initialize stick positions and directions to center
			self.left_stick = StickState(
				x=(self.abs_ranges.get(ecodes.ABS_X, {}).get('min', 0) + self.abs_ranges.get(ecodes.ABS_X, {}).get('max', 255)) / 2,
				y=(self.abs_ranges.get(ecodes.ABS_Y, {}).get('min', 0) + self.abs_ranges.get(ecodes.ABS_Y, {}).get('max', 255)) / 2
			)
			self.right_stick = StickState(
				x=(self.abs_ranges.get(ecodes.ABS_Z, {}).get('min', 0) + self.abs_ranges.get(ecodes.ABS_Z, {}).get('max', 255)) / 2,
				y=(self.abs_ranges.get(ecodes.ABS_RZ, {}).get('min', 0) + self.abs_ranges.get(ecodes.ABS_RZ, {}).get('max', 255)) / 2
			)
			# Initialize trigger states
			self.left_trigger_pressed = False
			self.right_trigger_pressed = False
			# Initialize D-pad states
			self.dpad_left_pressed = False
			self.dpad_right_pressed = False
			self.dpad_up_pressed = False
			self.dpad_down_pressed = False
			# Start the input reading thread
			self.update_thread = eventlet.spawn(self.read_inputs)
		else:
			print("No gamepad detected.")

	def _find_gamepad(self):
		devices = [InputDevice(path) for path in list_devices()]
		for device in devices:
			if 'hdmi' in device.name.lower():
				continue

			if any(keyword in device.name.lower() for keyword in ['gamepad', 'joystick', 'controller']):
				return device

			capabilities = device.capabilities()
			if (ecodes.ABS_X in capabilities.get(ecodes.EV_ABS, []) and
				(ecodes.BTN_GAMEPAD in capabilities.get(ecodes.EV_KEY, []) or
				 ecodes.BTN_JOYSTICK in capabilities.get(ecodes.EV_KEY, []))):
				return device
		return None

	def _get_abs_ranges(self):
		abs_info = self.device.capabilities().get(ecodes.EV_ABS, [])
		ranges = {}
		if not abs_info:
			print("No absolute axis information found.")
		for code, info in abs_info:
			if not isinstance(info, tuple) or len(info) < 6:
				continue
			min_val = info[1]
			max_val = info[2]
			ranges[code] = {'min': min_val, 'max': max_val}
			axis_name = ecodes.ABS.get(code, f"code_{code}")
			# Uncomment the next line to print axis ranges for debugging
			# print(f"Axis {axis_name}: min={min_val}, max={max_val}")
		return ranges

	def read_inputs(self):
		if not self.device:
			print("No gamepad device available to read inputs from.")
			return

		print(f"Listening for inputs on {self.device.name}...")

		try:
			for event in self.device.read_loop():
				if event.type == ecodes.EV_KEY:
					button_event = categorize(event)
					self._process_button_event(button_event)
				elif event.type == ecodes.EV_ABS:
					abs_event = categorize(event)
					self._process_abs_event(abs_event)
		except KeyboardInterrupt:
			print("\nStopping gamepad input listener.")

	def _dispatch_key_event(self, key: str, value: int, bAnalog: bool):
		dispatcher.send(signal="keyEvent", key=key, val=value)

	def _process_button_event(self, event):
		keycode = event.scancode  # Use scancode, which is an integer

		if keycode in self.keyButtonMap:
			button = self.keyButtonMap[keycode]
			if event.keystate == 1:  # Button press
				#print(f"Button {button.name} pressed.")
				self.buttons[keycode] = True
				self._dispatch_key_event(button.value, 1, False)
			elif event.keystate == 0:  # Button release
				#print(f"Button {button.name} released.")
				self.buttons[keycode] = False
				self._dispatch_key_event(button.value, 0, False)
		#else:
			# Optionally print unhandled button events
			#print(f"Unhandled button event: scancode={keycode}, keystate={event.keystate}")

	def _process_abs_event(self, event):
		# Define axis codes for left and right sticks
		LEFT_X = ecodes.ABS_X
		LEFT_Y = ecodes.ABS_Y
		RIGHT_X = ecodes.ABS_Z      # Corrected to match your controller
		RIGHT_Y = ecodes.ABS_RZ     # Corrected to match your controller

		stick_prefix = ""
		direction = Direction.NEUTRAL

		# Update stick positions and calculate new direction
		if event.event.code == LEFT_X:
			self.left_stick.x = event.event.value
			direction = self.get_direction('left', self.left_stick.x, self.left_stick.y)
			if direction != self.left_stick.direction:
				self.left_stick.direction = direction
				stick_prefix = "LEFT_STICK_"
		elif event.event.code == LEFT_Y:
			self.left_stick.y = event.event.value
			direction = self.get_direction('left', self.left_stick.x, self.left_stick.y)
			if direction != self.left_stick.direction:
				self.left_stick.direction = direction
				stick_prefix = "LEFT_STICK_"
		elif event.event.code == RIGHT_X:
			self.right_stick.x = event.event.value
			direction = self.get_direction('right', self.right_stick.x, self.right_stick.y)
			if direction != self.right_stick.direction:
				self.right_stick.direction = direction
				stick_prefix = "RIGHT_STICK_"
		elif event.event.code == RIGHT_Y:
			self.right_stick.y = event.event.value
			direction = self.get_direction('right', self.right_stick.x, self.right_stick.y)
			if direction != self.right_stick.direction:
				self.right_stick.direction = direction
				stick_prefix = "RIGHT_STICK_"
		elif event.event.code == ecodes.ABS_HAT0X:
			# D-pad left/right
			if event.event.value == -1:
				# D-pad left pressed
				if not self.dpad_left_pressed:
					self._dispatch_key_event(Button.DPAD_LEFT.value, 1, False)
					self.dpad_left_pressed = True
				if self.dpad_right_pressed:
					self._dispatch_key_event(Button.DPAD_RIGHT.value, 0, False)
					self.dpad_right_pressed = False
			elif event.event.value == 1:
				# D-pad right pressed
				if not self.dpad_right_pressed:
					self._dispatch_key_event(Button.DPAD_RIGHT.value, 1, False)
					self.dpad_right_pressed = True
				if self.dpad_left_pressed:
					self._dispatch_key_event(Button.DPAD_LEFT.value, 0, False)
					self.dpad_left_pressed = False
			else:
				# D-pad left/right released
				if self.dpad_left_pressed:
					self._dispatch_key_event(Button.DPAD_LEFT.value, 0, False)
					self.dpad_left_pressed = False
				if self.dpad_right_pressed:
					self._dispatch_key_event(Button.DPAD_RIGHT.value, 0, False)
					self.dpad_right_pressed = False
		elif event.event.code == ecodes.ABS_HAT0Y:
			# D-pad up/down
			if event.event.value == -1:
				# D-pad up pressed
				if not self.dpad_up_pressed:
					self._dispatch_key_event(Button.DPAD_UP.value, 1, False)
					self.dpad_up_pressed = True
				if self.dpad_down_pressed:
					self._dispatch_key_event(Button.DPAD_DOWN.value, 0, False)
					self.dpad_down_pressed = False
			elif event.event.value == 1:
				# D-pad down pressed
				if not self.dpad_down_pressed:
					self._dispatch_key_event(Button.DPAD_DOWN.value, 1, False)
					self.dpad_down_pressed = True
				if self.dpad_up_pressed:
					self._dispatch_key_event(Button.DPAD_UP.value, 0, False)
					self.dpad_up_pressed = False
			else:
				# D-pad up/down released
				if self.dpad_up_pressed:
					self._dispatch_key_event(Button.DPAD_UP.value, 0, False)
					self.dpad_up_pressed = False
				if self.dpad_down_pressed:
					self._dispatch_key_event(Button.DPAD_DOWN.value, 0, False)
					self.dpad_down_pressed = False
		else:
			axis_name = ecodes.ABS.get(event.event.code, f"code_{event.event.code}")
			#print(f"Unhandled Axis {axis_name} (code {event.event.code}) moved to {event.event.value}.")
			return  # Exit the function since we have nothing to process

		if stick_prefix:
			current_direction = self.left_stick.direction if "LEFT" in stick_prefix else self.right_stick.direction
			
			# Determine related keys based on stick prefix
			related_keys = []
			if "LEFT_STICK" in stick_prefix:
				related_keys = [
					Button.LEFT_STICK_LEFT.value,
					Button.LEFT_STICK_RIGHT.value,
					Button.LEFT_STICK_DOWN.value
				]
			elif "RIGHT_STICK" in stick_prefix:
				related_keys = [
					Button.RIGHT_STICK_LEFT.value,
					Button.RIGHT_STICK_RIGHT.value,
					#Button.RIGHT_STICK_UP.value,
					Button.RIGHT_STICK_DOWN.value
				]

			# Release all related keys first
			for key in related_keys:
				self._dispatch_key_event(key, 0, False)

			# Collect all relevant directions
			mapped_keys = []

			if 'up' in current_direction.value:
				mapped_keys.append(stick_prefix + "UP")
			if 'down' in current_direction.value:
				mapped_keys.append(stick_prefix + "DOWN")
			if 'left' in current_direction.value:
				mapped_keys.append(stick_prefix + "LEFT")
			if 'right' in current_direction.value:
				mapped_keys.append(stick_prefix + "RIGHT")

			# Dispatch key events for each direction
			for mapped in mapped_keys:
				# Handle stick directions
				if mapped.startswith("LEFT_STICK_") or mapped.startswith("RIGHT_STICK_"):
					button_name = mapped
					# Map the direction to the Button enum
					button = getattr(Button, button_name, None)
					if button:
						self._dispatch_key_event(button.value, 1, False)
				else:
					# For other mappings, use keyButtonMap
					button = self.keyButtonMap.get(mapped)
					if button:
						self._dispatch_key_event(button.value, 1, False)

	def get_direction(self, stick: str, x: int, y: int) -> Direction:
		if stick == 'left':
			axis_x = ecodes.ABS_X
			axis_y = ecodes.ABS_Y
		elif stick == 'right':
			axis_x = ecodes.ABS_Z      # Corrected to match your controller
			axis_y = ecodes.ABS_RZ     # Corrected to match your controller
		else:
			return Direction.NEUTRAL

		# Retrieve axis ranges
		min_x = self.abs_ranges.get(axis_x, {}).get('min', 0)
		max_x = self.abs_ranges.get(axis_x, {}).get('max', 255)
		min_y = self.abs_ranges.get(axis_y, {}).get('min', 0)
		max_y = self.abs_ranges.get(axis_y, {}).get('max', 255)

		# Calculate center for each axis
		center_x = (min_x + max_x) / 2
		center_y = (min_y + max_y) / 2

		# Normalize the axis values to a range of -1 to 1
		normalized_x = (x - center_x) / ((max_x - center_x) if (max_x - center_x) != 0 else 1)
		normalized_y = (y - center_y) / ((max_y - center_y) if (max_y - center_y) != 0 else 1)

		# Define dead zone
		DEAD_ZONE = 0.2

		# Apply dead zone
		if abs(normalized_x) < DEAD_ZONE:
			normalized_x = 0
		if abs(normalized_y) < DEAD_ZONE:
			normalized_y = 0

		# Define a threshold to determine directional input
		threshold = 0.3

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
			return Direction.NEUTRAL

		direction_map = {
			'up': Direction.UP,
			'down': Direction.DOWN,
			'left': Direction.LEFT,
			'right': Direction.RIGHT,
			'up-right': Direction.UP_RIGHT,
			'up-left': Direction.UP_LEFT,
			'down-right': Direction.DOWN_RIGHT,
			'down-left': Direction.DOWN_LEFT,
		}

		determined_direction = direction_map.get(direction, Direction.NEUTRAL)
		return determined_direction
