import os
import subprocess
import pygame
import time
from pydispatch import dispatcher
from wifi_management import WifiManagement
from system_info import SystemInfo
from automated_puppeteering import AutomatedPuppeteering
from typing import Any, List

class VoiceEventHandler:
	def __init__(self, pygame_instance: Any, voice_input_instance: Any) -> None:
		self.pygame = pygame_instance
		self.voice_input_processor = voice_input_instance
		self.puppeteer = AutomatedPuppeteering(pygame_instance)

		self.wifi_management = WifiManagement()
		self.system_info = SystemInfo(False)

		self.audio_path = os.path.join(os.path.dirname(__file__), "miscAudioAssets")

		self.commands = {
			"PlaySong": self.play_song,
			"Encore": self.play_encore,
			"WhoAreYou": self.who_are_you,
			"HowDoYouWork": self.how_do_you_work,
			"IPAddress": self.ip_address,
			"HotspotStart": self.hotspot_start,
			"HotspotEnd": self.hotspot_end,
			"WifiNetwork": self.wifi_network,
			"PSI": self.psi,
			"TryAI": self.ai,
			"LookUpAndDown": self.look_up_and_down
		}

	def trigger_event(self, event_id: str, value: Any) -> None:
		print(f"VoiceEvent: {event_id}, {value}")

		if event_id == "noTranscription":
			self.play_audio_sequence([f"{self.audio_path}/no_transcription.ogg"])
		elif event_id == "error":
			if not self.wifi_management.is_internet_available():
				self.play_audio_sequence([f"{self.audio_path}/no_connection.ogg"])
			else:
				self.play_audio_sequence([f"{self.audio_path}/no_ai.ogg"])
		elif event_id == "command":
			self.handle_command(value)

	def handle_command(self, command: str) -> None:
		action = self.commands.get(command)
		if action:
			action()  # Call the corresponding method
		else:
			print(f"Unknown command: '{command}'")

	def play_audio_sequence(self, audio_files: List[str]) -> None:
		for file in audio_files:
			try:
				self.puppeteer.play_audio_with_puppeting(file)
			except pygame.error as e:
				print(f"Error playing {file}: {e}")

	def play_song(self) -> None:
		self.play_audio_sequence([f"{self.audio_path}/song_start.ogg"])  # Voice audio to announce playing a song.
		dispatcher.send(signal="showPlay", show_name="")  # Empty show name means play something random

	def play_encore(self) -> None:
		self.play_audio_sequence([f"{self.audio_path}/encore.ogg", f"{self.audio_path}/song_start.ogg"])
		dispatcher.send(signal="showPlay", show_name="")  # Empty show name means play something random

	def who_are_you(self) -> None:
		self.play_audio_sequence([f"{self.audio_path}/who_are_you.ogg"])  # Voice audio for a brief introduction.

	def how_do_you_work(self) -> None:
		self.play_audio_sequence([f"{self.audio_path}/how_do_you_work.ogg"])  # Voice audio for a brief introduction.

	def ip_address(self) -> None:
		# Play sequential audio to read out the current IP address.
		ip = self.wifi_management.get_current_ip()
		if ip is None:
			audio_files = [f"{self.audio_path}/no_connection.ogg"]
		else:
			audio_files = [f"{self.audio_path}/ip_prefix.ogg"]  # A voice intro
			for char in ip:
				if char == ".":
					audio_files.append(f"{self.audio_path}/dot.wav")
				else:
					audio_files.append(f"{self.audio_path}/numero_{char}.wav")
		self.play_audio_sequence(audio_files)

	def look_up_and_down(self) -> None:
		dispatcher.send(signal="keyEvent", key='a', val=1)  # Force head/body to turn right
		time.sleep(0.1)
		dispatcher.send(signal="voiceInputEvent", id="ttsComplete", val=None)
		dispatcher.send(signal="keyEvent", key='s', val=1)
		time.sleep(0.75)
		dispatcher.send(signal="keyEvent", key='s', val=0)
		time.sleep(0.75)
		dispatcher.send(signal="keyEvent", key='s', val=1)
		time.sleep(0.75)
		dispatcher.send(signal="keyEvent", key='s', val=0)
		time.sleep(0.75)
		dispatcher.send(signal="keyEvent", key='s', val=1)
		time.sleep(0.75)
		dispatcher.send(signal="keyEvent", key='s', val=0)

	def ai(self) -> None:
		self.play_audio_sequence([f"{self.audio_path}/ai.ogg"])

	def hotspot_start(self) -> None:
		self.play_audio_sequence([f"{self.audio_path}/hotspot_activate.ogg"])
		dispatcher.send(signal="activateWifiHotspot", bActivate=True)

	def hotspot_end(self) -> None:
		self.play_audio_sequence([f"{self.audio_path}/hotspot_deactivate.ogg"])
		dispatcher.send(signal="activateWifiHotspot", bActivate=False)

	def wifi_network(self) -> None:
		ssid = self.wifi_management.get_current_ssid()
		if ssid is None:
			self.play_audio_sequence([f"{self.audio_path}/no_connection.ogg"])
		else:
			print(1)
			self.play_audio_sequence([f"{self.audio_path}/ssid.ogg"])
			print(2)
			self.voice_input_processor.generate_and_play_tts(ssid)

	def psi(self) -> None:
		# This function should read off the current PSI by creating a list of WAV audio files.
		# Start with the prefix audio.
		audio_files = [f"{self.audio_path}/psi_prefix.ogg"]

		# Get the current PSI value from the system.
		psi_value = self.system_info.get_psi()

		# Select the correct numero files based on psi_value.
		if psi_value <= 20:
			# For PSI 0 through 20, use the corresponding file.
			audio_files.append(f"{self.audio_path}/numero_{psi_value}.wav")
		else:
			# For PSI values above 20:
			# Special-case 100 if it exists.
			if psi_value == 100:
				audio_files.append(f"{self.audio_path}/numero_100.wav")
			else:
				# Determine tens and ones digits.
				tens = psi_value - (psi_value % 10)
				ones = psi_value % 10

				if ones == 0:
					# If the ones digit is zero, just use the corresponding tens file.
					audio_files.append(f"{self.audio_path}/numero_{psi_value}.wav")
				else:
					# Otherwise, append the tens file first and then the ones file.
					audio_files.append(f"{self.audio_path}/numero_{tens}.wav")
					audio_files.append(f"{self.audio_path}/numero_{ones}.wav")

		# Append the postfix audio file.
		audio_files.append(f"{self.audio_path}/psi_postfix.wav")

		# Play the complete audio sequence.
		self.play_audio_sequence(audio_files)
