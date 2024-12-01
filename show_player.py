import os
import mido
import time
import pygame
import eventlet
from pydispatch import dispatcher

class ShowPlayer:
	def __init__(self):
		pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
		pygame.display.init()
		pygame.display.set_mode((1, 1))
		
		self.MUSIC_END = pygame.USEREVENT + 1
		pygame.mixer.music.set_endevent(self.MUSIC_END)

		self.show_list = []
		self.active_showName = None
		self.bPaused = False
		self.midi_data = [] # MSec timecode, midi note, on/off state

		script_dir = os.path.dirname(os.path.abspath(__file__))
		# Define the 'show' directory relative to the script
		self.show_dir = os.path.join(script_dir, "shows")

		# Check if the 'show' directory exists
		if os.path.exists(self.show_dir):
			self.getShowList()
			self.update_thread = eventlet.spawn(self.update)
		else:
			print(f"'show' directory does not exist at: {self.show_dir}")
			self.show_dir = None

	def update(self):
		while True:
			try:
				for event in pygame.event.get():
					if event.type == self.MUSIC_END and self.active_showName is not None:
						print("Show has completed!")
						self.stopShow()

				if pygame.mixer.music.get_busy():  # Check if music is playing
					current_time_ms = pygame.mixer.music.get_pos()  # Get playback time in milliseconds
					print(f"Music is playing. Current time: {current_time_ms} ms")

				eventlet.sleep(0.01)
			except Exception as e:
				print(f"Exception in update thread: {e}")

	def loadShow(self, showName):
		if self.show_dir is None:
			return

		if self.active_showName != showName:
			# Supported file extensions
			supported_extensions = ['.mp3', '.wav', '.ogg']
			
			# Iterate through supported extensions to find the file
			for ext in supported_extensions:
				file_path = os.path.join(self.show_dir, showName + ext)
				if os.path.isfile(file_path):
					if( self.parseMidiFile(showName)):
						self.active_showName = showName
						pygame.mixer.music.load(file_path)
						pygame.mixer.music.play()
						print(f"Playing show: {file_path}")
						return
					
			# If no file is found, raise an error
			raise FileNotFoundError(f"No audio file named '{showName}' found in {self.show_dir} with supported extensions.")

		if self.active_showName is not None and self.bPaused:
			self.togglePause()

	def stopShow(self):
		if self.active_showName is not None:
			pygame.mixer.music.stop()
			self.bPaused = False
			self.active_showName = None
			print("Stopped")

	def togglePause(self):
		if not self.bPaused:
			self.bPaused = True
			print("Paused")
			pygame.mixer.music.pause()
		else:
			self.bPaused = False
			print("Unpaused")
			pygame.mixer.music.unpause()

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
			self.midi_data = []

			# Track elapsed time in milliseconds
			current_time_ms = 0

			for message in midi_file:
				current_time_ms += message.time * 1000  # Convert time to milliseconds

				if message.type == 'note_on':
					if message.velocity == 0:
						self.midi_data.append([current_time_ms, message.note, 0])  # Animation "off" event
					else:
						self.midi_data.append([current_time_ms, message.note, 1])  # Animation "off" event
			
			
			#print("Parsed MIDI data:")
			#for row in self.midi_data:
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
		
		self.show_list = []
		for file in files_in_directory:
			if file.lower().endswith(audio_extensions):
				base_name, _ = os.path.splitext(file)
				midi_file = f"{base_name}.mid"
				if midi_file in files_in_directory:
					self.show_list.append(base_name)

		if self.show_list:
			dispatcher.send(signal="showListLoad", showList = self.show_list)
		else:
			print("No matching audio and .mid files found in the 'show' directory.")
