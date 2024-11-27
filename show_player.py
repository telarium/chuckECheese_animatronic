import os
import mido
from pydispatch import dispatcher

class ShowPlayer:
	def __init__(self):
		self.show_list = []
		self.midi_data = [] # MSec timecode, midi note, on/off state

		# Get the directory path of this script
		script_dir = os.path.dirname(os.path.abspath(__file__))
		# Define the 'show' directory relative to the script
		self.show_dir = os.path.join(script_dir, "shows")

		# Check if the 'show' directory exists
		if os.path.exists(self.show_dir):
			self.getShowList()
			self.parseMidiFile()
		else:
			print(f"'show' directory does not exist at: {self.show_dir}")
			self.show_dir = None

	def parseMidiFile(self):
		if self.show_dir is None:
			return
		
		# Path to the MIDI file
		midi_file_path = os.path.join(self.show_dir, "row.mid")
		
		# Check if the MIDI file exists
		if not os.path.exists(midi_file_path):
			print(f"Error: MIDI file not found at {midi_file_path}")
			return
		
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
			
			print("Parsed MIDI data:")
			for row in self.midi_data:
				print(row)

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
