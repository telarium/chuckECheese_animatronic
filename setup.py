#!/usr/bin/env python3

import os
import sys
import subprocess

class Setup:
	def __init__(self):
		path = os.path.dirname(os.path.realpath(sys.argv[0]))

		# List of system packages to install (from apt)
		packages = [
			"git", "build-essential", "python3-dev", "flex", "bison", "mpv", "hostapd", "dnsmasq",
			"python3-smbus", "python3-evdev", "python3-setuptools", "python3-mido",
			"python3-flask", "python3-flask-socketio", "python3-flask-talisman", "python3-pip",
			"python3-eventlet", "python3-psutil", "python3-pydispatch", "python3-pygame", "iw",
			"iproute2"
		]

		self.run_command("sudo apt-get update")

		# Install system packages using subprocess and handle potential errors
		self.install_packages(packages)

		# Install Python dependencies via pip with --break-system-packages
		self.install_python_packages([
			"pvporcupine", "pvrhino", "openai", "google-cloud-speech", "elevenlabs", "piper-tts", "pywifi"
		])
		
		# Clone the flask-uploads repository
		self.run_command("git clone https://github.com/maxcountryman/flask-uploads.git")
		
		# Change directory, run setup, and clean up
		self.run_command("cd flask-uploads && sudo python3 setup.py install")
		self.run_command("sudo rm -rf flask-uploads")

		# Clone Chuck E. Cheese Git repository
		self.run_command("git clone https://github.com/YourGitRepo/ChuckE.git chuck_e_git")
		
		# Set up Piper TTS models
		self.setup_piper_models()

	def install_packages(self, packages):
		try:
			# Install packages using apt-get
			subprocess.check_call(["sudo", "apt-get", "install", "-y"] + packages)
		except subprocess.CalledProcessError as e:
			print(f"Failed to install packages: {e}")
			sys.exit(1)

	def install_python_packages(self, packages):
		try:
			for package in packages:
				# Use pip with --break-system-packages flag to allow installation
				subprocess.check_call(["sudo", sys.executable, "-m", "pip", "install", "--break-system-packages", package])
		except subprocess.CalledProcessError as e:
			print(f"Failed to install Python packages: {e}")
			sys.exit(1)

	def setup_piper_models(self):
		try:
			# Create directory for Piper models
			piper_dir = os.path.join(os.getcwd(), "chuck_e_git", "piper")
			os.makedirs(piper_dir, exist_ok=True)

			# Download Ryan Low voice model
			subprocess.check_call([
				"wget",
				"-O", os.path.join(piper_dir, "en_US-ryan-low.onnx"),
				"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/low/en_US-ryan-low.onnx?download=true"
			])
			subprocess.check_call([
				"wget",
				"-O", os.path.join(piper_dir, "en_US-ryan-low.json"),
				"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/low/en_US-ryan-low.onnx.json?download=true"
			])

			print("Piper TTS models are available in the chuck_e_git/piper directory.")
		except subprocess.CalledProcessError as e:
			print(f"Failed to set up Piper models: {e}")
			sys.exit(1)

	def run_command(self, command):
		try:
			subprocess.check_call(command, shell=True)
		except subprocess.CalledProcessError as e:
			print(f"Command failed: {command}\nError: {e}")
			sys.exit(1)

if __name__ == "__main__":
	Setup()
