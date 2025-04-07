from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any
from pydispatch import dispatcher
from midi import MIDI
import time
import threading
import random

# Valve1  -> 0x20, GP0	-> Eye right
# Valve2  -> 0x21, GP4	-> Eye left
# Valve3  -> 0x20, GP1	-> Eyelid Up
# Valve4  -> 0x21, GP5	-> Eyelid down
# Valve5  -> 0x20, GP2	-> Mustache
# Valve6  -> NONE
# Valve7  -> 0x20, GP3	-> Neck down
# Valve8  -> 0x21, GP6	-> Neck up
# Valve9  -> 0x20, GP4	-> Left shoulder out
# Valve10 -> 0x21, GP7	-> Left shoulder in
# Valve11 -> 0x20, GP5	-> --unused--
# Valve12 -> 0x23, GP0	-> --unused--
# Valve13 -> 0x20, GP6	-> Left arm down
# Valve14 -> 0x23, GP1	-> Left arm up
# Valve15 -> 0x20, GP7	-> Mouth open
# Valve16 -> 0x23, GP2	-> Mouth closed
# Valve17 -> 0x21, GP0	-> Neck/torso left
# Valve18 -> 0x23, GP3	-> Neck/torso right
# Valve19 -> 0x21, GP1	-> Lean forward
# Valve20 -> 0x23, GP4	-> Lean Backward
# Valve21 -> 0x21, GP2	-> Right arm down
# Valve22 -> 0x23, GP5	-> Right arm up
# Valve23 -> 0x21, GP3	-> Right shoulder in
# Valve24 -> 0x23, GP6	-> Right shoulder out
# Valve25 -> NONE (COM 24v)
# Valve26 -> 0x23, GP7	-> --unused--

@dataclass
class MovementStruct:
	key: str = ''  # A keyboard key press assigned to this movement
	description: str = ""  # A handy description of this movement
	output_pin1: List[Any] = field(default_factory=list)  # Index 0: I2C address, index 1: pin number
	output_pin2: List[Any] = field(default_factory=list)  # Optional second IO pin array (usually the inverse of output_pin1)
	midi_note: int = 0  # A MIDI note assigned to this movement to be recorded in a sequencer
	output_pin1_max_time: float = -1  # Maximum time (in seconds) for pin 1 to remain high (-1 means infinite)
	output_pin2_max_time: float = -1  # Maximum time for pin 2 (-1 means infinite)
	output_inverted: bool = False  # Invert high/low for this movement
	callback_func: Optional[Callable[[Any, int], None]] = None  # Function to call when value changes
	linked_keys: List[str] = field(default_factory=list)  # Combined movement: list of keys to trigger together
	mirrored_key: Optional[str] = None  # Alternate key for mirroring (e.g., swapping left/right)
	b_is_original_movement: bool = False  # Whether this movement is part of the original 1981 animatronic
	b_enable_on_retro_mode: bool = False  # In retro mode, enable only original movements
	key_is_pressed: bool = False  # Tracks if the key is currently pressed
	pin1_time: float = 0  # Timer for output_pin1
	pin2_time: float = 0  # Timer for output_pin2

