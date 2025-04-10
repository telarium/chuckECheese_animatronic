import threading
import time
from evdev import InputDevice, categorize, ecodes, list_devices, InputEvent
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

class Button(Enum):
	# Bumpers
	LEFT_BUMPER = 'q'               # eyes left
	RIGHT_BUMPER = 'e'              # eyes right

	# Left Stick
	LEFT_STICK_LEFT = 'a'           # neck left
	LEFT_STICK_RIGHT = 'd'          # neck right
	LEFT_STICK_UP = 's'             # neck up

	# Right Stick
	RIGHT_STICK_LEFT = 'i'          # both shoulders move out
	RIGHT_STICK_RIGHT = 'i'         # both shoulders move out (duplicate)
	RIGHT_STICK_DOWN = 'k'          # both arms down

	# Triggers
	LEFT_TRIGGER = 'z'              # mustache
	RIGHT_TRIGGER = 'x'             # mouth

	# Face Buttons
	BTN_A = 'j'                   # left arm down
	BTN_B = 'l'                   # right arm down
	BTN_NORTH = 'u'               # left shoulder out
	BTN_WEST = 'o'                # right shoulder out

	# Hat (analog stick button)
	BTN_THUMBL = 'w'              # blink
	BTN_THUMBR = 'w'              # blink

	# D-pad
	DPAD_LEFT = 'a'               # neck left
	DPAD_RIGHT = 'd'              # neck right
	DPAD_DOWN = 'w'               # head up
	DPAD_UP = 's'                # blink

	# Start and Select Buttons. Holding down both toggles mirrored mode
	START = 'start'
	SELECT = 'select'

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

