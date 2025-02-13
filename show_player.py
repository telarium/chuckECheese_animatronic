import os
import mido
import time
import pygame
import eventlet
import random
from pydispatch import dispatcher

class ShowPlayer:
	def __init__(self, pygame_instance):
		
		self.pygame = pygame_instance
		self.MUSIC_END = self.pygame.USEREVENT + 1
		self.pygame.mixer.music.set_endevent(self.MUSIC_END)

		self.showList = []
		self.active_showName = None
		self.bPaused = False
		self.midiFileData = []  # MSec timecode, midi note, on/off state
		self.midiStates = {}  # Track current state of MIDI notes
		
		script_dir = os.path.dirname(os.path.abspath(__file__))
		self.show_dir = os.path.join(script_dir, "shows")

		if os.path.exists(self.show_dir):
			self.getShowList()
			self.update_thread = eventlet.spawn(self.update)
		else:
			print(f"'show' directory does not exist at: {self.show_dir}")
			self.show_dir = None

	def update(self):
		last_checked_time = 0  # Keep track of the last update time
		while True:
			try:
				for event in self.pygame.event.get():
					if event.type == self.MUSIC_END and self.active_showName is not None:
						dispatcher.send(signal="showEnd")
						self.stopShow()

				if self.pygame.mixer.music.get_busy():  # Check if music is playing
					current_time_ms = self.pygame.mixer.music.get_pos()  # Get playback time in milliseconds

					# Process MIDI data for the current time
					if current_time_ms != last_checked_time:
						self.processMidiStates(current_time_ms)
						last_checked_time = current_time_ms

				eventlet.sleep(0.01)
			except Exception as e:
				print(f"Exception in update thread: {e}")

	def processMidiStates(self, current_time_ms):
		# Iterate over midiFileData and find events that occur at or before the current time
		for entry in self.midiFileData:
			event_time, midi_note, state = entry

			# Process events that occur before or at the current time
			if event_time <= current_time_ms:
				# Check if the state of the note has changed
				if self.midiStates.get(midi_note) != state:
					self.midiStates[midi_note] = state  # Update the state
					# Send the event only for the specific note that changed
					dispatcher.send(signal="showPlaybackMidiEvent", midiNote=midi_note, value=state)
				
		# Remove processed events
		self.midiFileData = [entry for entry in self.midiFileData if entry[0] > current_time_ms]


	def loadShow(self, showName):
		if self.show_dir is None:
			return

		if showName == "":
			showName = random.choice(self.showList)

		if self.active_showName != showName:
			# Supported file extensions
			supported_extensions = ['.mp3', '.wav', '.ogg']
			
			# Iterate through supported extensions to find the file
			for ext in supported_extensions:
				file_path = os.path.join(self.show_dir, showName + ext)
				if os.path.isfile(file_path):
					if self.parseMidiFile(showName):
						self.active_showName = showName
						self.midiStates.clear()  # Reset MIDI states for a new show
						self.pygame.mixer.music.load(file_path)
						self.pygame.mixer.music.play()
						print(f"Playing show: {file_path}")
						return
					
			raise FileNotFoundError(f"No audio file named '{showName}' found in {self.show_dir} with supported extensions.")

		if self.active_showName is not None and self.bPaused:
			self.togglePause()

	def stopShow(self):
		if self.active_showName is not None:
			self.pygame.mixer.music.stop()
			self.bPaused = False
			self.active_showName = None

	def togglePause(self):
		if not self.bPaused:
			self.bPaused = True
			self.pygame.mixer.music.pause()
		else:
			self.bPaused = False
			self.pygame.mixer.music.unpause()

	def parseMidiFile(self, showName):
		if self.show_dir is None:
			return False
		
		# Path to the MIDI file
		midi_file_path = os.path.join(self.show_dir, showName + ".mid")
		
		# Check if the MIDI file exists
		if not os.path.exists(midi_file_path):
			print(f"Error: MIDI file not found at {midi_file_path}")
			return False
		
		# Parse the MIDI file
		try:
			midi_file = mido.MidiFile(midi_file_path)
			self.midiFileData = []

			# Track elapsed time in milliseconds
			current_time_ms = 0

			for message in midi_file:
				current_time_ms += message.time * 1000  # Convert time to milliseconds

				if message.type == 'note_on':
					if message.velocity == 0:
						self.midiFileData.append([current_time_ms, message.note, 0])  # Animation "off" event
					else:
						self.midiFileData.append([current_time_ms, message.note, 1])  # Animation "off" event
			
			
			#print("Parsed MIDI data:")
			#for row in self.midiFileData:
			#	print(row)

			return True

		except Exception as e:
			print(f"Error parsing MIDI file: {e}")

	def getShowList(self):
		if self.show_dir is None:
			return

		# Get all audio files and check for corresponding .mid files
		audio_extensions = ('.mp3', '.wav', '.ogg')
		files_in_directory = os.listdir(self.show_dir)
		
		self.showList = []
		for file in files_in_directory:
			if file.lower().endswith(audio_extensions):
				base_name, _ = os.path.splitext(file)
				midi_file = f"{base_name}.mid"
				if midi_file in files_in_directory:
					self.showList.append(base_name)

		if self.showList:
			dispatcher.send(signal="showListLoad", showList = self.showList)
		else:
			print("No matching audio and .mid files found in the 'show' directory.")
