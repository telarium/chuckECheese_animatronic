import pvporcupine
import pvrhino
import struct
import subprocess
import configparser
import os
import wave
from collections import deque
from google.cloud import speech
from pydub import AudioSegment
import openai
import pygame
import requests

class VoiceAssistant:
	def __init__(self, config_file="VoiceControlConfig.txt"):
		self.config = self.load_config(config_file)

		# PicoVoice and Google Speech-to-Text keys
		self.pv_access_key = self.config["PicoVoice"]["AccessKey"]
		self.wakeword_path = self.config["PicoVoice"]["WakewordPath"]
		self.rhino_context_path = self.config["PicoVoice"]["RhinoContextPath"]
		self.google_cloud_key_path = self.config["SpeechToText"]["GoogleCloudKeyPath"]
		os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.google_cloud_key_path

		# OpenAI ChatGPT key and context
		self.openai_api_key = self.config["ChatGPT"]["OpenAIKey"]
		self.chatgpt_context = self.config["ChatGPT"]["ChatGPTContext"]
		openai.api_key = self.openai_api_key
		self.openai_client = openai.Client(api_key=self.openai_api_key)

		# ElevenLabs TTS keys
		self.elevenlabs_key = self.config["TextToSpeech"]["ElevenLabsKey"]
		self.elevenlabs_voice_id = self.config["TextToSpeech"]["ElevenLabsVoiceID"]

		self.sample_rate = 16000
		self.porcupine = pvporcupine.create(
			access_key=self.pv_access_key,
			keyword_paths=[self.wakeword_path],
		)
		self.rhino = pvrhino.create(
			access_key=self.pv_access_key,
			context_path=self.rhino_context_path,
		)

		self.pre_wakeword_buffer = deque(maxlen=10)  # Store ~1 second of pre-wakeword audio
		self.frame_length = self.porcupine.frame_length
		self.frame_size = self.frame_length * 2
		self.speech_client = speech.SpeechClient()

	def load_config(self, config_file):
		config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)
		if not os.path.exists(config_path):
			raise FileNotFoundError(f"Configuration file not found: {config_path}")
		config = configparser.ConfigParser()
		config.read(config_path)
		return config

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
			print("Recording audio stream...")
			process = subprocess.Popen(command, stdout=subprocess.PIPE)
			return process
		except Exception as e:
			print(f"Error starting audio stream: {e}")
			return None

	def process_audio_stream(self, process):
		"""Process audio for wakeword detection and transition seamlessly to intent capture."""
		wakeword_detected = False
		intent_audio = bytearray()
		silent_frames = 0
		max_silent_frames = int(self.sample_rate * 0.5 / self.frame_length)  # 0.5 seconds of silence

		while True:
			chunk = process.stdout.read(self.frame_size)
			if len(chunk) < self.frame_size:
				break

			self.pre_wakeword_buffer.append(chunk)
			audio_frame = struct.unpack_from(f"{self.frame_length}h", chunk)

			if not wakeword_detected and self.porcupine.process(audio_frame) >= 0:
				print("Wakeword detected!")
				wakeword_detected = True
				intent_audio.extend(b"".join(self.pre_wakeword_buffer))
				self.pre_wakeword_buffer.clear()

			if wakeword_detected:
				intent_audio.extend(chunk)

				# Check for silence
				rms = sum(x * x for x in audio_frame) / len(audio_frame)  # Root Mean Square
				if rms < 100:  # Silence threshold (adjustable)
					silent_frames += 1
				else:
					silent_frames = 0

				if silent_frames > max_silent_frames:
					print("User stopped speaking.")
					process.terminate()
					process.wait()
					return intent_audio

				# Stop after 5 seconds of audio regardless
				if len(intent_audio) >= self.sample_rate * 5 * 2:
					print("Maximum recording duration reached.")
					process.terminate()
					process.wait()
					return intent_audio

	def save_audio_to_file(self, audio_data, filename):
		"""Save audio data to a WAV file."""
		with wave.open(filename, "wb") as wf:
			wf.setnchannels(1)
			wf.setsampwidth(2)
			wf.setframerate(self.sample_rate)
			wf.writeframes(audio_data)
		print(f"Saved audio to {filename}")

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
				print(f"Google Speech-to-Text result: {transcript}")
				return transcript
			else:
				print("No transcription result from Google.")
				return None
		except Exception as e:
			print(f"Error during transcription: {e}")
			return None

	def send_to_chatgpt(self, text):
		print(f"Sending text to ChatGPT: {text}")
		try:
			response = self.openai_client.chat.completions.create(
				model="gpt-4",
				messages=[
					{"role": "system", "content": self.chatgpt_context},
					{"role": "user", "content": text},
				],
			)
			chat_response = response.choices[0].message.content
			print(f"ChatGPT Response: {chat_response}")

			# Generate and play TTS audio
			self.generate_and_play_tts(chat_response)

			return chat_response
		except Exception as e:
			print(f"Failed to get response from ChatGPT: {e}")
			return None

	def generate_and_play_tts(self, text):
		"""Generate audio using ElevenLabs TTS API with eleven_multilingual_v2, convert it, and play it back."""
		try:
			print("Generating audio using ElevenLabs API...")

			# Define the API endpoint
			url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}"
			headers = {
				"xi-api-key": self.elevenlabs_key,
				"Content-Type": "application/json"
			}
			payload = {
				"text": text,
				"model_id": "eleven_multilingual_v2",
				"voice_settings": {
					"stability": 0.7,
					"similarity_boost": 0.8,
					"style_exaggeration": 0.8
				}
			}

			# Send the request to ElevenLabs API
			response = requests.post(url, headers=headers, json=payload)

			# Check response status and handle audio
			if response.status_code == 200:
				raw_filename = "raw_response.wav"
				compatible_filename = "response.wav"

				# Save raw audio
				with open(raw_filename, "wb") as f:
					f.write(response.content)
				print(f"Audio saved to {raw_filename}")

				# Convert to a compatible WAV format
				audio = AudioSegment.from_file(raw_filename)
				audio.export(compatible_filename, format="wav")
				print(f"Converted audio saved to {compatible_filename}")

				# Play the converted audio
				self.play_audio(compatible_filename)
			else:
				print(f"Error from ElevenLabs API: {response.status_code}, {response.text}")

		except Exception as e:
			print(f"Error generating or playing TTS audio: {e}")


	def play_audio(self, filename):
		"""Play an audio file using pygame."""
		try:
			print(f"Playing audio from {filename}...")
			pygame.mixer.init()
			pygame.mixer.music.load(filename)
			pygame.mixer.music.play()

			# Wait until the audio finishes playing
			while pygame.mixer.music.get_busy():
				pygame.time.Clock().tick(10)
		except Exception as e:
			print(f"Error playing audio: {e}")
		finally:
			pygame.mixer.quit()

	def run(self):
		print("Listening for wakeword...")
		stream_process = self.record_audio_stream()
		if not stream_process:
			print("Failed to start audio stream.")
			return

		# Process audio and capture intent audio
		intent_audio = self.process_audio_stream(stream_process)

		# Trim a small portion (e.g., 100ms) from the start of the intent audio
		trim_frames = int(self.sample_rate * 0.1 * 2)  # 100 ms worth of frames
		if len(intent_audio) > trim_frames:
			intent_audio = intent_audio[trim_frames:]
			print(f"Trimmed {trim_frames} bytes ({len(intent_audio)} bytes remaining).")

		# Save trimmed intent audio for debugging
		self.save_audio_to_file(intent_audio, "intent_trimmed.wav")

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
						return

		print("No intent detected. Transcribing audio...")
		transcription = self.transcribe_audio(intent_audio)
		if transcription:
			self.send_to_chatgpt(transcription)

	def cleanup(self):
		self.porcupine.delete()
		self.rhino.delete()


if __name__ == "__main__":
	try:
		assistant = VoiceAssistant()
		assistant.run()
	except Exception as e:
		print(f"VoiceAssistant failed to start: {e}")
