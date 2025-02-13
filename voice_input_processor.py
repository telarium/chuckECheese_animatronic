from collections import deque
from google.cloud import speech
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings
from pydispatch import dispatcher
from automated_puppeteering import AutomatedPuppeteering
import pygame
import openai
import pvporcupine
import pvrhino
import struct
import subprocess
import configparser
import os
import wave
import tempfile
import signal
import threading
import time
import requests

class VoiceInputProcessor:
	def __init__(self, pygame_instance, config_file="config.cfg"):
		self.pygame = pygame_instance
		self.puppeteer = AutomatedPuppeteering(pygame_instance)
		self.config = self.load_config(config_file)

		# PicoVoice and Google Speech-to-Text keys
		self.pv_access_key = self.config["PicoVoice"]["AccessKey"]
		self.wakeword_path = self.config["PicoVoice"]["WakewordPath"]
		self.rhino_context_path = self.config["PicoVoice"]["RhinoContextPath"]
		self.google_cloud_key_path = self.config["SpeechToText"]["GoogleCloudKeyPath"]
		os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.google_cloud_key_path

		# OpenAI ChatGPT key
		try:
			self.openai_api_key = self.config["ChatGPT"]["OpenAIKey"]
			openai.api_key = self.openai_api_key
			self.openai_client = openai.Client(api_key=self.openai_api_key)
		except:
			self.openai_api_key = None

		try:
			# DeepSeek API key and model
			self.deepseek_api_key = self.config["DeepSeek"]["DeepSeekAPIKey"]
			self.deepseek_model = self.config["DeepSeek"]["DeepSeekModel"]
		except:
			self.deepseek_api_key = None

		self.ai_context = self.config["AI"]["Context"]

		# ElevenLabs TTS keys
		self.elevenlabs_key = self.config["TextToSpeech"]["ElevenLabsKey"]
		self.elevenlabs_voice_id = self.config["TextToSpeech"]["ElevenLabsVoiceID"]

		self.sample_rate = 16000

		self.porcupine = None

		try:
			self.porcupine = pvporcupine.create(
				access_key=self.pv_access_key,
				keyword_paths=[self.wakeword_path],
			)
		except:
			print("Porcupine wakeword path not set correctly in config.cfg. Voice control disabled.")
			return

		self.rhino = None

		try:
			self.rhino = pvrhino.create(
				access_key=self.pv_access_key,
				context_path=self.rhino_context_path,
			)
		except:
			print("Rhino access key or path not set in config.cfg")

		self.pre_wakeword_buffer = deque(maxlen=10)  # Store ~1 second of pre-wakeword audio
		self.frame_length = self.porcupine.frame_length
		self.frame_size = self.frame_length * 2
		self.speech_client = None

		try:
			self.speech_client = speech.SpeechClient()
		except:
			print("Problem with GoogleCloudKeyPath in config.cfg")

		# Create a temporary directory
		self.temp_dir = tempfile.TemporaryDirectory()

		# Register signal handlers for graceful shutdown
		signal.signal(signal.SIGTERM, self.shutdown)
		signal.signal(signal.SIGINT, self.shutdown)

		self.running = True  # Control flag for the main thread

		# Start the assistant in its own thread
		self.thread = threading.Thread(target=self.run_thread, daemon=True)
		self.thread.start()

	def load_config(self, config_file):
		config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)
		if not os.path.exists(config_path):
			raise FileNotFoundError(f"Configuration file not found: {config_path}")
		config = configparser.ConfigParser()
		config.read(config_path)
		return config

	def setVoiceCommand(self, id, value=None):
		self.voiceStatus = {
			'id': id,
			'value': value,
		}
		dispatcher.send(signal="voiceInputEvent", id=id, value=value)

	def getLastVoiceCommand(self):
		return self.voiceStatus

	def record_audio_stream(self):
		"""Start an audio recording stream."""
		command = [
			"arecord",
			"-D", "plughw:CARD=Device,DEV=0",
			"-f", "S16_LE",
			"-r", str(self.sample_rate),
			"-c", "1",
			"--buffer-size=1920"
		]
		try:
			with open(os.devnull, 'w') as devnull:
				self.process = subprocess.Popen(
					command,
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE
				)
				return self.process
		except Exception as e:
			print(f"Error starting audio stream: {e}")
			return None


	def process_audio_stream(self, process):
		"""Process audio for wakeword detection and transition seamlessly to intent capture."""
		wakeword_detected = False
		intent_audio = bytearray()
		silent_frames = 0
		timeout_time = 5 # The initial default time (in seconds) inbetween the wakeword and when speaking starts

		while True:
			chunk = process.stdout.read(self.frame_size)
			if len(chunk) < self.frame_size:
				break

			self.pre_wakeword_buffer.append(chunk)
			audio_frame = struct.unpack_from(f"{self.frame_length}h", chunk)

			if not wakeword_detected and self.porcupine.process(audio_frame) >= 0:
				print("Wakeword detected!")
				self.setVoiceCommand("wakeWord")
				timeout_time = 5
				wakeword_detected = True
				intent_audio.extend(b"".join(self.pre_wakeword_buffer))
				self.pre_wakeword_buffer.clear()

			if wakeword_detected:
				intent_audio.extend(chunk)
				max_silent_frames = int(self.sample_rate * timeout_time / self.frame_length)  # 1.5 seconds of silence

				# Check for silence
				rms = sum(x * x for x in audio_frame) / len(audio_frame)  # Root Mean Square
				if rms < 500000:  # Silence threshold (adjustable)
					silent_frames += 1
				else:
					timeout_time = 1.5
					silent_frames = 0

				if silent_frames > max_silent_frames:
					print("User stopped speaking.")
					process.terminate()
					process.wait()
					return intent_audio

				# Stop after 10 seconds of audio regardless
				if len(intent_audio) >= self.sample_rate * 10 * 2:
					print(f"Maximum recording duration reached. Silence frames: {silent_frames}")
					process.terminate()
					process.wait()
					return intent_audio

	def save_audio_to_file(self, audio_data, filename):
		"""Save audio data to a WAV file in the temporary directory."""
		filepath = os.path.join(self.temp_dir.name, filename)
		with wave.open(filepath, "wb") as wf:
			wf.setnchannels(1)
			wf.setsampwidth(2)
			wf.setframerate(self.sample_rate)
			wf.writeframes(audio_data)

		return filepath

	def transcribe_audio(self, audio_data):
		"""Send audio to Google Speech-to-Text."""
		if isinstance(audio_data, bytearray):
			audio_data = bytes(audio_data)

		audio = speech.RecognitionAudio(content=audio_data)
		config = speech.RecognitionConfig(
			encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
			sample_rate_hertz=self.sample_rate,
			language_code="en-US",
		)
		try:
			print("Sending audio to Google Speech-to-Text...")
			response = self.speech_client.recognize(config=config, audio=audio)
			if response.results:
				transcript = response.results[0].alternatives[0].transcript
				return transcript
			else:
				self.setVoiceCommand("noTranscription")
				print("No transcription result from Google.")
				return None
		except Exception as e:
			print(f"Error during transcription: {e}")
			self.setVoiceCommand("error")
			return None

	def send_to_chatgpt(self, text):
		"""Send text to ChatGPT and generate a response."""
		print(f"Sending text to ChatGPT: {text}")
		self.setVoiceCommand("chatGPTSend", text)
		try:
			response = self.openai_client.chat.completions.create(
				model="gpt-4",
				messages=[
					{"role": "system", "content": self.ai_context},
					{"role": "user", "content": text},
				],
			)
			chat_response = response.choices[0].message.content
			self.setVoiceCommand("chatGPTReceive", chat_response)
			print(f"ChatGPT Response: {chat_response}")

			# Generate and play TTS audio
			self.generate_and_play_tts(chat_response)

			return chat_response
		except Exception as e:
			self.setVoiceCommand("error")
			print(f"Failed to get response from ChatGPT: {e}")
			return None

	def send_to_deepseek(self, text):
		"""Send text to DeepSeek and generate a response."""
		print(f"Sending text to DeepSeek: {text}")
		self.setVoiceCommand("deepseekSend", text)
		try:
			headers = {
				"Authorization": f"Bearer {self.deepseek_api_key}",
				"Content-Type": "application/json",
			}
			data = {
				"model": self.deepseek_model,
				"messages": [
					{"role": "system", "content": self.ai_context},
					{"role": "user", "content": text},
				],
			}
			
			response = requests.post(
				"https://api.deepseek.com/v1/chat/completions",
				headers=headers,
				json=data,
			)
			response.raise_for_status()

			deepseek_response = response.json()["choices"][0]["message"]["content"]
			self.setVoiceCommand("deepseekReceive", deepseek_response)
			print(f"DeepSeek Response: {deepseek_response}")

			# Generate and play TTS audio
			self.generate_and_play_tts(deepseek_response)

			return deepseek_response
		except Exception as e:
			self.setVoiceCommand("error")
			print(f"Failed to get response from DeepSeek: {e}")
			return None

	def generate_and_play_tts(self, text):
		self.setVoiceCommand("ttsSubmitted")
		"""Generate audio using ElevenLabs TTS API and play directly as MP3."""
		try:
			client = ElevenLabs(api_key=self.elevenlabs_key)

			stability = 0.7
			similarity_boost = 0.8
			style_exaggeration = 0.5

			# Generate the audio (stream=True to receive a generator)
			audio_generator = client.generate(
				text=text,
				stream=True,  # Stream the audio as a generator
				model="eleven_multilingual_v2",
				voice=Voice(
					voice_id=self.elevenlabs_voice_id,
					settings=VoiceSettings(
						stability=stability,
						similarity_boost=similarity_boost,
						style=style_exaggeration,
						use_speaker_boost=True
					)
				)
			)

			# Collect the audio chunks into a byte array
			audio_data = b''.join(audio_generator)

			# Save the audio as an MP3 file in the temporary directory
			temp_audio_file = os.path.join(self.temp_dir.name, "tts_audio.mp3")
			with open(temp_audio_file, "wb") as f:
				f.write(audio_data)

			# Use the AutomatedPuppeteering class to play the MP3 with puppeting
			self.puppeteer.play_audio_with_puppeting(temp_audio_file)
			self.setVoiceCommand("ttsComplete")

		except Exception as e:
			print(f"Elevenlabs not functional. Using Piper instead for tts.")
			print(e)
			# Get the directory of the current Python script
			script_dir = os.path.dirname(os.path.realpath(__file__))

			# Paths to Piper model and config files in the same directory as the script
			piper_model = os.path.join(script_dir, "en_US-ryan-low.onnx")
			piper_config = os.path.join(script_dir, "en_US-ryan-low.json")

			# Temporary audio file for TTS output
			temp_audio_file = os.path.join(self.temp_dir.name, "tts_audio.wav")

			# Run Piper TTS using the pip-installed command
			subprocess.run([
				"piper",
				"-m", piper_model,
				"-c", piper_config,
				"-f", temp_audio_file
			], input=text, text=True, check=True)

			# Play the generated audio
			self.puppeteer.play_audio_with_puppeting(temp_audio_file)

	def shutdown(self, *args):
		"""Clean up resources and terminate gracefully."""
		self.running = False  # Stop the thread's loop

		try:
			# Stop the arecord subprocess if it's running
			if hasattr(self, 'process') and self.process is not None:
				self.process.terminate()
				for _ in range(50):  # Wait up to 5 seconds for termination
					if self.process.poll() is not None:
						break
					time.sleep(0.1)  # Non-blocking wait
				else:
					self.process.kill()
				self.process = None

			# Clean up PicoVoice resources
			self.porcupine.delete()
			self.rhino.delete()

			# Clean up temporary directory
			self.temp_dir.cleanup()
		except:
			pass

	def run_thread(self):
		"""Run the assistant's main loop in a separate thread."""
		while self.running:
			try:
				self.run()
			except Exception as e:
				print(f"Error in VoiceAssistant loop: {e}")

	def run(self):
		"""Main loop to handle wakeword detection and audio processing."""
		# Check if a microphone is available
		mic_check_command = ["arecord", "-l"]
		try:
			result = subprocess.run(mic_check_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
			if "card" not in result.stdout.lower():
				print("No microphone detected. Exiting voice assistant.")
				self.setVoiceCommand("micNotFound")
				self.running = False
				return
		except Exception as e:
			print(f"Error checking microphone: {e}")
			self.setVoiceCommand("micNotFound")
			self.running = False
			return

		self.setVoiceCommand("idle")
		print("Waiting for 'Hey chef' wakeword...")
		stream_process = self.record_audio_stream()
		if not stream_process:
			print("Failed to start audio stream.")
			return

		intent_audio = self.process_audio_stream(stream_process)

		if intent_audio is None:
			return

		# Trim a small portion (e.g., 100ms) from the start of the intent audio
		trim_frames = int(self.sample_rate * 0.1 * 2)  # 100 ms worth of frames
		if len(intent_audio) > trim_frames:
			intent_audio = intent_audio[trim_frames:]

		filepath = self.save_audio_to_file(intent_audio, "speech_trimmed.wav")

		if self.rhino is not None:
			# Send intent audio to Rhino
			frame_length = self.rhino.frame_length
			frame_size = frame_length * 2

			for i in range(0, len(intent_audio), frame_size):
				frame = intent_audio[i:i + frame_size]
				if len(frame) == frame_size:
					audio_frame = struct.unpack_from(f"{frame_length}h", frame)
					if self.rhino.process(audio_frame):
						inference = self.rhino.get_inference()
						if inference.is_understood:
							print(f"Intent detected: {inference.intent}")
							print(f"Slots: {inference.slots}")
							self.setVoiceCommand("command", inference.intent)
							return

		print("No intent detected. Transcribing audio...")
		self.setVoiceCommand("transcribing")
		transcription = self.transcribe_audio(intent_audio)
		if transcription:
			# Rhino is supposed to catch these keywords, but just in case it doesn't, try to catch them here...
			if "your ip address" in transcription.lower():
				self.setVoiceCommand("command", "IPAddress")
			elif "your Wi-Fi network" in transcription.lower():
				self.setVoiceCommand("command", "WifiNetwork")
			elif "activate hotspot" in transcription.lower():
				self.setVoiceCommand("command", "HotspotStart")
			elif "deactivate hotspot" in transcription.lower():
				self.setVoiceCommand("command", "HotspotEnd")
			elif transcription.lower() == "stop" or transcription.lower() == "stop singing" or transcription.lower() == "stop show":
				dispatcher.send(signal="showStop")
			else:
				# If no command found, send to OpenAI or DeepSeek, depending on if either have been configured.
				if self.openai_api_key and "your" not in self.openai_api_key:
					self.send_to_chatgpt(transcription)
				elif self.deepseek_api_key and "your" not in self.deepseek_api_key:
					self.send_to_deepseek(transcription)
		else:
			self.setVoiceCommand("timeout")

if __name__ == "__main__":
	try:
		assistant = VoiceControl()
		# Keep the main thread alive while the assistant runs
		while assistant.thread.is_alive():
			assistant.thread.join(0.1)
	except Exception as e:
		print(f"VoiceAssistant failed to start: {e}")
