import os
import mido
import time
import pygame
import random
from pydispatch import dispatcher
import threading
from typing import List, Optional

class ShowPlayer:
	def __init__(self, pygame_instance) -> None:
		self.pygame = pygame_instance
		self.MUSIC_END = self.pygame.USEREVENT + 1
		self.pygame.mixer.music.set_endevent(self.MUSIC_END)

		self.show_list: List[str] = []
		self.active_show_name: Optional[str] = None
		self.paused: bool = False
		self.midi_file_data: List[List[float]] = []  # Each entry: [time_ms, midi_note, on/off state]
		self.midi_states: dict = {}    # Track current state of MIDI notes

		script_dir = os.path.dirname(os.path.abspath(__file__))
		self.show_dir = os.path.join(script_dir, "shows")

		if os.path.exists(self.show_dir):
			self.get_show_list()
			self.update_thread = threading.Thread(target=self.update, daemon=True)
			self.update_thread.start()
		else:
			print(f"'show' directory does not exist at: {self.show_dir}")
			self.show_dir = None

	def update(self) -> None:
		last_checked_time = 0  # Keep track of the last update time
		while True:
			try:
				for event in self.pygame.event.get():
					if event.type == self.MUSIC_END and self.active_show_name is not None:
						dispatcher.send(signal="showEnd")
						self.stop_show()

				if self.pygame.mixer.music.get_busy():  # Check if music is playing
					current_time_ms = self.pygame.mixer.music.get_pos()  # Get playback time in milliseconds

					# Process MIDI data for the current time
					if current_time_ms != last_checked_time:
						self.process_midi_states(current_time_ms)
						last_checked_time = current_time_ms

				time.sleep(0.01)
			except Exception as e:
				print(f"Exception in update thread: {e}")

	def process_midi_states(self, current_time_ms: int) -> None:
		# Iterate over midi_file_data and find events that occur at or before the current time
		for entry in self.midi_file_data:
			event_time, midi_note, state = entry
			# Process events that occur before or at the current time
			if event_time <= current_time_ms:
				# Check if the state of the note has changed
				if self.midi_states.get(midi_note) != state:
					self.midi_states[midi_note] = state  # Update the state
					# Send the event only for the specific note that changed
					dispatcher.send(signal="showPlaybackMidiEvent", midi_note=midi_note, val=state)

		# Remove processed events
		self.midi_file_data = [entry for entry in self.midi_file_data if entry[0] > current_time_ms]

	def load_show(self, show_name: str) -> None:
		if self.show_dir is None:
			return

		if show_name == "":
			show_name = random.choice(self.show_list)

		if self.active_show_name != show_name:
			# Supported file extensions
			supported_extensions = ['.mp3', '.wav', '.ogg']

			# Iterate through supported extensions to find the file
			for ext in supported_extensions:
				file_path = os.path.join(self.show_dir, show_name + ext)
				if os.path.isfile(file_path):
					if self.parse_midi_file(show_name):
						self.active_show_name = show_name
						self.midi_states.clear()  # Reset MIDI states for a new show
						self.pygame.mixer.music.load(file_path)
						self.pygame.mixer.music.play()
						print(f"Playing show: {file_path}")
						return

			raise FileNotFoundError(
				f"No audio file named '{show_name}' found in {self.show_dir} with supported extensions."
			)

		if self.active_show_name is not None and self.paused:
			self.toggle_pause()

	def stop_show(self) -> None:
		if self.active_show_name is not None:
			self.pygame.mixer.music.stop()
			self.paused = False
			self.active_show_name = None

	def toggle_pause(self) -> None:
		if not self.paused:
			self.paused = True
			self.pygame.mixer.music.pause()
		else:
			self.paused = False
			self.pygame.mixer.music.unpause()

	def parse_midi_file(self, show_name: str) -> bool:
		if self.show_dir is None:
			return False

		# Path to the MIDI file
		midi_file_path = os.path.join(self.show_dir, show_name + ".mid")

		# Check if the MIDI file exists
		if not os.path.exists(midi_file_path):
			print(f"Error: MIDI file not found at {midi_file_path}")
			return False

		# Parse the MIDI file
		try:
			midi_file = mido.MidiFile(midi_file_path)
			self.midi_file_data = []

			# Track elapsed time in milliseconds
			current_time_ms = 0

			for message in midi_file:
				current_time_ms += message.time * 1000  # Convert time to milliseconds

				if message.type == 'note_on':
					if message.velocity == 0:
						self.midi_file_data.append([current_time_ms, message.note, 0])  # "Off" event
					else:
						self.midi_file_data.append([current_time_ms, message.note, 1])  # "On" event

			return True

		except Exception as e:
			print(f"Error parsing MIDI file: {e}")
			return False

	def get_show_list(self) -> None:
		if self.show_dir is None:
			return

		# Get all audio files and check for corresponding .mid files
		audio_extensions = ('.mp3', '.wav', '.ogg')
		files_in_directory = os.listdir(self.show_dir)

		self.show_list = []
		for file in files_in_directory:
			if file.lower().endswith(audio_extensions):
				base_name, _ = os.path.splitext(file)
				midi_file = f"{base_name}.mid"
				if midi_file in files_in_directory:
					self.show_list.append(base_name)

		if self.show_list:
			dispatcher.send(signal="showListLoad", show_list=self.show_list)
		else:
			print("No matching audio and .mid files found in the 'show' directory.")
