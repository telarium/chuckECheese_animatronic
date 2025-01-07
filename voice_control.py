from collections import deque
from google.cloud import speech
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings, stream
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
import sys
import threading
import time

class VoiceControl:
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

		# Create a temporary directory
		self.temp_dir = tempfile.TemporaryDirectory()

		# Register signal handlers for graceful shutdown
		signal.signal(signal.SIGTERM, self.cleanup)
		signal.signal(signal.SIGINT, self.cleanup)

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
		max_silent_frames = int(self.sample_rate * 1.5 / self.frame_length)  # 1.5 seconds of silence

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
				if rms < 500000:  # Silence threshold (adjustable)
					silent_frames += 1
				else:
					silent_frames = 0

				if silent_frames > max_silent_frames:
					print("User stopped speaking.")
					process.terminate()
					process.wait()
					return intent_audio

				# Stop after 8 seconds of audio regardless
				if len(intent_audio) >= self.sample_rate * 8 * 2:
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
				print("No transcription result from Google.")
				return None
		except Exception as e:
			print(f"Error during transcription: {e}")
			return None

	def send_to_chatgpt(self, text):
		"""Send text to ChatGPT and generate a response."""
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
		"""Generate audio using ElevenLabs TTS API."""
		try:
			client = ElevenLabs(api_key=self.elevenlabs_key)

			stability = 0.7
			similarity_boost = 0.8
			style_exaggeration = 0.5

			audio = client.generate(
				text=text,
				stream=True,
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
			stream(audio)
		except Exception as e:
			print(f"Error generating or playing TTS audio: {e}")

	def cleanup(self, *args):
		"""Clean up resources and terminate gracefully."""
		self.running = False  # Stop the thread's loop

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

	def run_thread(self):
		"""Run the assistant's main loop in a separate thread."""
		while self.running:
			try:
				self.run()
			except Exception as e:
				print(f"Error in VoiceAssistant loop: {e}")

	def run(self):
		"""Main loop to handle wakeword detection and audio processing."""
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


if __name__ == "__main__":
	try:
		assistant = VoiceControl()
		# Keep the main thread alive while the assistant runs
		while assistant.thread.is_alive():
			assistant.thread.join(0.1)
	except Exception as e:
		print(f"VoiceAssistant failed to start: {e}")
