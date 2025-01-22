import os
import subprocess
import pygame
from pydispatch import dispatcher
from wifi_management import WifiManagement
from automated_puppeteering import AutomatedPuppeteering

class VoiceEventHandler:
	def __init__(self, pygame_instance, voice_input_instance):
		self.pygame = pygame_instance
		self.voiceInputProcessor = voice_input_instance
		self.puppeteer = AutomatedPuppeteering(pygame_instance)

		self.wifiManagement = WifiManagement()

		self.audioPath = os.path.join(os.path.dirname(__file__), "miscAudioAssets")

		self.commands = {
			"PlaySong": self.playSong,
			"WhoAreYou": self.whoAreYou,
			"HowDoYouWork": self.howDoYouWork,
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
		dispatcher.send(signal="showPlay", showName="") # Empty show name means play something random

	def whoAreYou(self):
		self.playAudioSequence([self.audioPath+"/who_are_you.ogg"]) # Voice audio for a brief introduction.

	def howDoYouWork(self):
		self.playAudioSequence([self.audioPath+"/how_do_you_work.ogg"]) # Voice audio for a brief introduction.

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
		self.playAudioSequence([self.audioPath+"/hotspot_activate.ogg"])
		dispatcher.send(signal="activateWifiHotspot", bActivate=True)

	def hotspotEnd(self):
		self.playAudioSequence([self.audioPath+"/hotspot_deactivate.ogg"])
		dispatcher.send(signal="activateWifiHotspot", bActivate=False)

	def wifiNetwork(self):
		ssid = self.wifiManagement.get_current_ssid()
		if ssid is None:
			self.playAudioSequence([self.audioPath+"/no_connection.ogg"])
		else:
			print(1)
			self.playAudioSequence([self.audioPath+"/ssid.ogg"])
			print(2)
			self.voiceInputProcessor.generate_and_play_tts(ssid)

	def psi(self):
		self.playAudioSequence([self.audioPath+"/psi_prefix.ogg", self.audioPath+"/psi_postfix.ogg"])