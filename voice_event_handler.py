import os
import subprocess
import pygame
from pydispatch import dispatcher
from wifi_management import WifiManagement
from automated_puppeteering import AutomatedPuppeteering

class VoiceEventHandler:
	def __init__(self, pygame_instance):
		self.pygame = pygame_instance
		self.puppeteer = AutomatedPuppeteering(pygame_instance)

		self.wifiManagement = WifiManagement()

		self.audioPath = os.path.join(os.path.dirname(__file__), "miscAudioAssets")

		self.commands = {
			"PlaySong": self.playSong,
			"WhoAreYou": self.whoAreYou,
			"IPAddress": self.ipAddress,
			"HotspotStart": self.hotspotStart,
			"HotspotEnd": self.hotspotEnd,
			"WifiNetwork": self.wifiNetwork,
			"PSI": self.psi
		}

	def triggerEvent(self, id, value):
		print(f"VoiceEvent: {id}, {value}")

		if id == "noTranscription":
			self.playAudioSequence([self.audioPath+"/no_transcription.ogg"])
		elif id == "error":
			if not self.wifiManagement.is_internet_available():
				self.playAudioSequence([self.audioPath+"/no_connection.ogg"])
			else:
				self.playAudioSequence([self.audioPath+"/no_ai.ogg"])
		elif id == "command":
			self.handleCommand(value)

	def handleCommand(self, command):
		action = self.commands.get(command)
		if action:
			action()  # Call the corresponding method
		else:
			print(f"Unknown command: '{command}'")

	def playAudioSequence(self, audio_files):
		for file in audio_files:
			try:
				self.puppeteer.play_audio_with_puppeting(file)
			except self.pygame.error as e:
				print(f"Error playing {file}: {e}")

	def playSong(self):
		self.playAudioSequence([self.audioPath+"/song_start.ogg"]) # Voice audio to announce playing a song.

	def whoAreYou(self):
		self.playAudioSequence([self.audioPath+"/who_are_you.ogg"]) # Voice audio for a brief introduction.

	def ipAddress(self):
		# Play sequential audio to read out the current IP address.
		ip = self.wifiManagement.get_current_ip()
		if ip is None:
			audioFiles = [self.audioPath+"/no_connection.ogg"]
		else:
			audioFiles = [self.audioPath+"/ip_prefix.ogg"] # A voice intro
			for char in ip:
				if char == ".":
					audioFiles.append(self.audioPath+"/dot.wav")
				else:
					audioFiles.append(self.audioPath+"/numero_" + char + ".wav")

		self.playAudioSequence(audioFiles)

	def hotspotStart(self):
		dispatcher.send(signal="activateWifiHotspot", bActivate=True)
		self.playAudioSequence([self.audioPath+"/hotspot_activate.ogg"])

	def hotspotEnd(self):
		dispatcher.send(signal="activateWifiHotspot", bActivate=False)
		self.playAudioSequence([self.audioPath+"/hotspot_deactivate.ogg"])

	def wifiNetwork(self):
		ssid = self.wifiManagement.get_current_ssid()
		print(ssid)
		if ssid is None:
			self.playAudioSequence([self.audioPath+"/no_connection.ogg"])
		else:
			output_path = "/tmp/output.wav"

			# Use pico2wave to generate the speech
			subprocess.run(['pico2wave', '--lang=en-US', '--wave=' + output_path, ssid], check=True)
			self.playAudioSequence([self.audioPath+"/ssid.ogg",output_path])

	def psi(self):
		self.playAudioSequence([self.audioPath+"/psi_prefix.ogg", self.audioPath+"/psi_postfix.ogg"])