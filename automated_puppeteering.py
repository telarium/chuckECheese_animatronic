from pydub import AudioSegment
from pydispatch import dispatcher
from scipy.io import wavfile
import pygame
import numpy as np
import time
import io

class AutomatedPuppeteering:
	def __init__(self, pygame_instance, threshold=0.15, interval_ms=25):
		self.pygame = pygame_instance

		# Ensure threshold is numeric
		if not isinstance(threshold, (int, float)):
			raise ValueError("Threshold must be a numeric value!")
		
		self.threshold = threshold  # Audio level threshold to open/close mouth
		self.interval_ms = interval_ms  # Time interval to monitor audio (in ms)

	def normalize_rms(self, rms, max_rms):
		"""Normalize RMS to be between 0 and 1 based on dynamic max RMS value."""
		return min(rms / max_rms, 1.0)  # Normalize RMS to 0-1 range

	def calculate_rms(self, data, sample_rate):
		"""Calculate RMS values over time for the audio."""
		window_size = int(sample_rate * (self.interval_ms / 1000.0))  # Interval in samples
		rms_values = []
		num_samples = len(data)
		
		max_rms = np.max(np.abs(data))  # Dynamically adjust max RMS from data

		for i in range(0, num_samples, window_size):
			window = data[i:i + window_size]
			rms = np.sqrt(np.mean(window.astype(np.float64) ** 2))
			if np.isnan(rms) or np.isinf(rms):
				rms = 0  # Replace NaN/inf values with 0
			rms_values.append(self.normalize_rms(rms, max_rms))  # Normalize RMS value

		return rms_values

	def load_audio_data(self, file_path):
		"""Load audio data and sample rate from various file formats."""
		if file_path.endswith('.mp3'):
			audio = AudioSegment.from_mp3(file_path)
		elif file_path.endswith('.ogg'):
			audio = AudioSegment.from_ogg(file_path)
		elif file_path.endswith('.wav'):
			audio = AudioSegment.from_wav(file_path)
		else:
			raise ValueError(f"Unsupported file format: {file_path}")

		# Convert to raw audio data and retrieve sample rate
		wav_io = io.BytesIO()
		audio.export(wav_io, format="wav")
		wav_io.seek(0)
		sample_rate, data = wavfile.read(wav_io)

		return sample_rate, data

	def monitor_audio(self, file_path):
		"""Monitor the audio levels during playback with improved synchronization."""
		try:
			# Load audio data
			sample_rate, data = self.load_audio_data(file_path)

			# Calculate RMS values
			rms_values = self.calculate_rms(data, sample_rate)

			# Play the audio file using pygame.mixer
			self.pygame.mixer.music.load(file_path)
			self.pygame.mixer.music.play()

			# Use a monotonic clock for scheduling to prevent drift
			start_time = time.monotonic()
			iteration = 0
			duration = len(data) / sample_rate  # Audio duration in seconds

			for rms in rms_values:
				# If playback duration is exceeded, break out of the loop
				if time.monotonic() - start_time > duration:
					break

				# Trigger mouth movement based on the RMS threshold
				if rms > self.threshold:
					dispatcher.send(signal="keyEvent", key='x', val=1)  # Mouth open event
				else:
					dispatcher.send(signal="keyEvent", key='x', val=0)  # Mouth close event

				iteration += 1
				# Calculate target time for the next update
				target_time = start_time + iteration * (self.interval_ms / 1000.0)
				sleep_duration = target_time - time.monotonic()
				if sleep_duration > 0:
					time.sleep(sleep_duration)

			# Wait for the music to finish without busy-waiting
			while self.pygame.mixer.music.get_busy():
				self.pygame.time.wait(10)  # Small wait to avoid a busy loop

		except Exception as e:
			print(f"Error processing audio file {file_path}: {e}")

	def play_audio_with_puppeting(self, file_path):
		"""Plays audio and synchronizes mouth state with the audio."""
		try:
			print(f"Playing audio from {file_path}...")  # Debug output
			self.monitor_audio(file_path)
		except Exception as e:
			print(f"Error playing {file_path}: {e}")
