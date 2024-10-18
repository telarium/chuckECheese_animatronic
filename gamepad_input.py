import eventlet
import evdev
from pydispatch import dispatcher
from evdev import InputDevice, categorize, ecodes, list_devices
from enum import Enum
from dataclasses import dataclass, field

class Button(Enum):
    # Bumpers
    LEFT_BUMPER = 'q'               # BTN_TL = eyes left
    RIGHT_BUMPER = 'e'              # BTN_TR = eyes right

    # Left Stick Directions
    LEFT_STICK_LEFT = 'a'           # neck left
    LEFT_STICK_RIGHT = 'd'          # neck right
    LEFT_STICK_DOWN = 's'           # neck down

    # Right Stick Directions
    RIGHT_STICK_LEFT = 'u'          # neck left
    RIGHT_STICK_RIGHT = 'o'         # neck right
    RIGHT_STICK_UP = 'l'            # neck up
    RIGHT_STICK_DOWN = 'j'          # neck down

    # Triggers
    LEFT_TRIGGER = 'z'              # Left trigger maps to 'z'
    RIGHT_TRIGGER = 'x'             # Right trigger maps to 'x'

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
        # Mapping of event codes to Button Enum
        self.keyButtonMap = {
            "BTN_TL": Button.LEFT_BUMPER,
            "BTN_TR": Button.RIGHT_BUMPER,
            "LEFT_STICK_LEFT": Button.LEFT_STICK_LEFT,
            "LEFT_STICK_RIGHT": Button.LEFT_STICK_RIGHT,
            "LEFT_STICK_DOWN": Button.LEFT_STICK_DOWN,
            "RIGHT_STICK_LEFT": Button.RIGHT_STICK_LEFT,
            "RIGHT_STICK_RIGHT": Button.RIGHT_STICK_RIGHT,
            "RIGHT_STICK_UP": Button.RIGHT_STICK_UP,
            "RIGHT_STICK_DOWN": Button.RIGHT_STICK_DOWN,
            "LEFT_TRIGGER": Button.LEFT_TRIGGER,
            "RIGHT_TRIGGER": Button.RIGHT_TRIGGER,
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
            print(f"Initialized Left Stick to center: x={self.left_stick.x}, y={self.left_stick.y}")
            print(f"Initialized Right Stick to center: x={self.right_stick.x}, y={self.right_stick.y}")
            # Initialize trigger states
            self.left_trigger_pressed = False
            self.right_trigger_pressed = False
            # Start the input reading thread
            self.update_thread = eventlet.spawn(self.read_inputs)
        else:
            print("No gamepad detected. Please connect a gamepad.")

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
        keycode = event.keycode[0] if isinstance(event.keycode, list) else event.keycode

        if keycode in self.keyButtonMap:
            button = self.keyButtonMap[keycode]
            if event.keystate == 1:  # Button press
                print(f"Button {button.name} pressed.")
                self.buttons[keycode] = True
                self._dispatch_key_event(button.value, 1, False)
            elif event.keystate == 0:  # Button release
                print(f"Button {button.name} released.")
                self.buttons[keycode] = False
                self._dispatch_key_event(button.value, 0, False)

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
        elif event.event.code == ecodes.ABS_BRAKE:  # Updated for Left Trigger
            # Left trigger
            self._process_trigger_event('LEFT_TRIGGER', event.event.code, event.event.value)
        elif event.event.code == ecodes.ABS_GAS:    # Updated for Right Trigger
            # Right trigger
            self._process_trigger_event('RIGHT_TRIGGER', event.event.code, event.event.value)
        else:
            axis_name = ecodes.ABS.get(event.event.code, f"code_{event.event.code}")
            print(f"Unhandled Axis {axis_name} (code {event.event.code}) moved to {event.event.value}.")
            return  # Exit the function since we have nothing to process

        if stick_prefix:
            current_direction = self.left_stick.direction if "LEFT" in stick_prefix else self.right_stick.direction
            print(f"{stick_prefix} Direction: {current_direction.value}")
            
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
                    Button.RIGHT_STICK_UP.value,
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
                button = self.keyButtonMap.get(mapped)
                if button:
                    self._dispatch_key_event(button.value, 1, False)

    def _process_trigger_event(self, trigger_name, code, value):
        threshold = 0.5  # Adjust this threshold as necessary
        max_val = self.abs_ranges.get(code, {}).get('max', 255)
        normalized_value = value / max_val if max_val else 0
        button = self.keyButtonMap.get(trigger_name)
        if button:
            if trigger_name == 'LEFT_TRIGGER':
                if normalized_value > threshold and not self.left_trigger_pressed:
                    self.left_trigger_pressed = True
                    print(f"Left trigger pressed. Dispatching '{button.value}' key event.")
                    self._dispatch_key_event(button.value, 1, False)
                elif normalized_value <= threshold and self.left_trigger_pressed:
                    self.left_trigger_pressed = False
                    print(f"Left trigger released. Dispatching '{button.value}' key release event.")
                    self._dispatch_key_event(button.value, 0, False)
            elif trigger_name == 'RIGHT_TRIGGER':
                if normalized_value > threshold and not self.right_trigger_pressed:
                    self.right_trigger_pressed = True
                    print(f"Right trigger pressed. Dispatching '{button.value}' key event.")
                    self._dispatch_key_event(button.value, 1, False)
                elif normalized_value <= threshold and self.right_trigger_pressed:
                    self.right_trigger_pressed = False
                    print(f"Right trigger released. Dispatching '{button.value}' key release event.")
                    self._dispatch_key_event(button.value, 0, False)

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
