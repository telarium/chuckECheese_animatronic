#!/usr/bin/env python3

import os
import sys
import subprocess

class Setup:
	def __init__(self):
		path = os.path.dirname(os.path.realpath(sys.argv[0]))
		
		# List of system packages to install
		packages = [
			"git", "build-essential", "python-dev-is-python3", "flex", "bison", 
			"dnsmasq", "python3-smbus", "python3-mido", "python3-rtmidi",
			"python3-flask", "python3-flask-socketio", "python3-flask-talisman", 
			"python3-eventlet", "python3-psutil", "python3-pydispatch", "python3-setuptools"
		]

		self.run_command("sudo apt-get update")

		# Install packages using subprocess and handle potential errors
		self.install_packages(packages)

		
		# Clone the flask-uploads repository
		self.run_command("git clone https://github.com/maxcountryman/flask-uploads.git")
		
		# Change directory, run setup, and clean up
		self.run_command("cd flask-uploads && sudo python3 setup.py install")
		self.run_command("sudo rm -rf flask-uploads")

	def install_packages(self, packages):
		try:
			# Join package list into a single string and install via apt-get
			subprocess.check_call(["sudo", "apt-get", "install", "-y"] + packages)
		except subprocess.CalledProcessError as e:
			print(f"Failed to install packages: {e}")
			sys.exit(1)

	def run_command(self, command):
		try:
			subprocess.check_call(command, shell=True)
		except subprocess.CalledProcessError as e:
			print(f"Command failed: {command}\nError: {e}")
			sys.exit(1)

if __name__ == "__main__":
	Setup()