class Movement:
	all: List[MovementStruct] = []

	def __init__(self, gpio: Any) -> None:
		self.b_mirrored: bool = False  # Swap left/right body movement to mirror animation
		self.b_retro_mode_active: bool = False  # Retro mode disables any movement not part of the original Pasqually
		self.gpio = gpio
		self.midi = MIDI()
		self.b_thread_started: bool = False

		# Define movements
		self.right_shoulder = MovementStruct()
		self.right_shoulder.description = "Shoulder R"
		self.right_shoulder.key = 'o'
		self.right_shoulder.output_pin2 = [0x23, 6]  # Shoulder out
		self.right_shoulder.output_pin1 = [0x21, 3]  # Shoulder in
		self.right_shoulder.output_pin2_max_time = 5 * 60
		self.right_shoulder.output_pin1_max_time = 5 * 60
		self.right_shoulder.midi_note = 50
		self.right_shoulder.mirrored_key = 'u'
		self.right_shoulder.b_is_original_movement = True
		self.all.append(self.right_shoulder)

		self.left_shoulder = MovementStruct()
		self.left_shoulder.description = "Shoulder L"
		self.left_shoulder.key = 'u'
		self.left_shoulder.output_pin2 = [0x20, 4]  # Shoulder out
		self.left_shoulder.output_pin1 = [0x21, 7]  # Shoulder in
		self.left_shoulder.output_pin2_max_time = 5 * 60
		self.left_shoulder.output_pin1_max_time = 5 * 60
		self.left_shoulder.midi_note = 51
		self.left_shoulder.mirrored_key = 'o'
		self.left_shoulder.b_is_original_movement = True
		self.all.append(self.left_shoulder)

		self.left_and_right_arms = MovementStruct()
		self.left_and_right_arms.description = "Arms L+R"
		self.left_and_right_arms.key = 'i'
		self.left_and_right_arms.midi_note = 52
		self.left_and_right_arms.linked_keys = ['u', 'o']
		self.all.append(self.left_and_right_arms)

		self.right_elbow = MovementStruct()
		self.right_elbow.key = 'l'
		self.right_elbow.description = "Elbow R"
		self.right_elbow.output_pin2 = [0x23, 5]  # Arm up
		self.right_elbow.output_pin1 = [0x21, 2]  # Arm down
		self.right_elbow.midi_note = 53
		self.right_elbow.mirrored_key = 'j'
		self.all.append(self.right_elbow)

		self.left_elbow = MovementStruct()
		self.left_elbow.description = "Elbow L"
		self.left_elbow.key = 'j'
		self.left_elbow.output_pin2 = [0x23, 1]  # Arm up
		self.left_elbow.output_pin1 = [0x20, 6]  # Arm down
		self.left_elbow.midi_note = 54
		self.left_elbow.mirrored_key = 'l'
		self.all.append(self.left_elbow)

		self.left_and_right_elbows = MovementStruct()
		self.left_and_right_elbows.description = "Elbows L+R"
		self.left_and_right_elbows.key = 'k'
		self.left_and_right_elbows.midi_note = 55
		self.left_and_right_elbows.linked_keys = ['j', 'l']
		self.all.append(self.left_and_right_elbows)

		self.mouth = MovementStruct()
		self.mouth.description = "Mouth"
		self.mouth.key = 'x'
		self.mouth.output_pin1 = [0x20, 7]  # Mouth open
		self.mouth.output_pin2 = [0x23, 2]  # Mouth close
		self.mouth.output_pin1_max_time = 0.75
		self.mouth.midi_note = 56
		self.mouth.b_is_original_movement = True
		self.all.append(self.mouth)

		self.mustache = MovementStruct()
		self.mustache.description = "Mustache"
		self.mustache.key = 'z'
		self.mustache.output_pin1 = [0x20, 2]
		self.mustache.output_pin1_max_time = 60 * 5
		self.mustache.midi_note = 57
		self.mustache.b_is_original_movement = True
		self.all.append(self.mustache)

		self.mouth_and_mustache = MovementStruct()
		self.mouth_and_mustache.description = "Mouth + Mustache"
		self.mouth_and_mustache.key = 'c'
		self.mouth_and_mustache.midi_note = 65
		self.mouth_and_mustache.linked_keys = ['z', 'x']
		self.all.append(self.mouth_and_mustache)

		self.eyes_left = MovementStruct()
		self.eyes_left.description = "Eyes L"
		self.eyes_left.key = 'q'
		self.eyes_left.output_pin1 = [0x21, 4]
		self.eyes_left.output_pin1_max_time = 60 * 10
		self.eyes_left.midi_note = 58
		self.eyes_left.callback_func = self.on_eye_move
		self.eyes_left.mirrored_key = 'e'
		self.eyes_left.b_is_original_movement = True
		self.all.append(self.eyes_left)

		self.eyes_right = MovementStruct()
		self.eyes_right.description = "Eyes R"
		self.eyes_right.key = 'e'
		self.eyes_right.output_pin1 = [0x20, 0]
		self.eyes_right.output_pin1_max_time = 60 * 10
		self.eyes_right.midi_note = 59
		self.eyes_right.callback_func = self.on_eye_move
		self.eyes_right.mirrored_key = 'q'
		self.eyes_right.b_is_original_movement = True
		self.all.append(self.eyes_right)

		self.eyes_blink_full = MovementStruct()
		self.eyes_blink_full.description = "Eyes Blink"
		self.eyes_blink_full.key = 'w'
		self.eyes_blink_full.output_pin1 = [0x21, 5]  # Eyes close
		self.eyes_blink_full.output_pin2 = [0x20, 1]  # Eyes open
		self.eyes_blink_full.output_pin1_max_time = 1
		self.eyes_blink_full.output_pin2_max_time = 1
		self.eyes_blink_full.midi_note = 60
		self.eyes_blink_full.b_is_original_movement = True
		self.all.append(self.eyes_blink_full)

		self.head_left = MovementStruct()
		self.head_left.description = "Head L"
		self.head_left.key = 'a'
		self.head_left.output_pin1 = [0x21, 0]
		self.head_left.output_pin1_max_time = 1
		self.head_left.midi_note = 61
		self.head_left.mirrored_key = 'd'
		self.head_left.b_is_original_movement = True
		self.all.append(self.head_left)

		self.head_right = MovementStruct()
		self.head_right.description = "Head R"
		self.head_right.key = 'd'
		self.head_right.output_pin1 = [0x23, 3]
		self.head_right.output_pin1_max_time = 1
		self.head_right.midi_note = 62
		self.head_right.mirrored_key = 'a'
		self.head_right.b_is_original_movement = True
		self.all.append(self.head_right)

		self.head_nod = MovementStruct()
		self.head_nod.description = "Head Up"
		self.head_nod.key = 's'
		self.head_nod.output_pin1 = [0x20, 3]  # Head down
		self.head_nod.output_pin2 = [0x21, 6]  # Head up
		self.head_nod.midi_note = 63
		self.head_nod.b_enable_on_retro_mode = True
		self.all.append(self.head_nod)

		self.body_lean_back = MovementStruct()
		self.body_lean_back.description = "Lean Back"
		self.body_lean_back.key = 'm'
		self.body_lean_back.output_pin1 = [0x23, 4]  # Lean forward
		self.body_lean_back.output_pin2 = [0x21, 1]  # Lean backwards
		self.body_lean_back.output_inverted = True
		self.body_lean_back.midi_note = 64
		self.all.append(self.body_lean_back)

		self.animation_threads_active: bool = False
		self.blink_animation_thread: Optional[threading.Thread] = None  # Random blinking thread
		self.eye_left_right_animation_thread: Optional[threading.Thread] = None  # Eye left/right animation thread
		self.mustache_animation_thread: Optional[threading.Thread] = None  # Mustache animation thread
		self.neck_animation_thread: Optional[threading.Thread] = None  # Head (neck) animation thread

		for movement in self.all:
			movement.key_is_pressed = False
			val = 0
			try:
				if movement.output_inverted:
					val = 1
			except Exception:
				movement.output_inverted = False

			movement.pin1_time = 0

			if movement.output_pin1:
				self.set_pin(movement.output_pin1, val, movement)
				if movement.output_pin2:
					movement.pin2_time = 0
					self.set_pin(movement.output_pin2, 1 - val, movement)

	def on_eye_move(self, movement: MovementStruct, val: int) -> None:
		if val == 0 and not self.eyes_left.key_is_pressed and not self.eyes_right.key_is_pressed:
			pin = None
			move_time = 0.06
			if movement == self.eyes_left:
				pin = self.eyes_right.output_pin1
			elif movement == self.eyes_right:
				pin = self.eyes_left.output_pin1
				move_time = 0.04
			if pin:
				# Move eyes in the opposite direction briefly to re-center the eyeballs.
				self.set_pin(pin, 1, movement)
				time.sleep(move_time)
				if not self.eyes_right.key_is_pressed and not self.eyes_left.key_is_pressed:
					self.set_pin(pin, 0, movement)

	def on_eye_blink_half(self, movement: MovementStruct, val: int) -> None:
		try:
			blinked = self.eyes_blink_half.bBlinked
		except Exception:
			self.eyes_blink_half.bBlinked = False

		self.set_pin(self.eyes_blink_full.output_pin2, 0, self.eyes_blink_full)
		if val == 1 and not self.eyes_blink_half.bBlinked:
			self.eyes_blink_half.bBlinked = True
			time.sleep(0.020)
			self.set_pin(self.eyes_blink_half.output_pin1, 0, self.eyes_blink_full)
		elif val == 1 and self.eyes_blink_half.bBlinked:
			self.eyes_blink_half.bBlinked = False
			self.set_pin(self.eyes_blink_half.output_pin1, 0, self.eyes_blink_full)
			self.execute_movement(self.eyes_blink_full.key, 0)
			time.sleep(0.025)
			self.set_pin(self.eyes_blink_full.output_pin2, 0, self.eyes_blink_full)

	def set_mirrored(self, b_mirrored: bool) -> None:
		if self.b_mirrored == b_mirrored:
			return
		self.b_mirrored = b_mirrored
		print(f"Setting mirrored mode: {self.b_mirrored}")
		for movement in self.all:
			if movement.mirrored_key:
				mirrored_key = movement.mirrored_key
				movement.mirrored_key = movement.key
				movement.key = mirrored_key

	def get_midi_notes(self) -> str:
		full_string = ""
		for movement in self.all:
			full_string += movement.key
			midi_note_str = str(movement.midi_note)
			if len(midi_note_str) < 2:
				midi_note_str = "0" + midi_note_str
			full_string += midi_note_str + "00" + ","
		return full_string

	def get_all_movement_info(self) -> List[List[Any]]:
		all_movements = []
		for movement in self.all:
			all_movements.append([movement.key, movement.midi_note])
		return all_movements

	def update_pins(self) -> None:
		while True:
			time.sleep(0.1)
			for movement in self.all:
				if movement.output_pin1_max_time > -1 and movement.pin1_time > 0:
					movement.pin1_time -= 0.1
					if movement.pin1_time <= 0:
						movement.pin1_time = 0
						self.set_pin(movement.output_pin1, 0, movement)
				if movement.output_pin2_max_time > -1 and movement.pin2_time > 0:
					movement.pin2_time -= 0.1
					if movement.pin2_time <= 0:
						movement.pin2_time = 0
						self.set_pin(movement.output_pin2, 0, movement)

	def set_pin(self, pin: List[Any], val: int, movement: MovementStruct) -> None:
		self.gpio.set_pin_from_address(pin[0], pin[1], val)

	def execute_movement(self, key: str, val: int, b_mute_midi: bool = False) -> bool:
		b_do_callback = False
		for movement in self.all:
			if movement.key == key and key:
				if val == 1 and not movement.key_is_pressed:
					movement.key_is_pressed = True
					b_do_callback = True
				elif val == 0 and movement.key_is_pressed:
					movement.key_is_pressed = False
					b_do_callback = True
				if b_do_callback:
					if movement.linked_keys:
						for linked_key in movement.linked_keys:
							self.execute_movement(linked_key, val, b_mute_midi)
						return True
					if not b_mute_midi:
						self.midi.send_message(movement.midi_note, val)
					if self.b_retro_mode_active and not movement.b_is_original_movement:
						if movement.b_enable_on_retro_mode:
							self.set_pin(movement.output_pin1, 1, movement)
							self.set_pin(movement.output_pin2, 0, movement)
						return True
					if movement.output_inverted:
						val = 1 - val
					self.set_pin(movement.output_pin1, val, movement)
					movement.pin1_time = movement.output_pin1_max_time if val == 1 else 0
					if movement.output_pin2:
						self.set_pin(movement.output_pin2, 1 - val, movement)
						movement.pin2_time = 0 if val == 1 else movement.output_pin2_max_time
					if movement.callback_func:
						try:
							t = threading.Thread(target=movement.callback_func, args=(movement, val))
							t.setDaemon(True)
							t.start()
						except Exception:
							pass
					break
		if not self.b_thread_started:
			self.b_thread_started = True
			t = threading.Thread(target=self.update_pins, daemon=True)
			t.start()
		return b_do_callback

	def execute_midi_note(self, midi_note: int, val: int) -> None:
		for movement in self.all:
			if movement.midi_note == midi_note:
				self.execute_movement(movement.key, val, True)
				break

	def set_retro_mode(self, b_enable: bool) -> None:
		self.b_retro_mode_active = b_enable
		print(f"Set Retro Mode: {b_enable}")
		for movement in self.all:
			if not movement.b_is_original_movement:
				self.execute_movement(movement.key, 0)

	def stop_all_animation_threads(self) -> None:
		self.animation_threads_active = False
		def anim_shutdown() -> None:
			self.execute_movement(self.head_nod.key, 1)
			self.execute_movement(self.mustache.key, 0)
			self.execute_movement(self.mouth.key, 0)
			if self.blink_animation_thread and self.blink_animation_thread.is_alive():
				self.blink_animation_thread.join()
			if not self.animation_threads_active:
				self.execute_movement(self.eyes_blink_full.key, 0)
				self.execute_movement(self.eyes_left.key, 0)
				self.execute_movement(self.eyes_right.key, 0)
				self.execute_movement(self.head_left.key, 1)
				time.sleep(1)
				self.execute_movement(self.head_left.key, 0)
		threading.Thread(target=anim_shutdown, daemon=True).start()

	def play_wakeword_acknowledgement(self) -> None:
		def mustache_shake() -> None:
			self.execute_movement(self.head_nod.key, 0)
			self.execute_movement(self.mustache.key, 1)
			time.sleep(0.2)
			self.execute_movement(self.mustache.key, 0)
			time.sleep(0.2)
			self.execute_movement(self.mustache.key, 1)
			time.sleep(0.2)
			self.execute_movement(self.mustache.key, 0)
			time.sleep(0.2)
		self.mustache_animation_thread = threading.Thread(target=mustache_shake, daemon=True)
		self.mustache_animation_thread.start()

	def play_blink_animation(self) -> None:
		self.animation_threads_active = True
		max_time_between_blinks = 3  # Seconds
		dispatcher.send(signal="keyEvent", key=self.head_nod.key, val=0)
		def blink() -> None:
			while self.animation_threads_active:
				self.execute_movement(self.eyes_blink_full.key, 1)
				time.sleep(random.uniform(0.05, 0.2))
				self.execute_movement(self.eyes_blink_full.key, 0)
				time.sleep(random.uniform(0.25, max_time_between_blinks))
		self.blink_animation_thread = threading.Thread(target=blink, daemon=True)
		self.blink_animation_thread.start()

	def play_neck_animation(self) -> None:
		self.animation_threads_active = True
		def head_turn() -> None:
			while self.animation_threads_active:
				time.sleep(random.uniform(0.5, 1.5))
				if self.animation_threads_active:
					self.execute_movement(self.head_left.key, 0)
					self.execute_movement(self.head_right.key, 1)
					time.sleep(random.uniform(0.1, 0.4))
				if self.animation_threads_active:
					self.execute_movement(self.head_right.key, 0)
					self.execute_movement(self.head_left.key, 0)
					time.sleep(random.uniform(0.25, 1.5))
				if self.animation_threads_active:
					self.execute_movement(self.head_right.key, 0)
					self.execute_movement(self.head_left.key, 1)
					time.sleep(random.uniform(0.5, 1))
				if self.animation_threads_active:
					self.execute_movement(self.head_right.key, 0)
					self.execute_movement(self.head_left.key, 0)
		self.neck_animation_thread = threading.Thread(target=head_turn, daemon=True)
		self.neck_animation_thread.start()

	def play_eye_left_right_animation(self) -> None:
		if self.eye_left_right_animation_thread and self.eye_left_right_animation_thread.is_alive():
			return
		self.animation_threads_active = True
		def eyes() -> None:
			b_move_left = random.choice([True, False])
			eye_movement = self.eyes_right
			while self.animation_threads_active:
				eye_movement = self.eyes_left if b_move_left else self.eyes_right
				self.execute_movement(self.head_left.key, 1)
				time.sleep(random.uniform(0.1, 0.3))
				self.execute_movement(self.head_left.key, 0)
				self.execute_movement(eye_movement.key, 1)
				if not self.animation_threads_active:
					return
				time.sleep(random.uniform(0, 2.5))
				self.execute_movement(eye_movement.key, 0)
				if not self.animation_threads_active:
					return
				time.sleep(random.uniform(0, 2.5))
				b_move_left = not b_move_left
		self.eye_left_right_animation_thread = threading.Thread(target=eyes, daemon=True)
		self.eye_left_right_animation_thread.start()

	def set_default_animation(self, b_end: bool = False) -> None:
		def default() -> None:
			if b_end:
				time.sleep(0.5)
			self.execute_movement(self.head_nod.key, 0)
			self.execute_movement(self.mouth.key, 0)
			self.execute_movement(self.mustache.key, 0)
			self.execute_movement(self.eyes_left.key, 0)
			self.execute_movement(self.eyes_right.key, 0)
			self.execute_movement(self.eyes_blink_full.key, 0)
			self.execute_movement(self.left_and_right_arms.key, 0)
			self.execute_movement(self.left_and_right_elbows.key, 0)
			self.execute_movement(self.body_lean_back.key, 0)
			if b_end:
				self.execute_movement(self.head_left.key, 1)
				time.sleep(2)
				self.execute_movement(self.head_left.key, 0)
		threading.Thread(target=default, daemon=True).start()
