import os
import subprocess
import pygame
import time
from pydispatch import dispatcher
from wifi_management import WifiManagement
from system_info import SystemInfo
from automated_puppeteering import AutomatedPuppeteering

class VoiceEventHandler:
	def __init__(self, pygame_instance, voice_input_instance):
		self.pygame = pygame_instance
		self.voiceInputProcessor = voice_input_instance
		self.puppeteer = AutomatedPuppeteering(pygame_instance)

		self.wifiManagement = WifiManagement()
		self.systemInfo = SystemInfo(False)

		self.audioPath = os.path.join(os.path.dirname(__file__), "miscAudioAssets")

		self.commands = {
			"PlaySong": self.playSong,
			"Encore": self.playEncore,
			"WhoAreYou": self.whoAreYou,
			"HowDoYouWork": self.howDoYouWork,
			"IPAddress": self.ipAddress,
			"HotspotStart": self.hotspotStart,
			"HotspotEnd": self.hotspotEnd,
			"WifiNetwork": self.wifiNetwork,
			"PSI": self.psi,
			"TryAI": self.ai,
			"LookUpAndDown": self.lookUpAndDown
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

	def playEncore(self):
		self.playAudioSequence([self.audioPath+"/encore.ogg",self.audioPath+"/song_start.ogg"]) # Voice audio to announce playing a song.
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

	def lookUpAndDown(self):
		print("LOOK UP AND DOWN!")
		dispatcher.send(signal="keyEvent", key='s', val=0)
		time.sleep(0.75)
		dispatcher.send(signal="keyEvent", key='s', val=1)
		time.sleep(0.75)
		dispatcher.send(signal="keyEvent", key='s', val=0)
		time.sleep(0.75)
		dispatcher.send(signal="keyEvent", key='s', val=1)

	def ai(self):
		self.playAudioSequence([self.audioPath+"/ai.ogg"])

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
		# This function should read off the current PSI by creating a list of WAV audio files.
		
		# Start with the prefix audio
		audioFiles = [self.audioPath + "/psi_prefix.ogg"]

		# Get the current PSI value from the system.
		psiValue = self.systemInfo.get_psi()

		# Select the correct numero files based on psiValue.
		if psiValue <= 20:
			# For PSI 0 through 20, use the corresponding file.
			audioFiles.append(self.audioPath + f"/numero_{psiValue}.wav")
		else:
			# For PSI values above 20:
			# Special-case 100 if it exists.
			if psiValue == 100:
				audioFiles.append(self.audioPath + "/numero_100.wav")
			else:
				# Determine tens and ones digits.
				tens = psiValue - (psiValue % 10)
				ones = psiValue % 10

				if ones == 0:
					# If the ones digit is zero, just use the corresponding tens file.
					audioFiles.append(self.audioPath + f"/numero_{psiValue}.wav")
				else:
					# Otherwise, append the tens file first and then the ones file.
					audioFiles.append(self.audioPath + f"/numero_{tens}.wav")
					audioFiles.append(self.audioPath + f"/numero_{ones}.wav")

		# Append the postfix audio file.
		audioFiles.append(self.audioPath + "/psi_postfix.wav")

		# Play the complete audio sequence.
		self.playAudioSequence(audioFiles)