class USBGamepadReader:
	def __init__(self, movements: Any, web_server: Any) -> None:
		self.movements = movements
		self.web_server = web_server

		self.head_nod_inverted: bool = False

		self.start_button_down: bool = False
		self.select_button_down: bool = False

		# Mapping of event codes to Button Enum using ecodes constants
		self.key_button_map: Dict[int, Button] = {
			# Bumpers
			ecodes.BTN_TL: Button.LEFT_BUMPER,
			ecodes.BTN_TR: Button.RIGHT_BUMPER,

			# Triggers
			ecodes.BTN_TL2: Button.LEFT_TRIGGER,
			ecodes.BTN_TR2: Button.RIGHT_TRIGGER,

			# Additional Buttons
			ecodes.BTN_A: Button.BTN_A,
			ecodes.BTN_B: Button.BTN_B,
			ecodes.BTN_WEST: Button.BTN_WEST,
			ecodes.BTN_NORTH: Button.BTN_NORTH,
			ecodes.BTN_THUMBL: Button.BTN_THUMBL,
			ecodes.BTN_THUMBR: Button.BTN_THUMBR,

			# Start and Select Buttons (using arbitrary codes 314 and 315)
			314: Button.SELECT,
			315: Button.START,
		}

		self.device: Optional[InputDevice] = self._find_gamepad()
		if self.device:
			print(f"Gamepad detected: {self.device.name} ({self.device.path})")
			# Initialize stick positions and directions to center
			self.left_stick: StickState = StickState()
			self.right_stick: StickState = StickState()
			# Initialize D-pad states
			self.dpad_states: Dict[str, bool] = {'left': False, 'right': False, 'up': False, 'down': False}
			# Retrieve axis ranges
			self.abs_ranges: Dict[int, Dict[str, int]] = self._get_abs_ranges()
			# Start the input reading thread using standard threading
			self.update_thread: threading.Thread = threading.Thread(target=self.read_inputs, daemon=True)
			self.update_thread.start()
		else:
			print("No gamepad detected.")

	def _find_gamepad(self) -> Optional[InputDevice]:
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

	def _get_abs_ranges(self) -> Dict[int, Dict[str, int]]:
		abs_info = self.device.capabilities().get(ecodes.EV_ABS, []) if self.device else []
		ranges: Dict[int, Dict[str, int]] = {}
		for code, info in abs_info:
			if isinstance(info, tuple) and len(info) >= 6:
				min_val, max_val = info[1], info[2]
				ranges[code] = {'min': min_val, 'max': max_val}
		return ranges

	def read_inputs(self) -> None:
		while True:
			# If the device isn't set, try to find it again.
			if not self.device:
				print("No gamepad device available. Trying to reconnect...")
				self.device = self._find_gamepad()
				if self.device:
					print(f"Reconnected to {self.device.name} ({self.device.path})")
					self.abs_ranges = self._get_abs_ranges()
				else:
					time.sleep(2)
					continue

			print(f"Listening for inputs on {self.device.name}...")
			try:
				for event in self.device.read_loop():
					if event.type == ecodes.EV_KEY:
						self._process_button_event(event)
					elif event.type == ecodes.EV_ABS:
						self._process_abs_event(event)
			except OSError as e:
				print(f"Device error: {e}. Attempting to reconnect...")
				self.device = None  # Invalidate the current device so we try to find it again
				time.sleep(1)  # Brief pause before attempting reconnection

	def _dispatch_key_event(self, key: str, val: int) -> None:
		# Tell the HTML front end that a gamepad event occurred so that it can play the corresponding MIDI note
		if key == self.movements.head_nod.key and self.head_nod_inverted:
			val = 1 - val
		try:
			if self.movements.execute_movement(str(key).lower(), val):
				self.web_server.broadcast('gamepadKeyEvent', [str(key).lower(), val])
		except Exception as e:
			print(f"Invalid key: {e}")

	def _process_button_event(self, event: InputEvent) -> None:
		keycode = event.code

		if keycode in self.key_button_map:
			button = self.key_button_map[keycode]
			self._dispatch_key_event(button.value, event.value)

			# Update Start and Select button states
			if button == Button.START:
				self.start_button_down = bool(event.value)
			elif button == Button.SELECT:
				self.select_button_down = bool(event.value)

			# Check if both Start and Select are pressed, which toggles mirrored mode.
			if self.start_button_down and self.select_button_down:
				from pydispatch import dispatcher  # Import here to avoid circular dependency if any
				dispatcher.send(signal="mirrorModeToggle")

	def _process_abs_event(self, event: InputEvent) -> None:
		code = event.code
		value = event.value

		# D-pad handling
		if code == ecodes.ABS_HAT0X:
			self._handle_dpad('left', 'right', value)
		elif code == ecodes.ABS_HAT0Y:
			self._handle_dpad('up', 'down', value)
		else:
			self._handle_stick(event)

	def _handle_dpad(self, negative_dir: str, positive_dir: str, value: int) -> None:
		if value == -1:
			self._set_dpad_state(negative_dir, True)
			self._set_dpad_state(positive_dir, False)
		elif value == 1:
			self._set_dpad_state(negative_dir, False)
			self._set_dpad_state(positive_dir, True)
		else:
			self._set_dpad_state(negative_dir, False)
			self._set_dpad_state(positive_dir, False)

	def _set_dpad_state(self, direction: str, pressed: bool) -> None:
		button = getattr(Button, f"DPAD_{direction.upper()}", None)
		if button and self.dpad_states[direction] != pressed:
			self.dpad_states[direction] = pressed
			self._dispatch_key_event(button.value, int(pressed))

	def _handle_stick(self, event: InputEvent) -> None:
		axis_map = {
			ecodes.ABS_X: ('left', 'x'),
			ecodes.ABS_Y: ('left', 'y'),
			ecodes.ABS_Z: ('right', 'x'),
			ecodes.ABS_RZ: ('right', 'y')
		}
		if event.code in axis_map:
			stick, axis = axis_map[event.code]
			stick_state: StickState = getattr(self, f"{stick}_stick")
			setattr(stick_state, axis, event.value)
			direction = self._get_direction(stick, stick_state.x, stick_state.y)
			if direction != stick_state.direction:
				self._update_stick_direction(stick_state, direction, stick)

	def _update_stick_direction(self, stick_state: StickState, new_direction: Direction, stick: str) -> None:
		# Release previous direction keys
		self._change_stick_keys(stick_state.direction, stick, pressed=False)
		# Update direction
		stick_state.direction = new_direction
		# Press new direction keys
		self._change_stick_keys(new_direction, stick, pressed=True)

	def _change_stick_keys(self, direction: Direction, stick: str, pressed: bool) -> None:
		if direction != Direction.NEUTRAL:
			keys: List[Button] = self._direction_to_keys(direction, stick)
			for key in keys:
				self._dispatch_key_event(key.value, int(pressed))

	def _direction_to_keys(self, direction: Direction, stick: str) -> List[Button]:
		directions = direction.value.split('-')
		keys: List[Button] = []
		for dir in directions:
			button_name = f"{stick.upper()}_STICK_{dir.upper()}"
			button = getattr(Button, button_name, None)
			if button:
				keys.append(button)
		return keys

	def _get_direction(self, stick: str, x: int, y: int) -> Direction:
		axis_x = ecodes.ABS_X if stick == 'left' else ecodes.ABS_Z
		axis_y = ecodes.ABS_Y if stick == 'left' else ecodes.ABS_RZ

		# Get axis ranges
		min_x, max_x = self.abs_ranges[axis_x]['min'], self.abs_ranges[axis_x]['max']
		min_y, max_y = self.abs_ranges[axis_y]['min'], self.abs_ranges[axis_y]['max']

		# Normalize values to -1 to 1
		norm_x = (2 * (x - min_x) / (max_x - min_x)) - 1
		norm_y = (2 * (y - min_y) / (max_y - min_y)) - 1

		# Apply dead zone
		DEAD_ZONE = 0.2
		norm_x = norm_x if abs(norm_x) > DEAD_ZONE else 0
		norm_y = norm_y if abs(norm_y) > DEAD_ZONE else 0

		direction_parts = []
		if norm_y < -DEAD_ZONE:
			direction_parts.append('up')
		elif norm_y > DEAD_ZONE:
			direction_parts.append('down')
		if norm_x < -DEAD_ZONE:
			direction_parts.append('left')
		elif norm_x > DEAD_ZONE:
			direction_parts.append('right')

		if direction_parts:
			return Direction('-'.join(direction_parts))
		else:
			return Direction.NEUTRAL
