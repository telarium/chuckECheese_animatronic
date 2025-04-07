#!/usr/bin/env python3

import os

# Supress annoying Pygame messages
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
if 'XDG_RUNTIME_DIR' not in os.environ:
	os.environ['XDG_RUNTIME_DIR'] = "/tmp"

import sys
import signal
import time
import threading
import pygame
import ctypes
from pydispatch import dispatcher
from web_io import WebServer
from system_info import SystemInfo
from gpio import GPIO
from animatronic_movements import Movement
from gamepad_input import USBGamepadReader
from show_player import ShowPlayer
from voice_input_processor import VoiceInputProcessor
from voice_event_handler import VoiceEventHandler
from wifi_management import WifiManagement


class Pasqually:
	def __init__(self) -> None:
		self.is_running: bool = True

		# Initialize pygame for managing audio playback
		pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
		pygame.display.init()
		pygame.display.set_mode((1, 1))

		self.wifi_access_points = None

		# Initialize components
		self.gpio = GPIO()
		self.movements = Movement(self.gpio)
		self.web_server = WebServer()
		self.wifi_management = WifiManagement()
		self.system_info = SystemInfo()
		self.gamepad = USBGamepadReader(self.movements, self.web_server)
		self.show_player = ShowPlayer(pygame)
		self.voice_input_processor = VoiceInputProcessor(pygame)
		self.voice_event_handler = VoiceEventHandler(pygame, self.voice_input_processor)

		self.set_dispatch_events()

		# Handle SIGINT and SIGTERM for graceful shutdown
		signal.signal(signal.SIGINT, self.shutdown)
		signal.signal(signal.SIGTERM, self.shutdown)

		self.movements.set_default_animation(True)

	def set_dispatch_events(self) -> None:
		dispatcher.connect(self.on_key_event, signal='keyEvent', sender=dispatcher.Any)
		dispatcher.connect(self.on_system_info_update, signal='systemInfoUpdate', sender=dispatcher.Any)
		dispatcher.connect(self.on_voice_input_event, signal='voiceInputEvent', sender=dispatcher.Any)
		dispatcher.connect(self.on_mirrored_mode_toggle, signal='mirrorModeToggle', sender=dispatcher.Any)
		dispatcher.connect(self.on_connect_event, signal='connectEvent', sender=dispatcher.Any)
		dispatcher.connect(self.on_show_list_load, signal='showListLoad', sender=dispatcher.Any)
		dispatcher.connect(self.on_show_play, signal='showPlay', sender=dispatcher.Any)
		dispatcher.connect(self.on_show_pause, signal='showPause', sender=dispatcher.Any)
		dispatcher.connect(self.on_show_stop, signal='showStop', sender=dispatcher.Any)
		dispatcher.connect(self.on_show_end, signal='showEnd', sender=dispatcher.Any)
		dispatcher.connect(self.on_mirrored_mode, signal='onMirroredMode', sender=dispatcher.Any)
		dispatcher.connect(self.on_retro_mode, signal='onRetroMode', sender=dispatcher.Any)
		dispatcher.connect(self.on_head_nod_inverted, signal='onHeadNodInverted', sender=dispatcher.Any)
		dispatcher.connect(self.on_show_playback_midi_event, signal='showPlaybackMidiEvent', sender=dispatcher.Any)
		dispatcher.connect(self.on_activate_wifi_hotspot, signal='activateWifiHotspot', sender=dispatcher.Any)
		dispatcher.connect(self.on_connect_to_wifi_network, signal='connectToWifi', sender=dispatcher.Any)
		dispatcher.connect(self.on_web_tts_event, signal='webTTSEvent', sender=dispatcher.Any)

	def run(self) -> None:
		try:
			while self.is_running:
				# Broadcast a new wifi scan result if it has changed.
				current_wifi = self.wifi_management.get_wifi_access_points()
				if current_wifi != self.wifi_access_points:
					self.wifi_access_points = current_wifi
					self.web_server.broadcast('wifiScan', self.wifi_access_points)

				time.sleep(0.005)

		except Exception as e:
			print(f"Error in main loop: {e}")
		finally:
			print("Main loop exiting, calling shutdown...")
			self.shutdown()

	def shutdown(self, *args) -> None:
		try:
			self.is_running = False  # Signal all loops to stop

			# Stop all dependent components
			if self.voice_input_processor:
				self.voice_input_processor.shutdown()

			if self.web_server:
				self.web_server.shutdown()

			if self.show_player:
				self.show_player.stop_show()

			# Ensure all non-main threads exit before quitting pygame
			for thread in threading.enumerate():
				if thread is not threading.main_thread():
					# If thread is still alive, force kill it
					if thread.is_alive():
						try:
							ctypes.pythonapi.PyThreadState_SetAsyncExc(
								ctypes.c_long(thread.ident), ctypes.py_object(SystemExit)
							)
						except Exception as e:
							print(f"Error stopping thread {thread.name}: {e}")

			pygame.mixer.quit()
			pygame.display.quit()
			pygame.quit()

			print("Shutdown complete. Exiting.")
			sys.exit(0)

		except Exception as e:
			print(f"Error during shutdown: {e}")
			sys.exit(1)

	def on_system_info_update(self) -> None:
		self.web_server.broadcast('systemInfo', self.system_info.get())

	# Event handling methods
	def on_voice_input_event(self, id: str, value: any = None) -> None:
		self.web_server.broadcast('voiceCommandUpdate', {"id": id, "value": value})

		# Play various animations to show Pasqually is listening and processing voice commands.
		if id in ("idle", "ttsComplete"):
			# Don't do any animations while he's not doing any voice processing.
			self.movements.stop_all_animation_threads()
		elif id == "wakeWord":
			# Twirls his mustache a bit to demonstrate wakeword acknowledgement.
			self.movements.play_wakeword_acknowledgement()
			self.show_player.stop_show()  # Stop any playing shows
		elif id == "transcribing":
			# Start random blinking animation.
			self.movements.play_blink_animation()
		elif id == "llmSend":
			self.movements.play_blink_animation()
			self.movements.play_eye_left_right_animation()
		elif id == "speaking":
			self.movements.play_neck_animation()
			self.movements.play_eye_left_right_animation()
			self.movements.play_neck_animation()
		elif id in ("command", "ttsSubmitted"):
			# Add some eye left/right movement animation.
			self.movements.play_eye_left_right_animation()
			self.movements.play_blink_animation()
			self.movements.play_neck_animation()

		self.voice_event_handler.trigger_event(id, value)

	def on_show_list_load(self, show_list: any) -> None:
		self.web_server.broadcast('showListLoaded', show_list)

	def on_show_play(self, show_name: str) -> None:
		self.show_player.load_show(show_name)
		self.movements.set_default_animation(False)

	def on_show_stop(self) -> None:
		self.show_player.stop_show()
		self.movements.set_default_animation(True)

	def on_show_end(self) -> None:
		self.movements.set_default_animation(True)

	def on_show_pause(self) -> None:
		self.show_player.toggle_pause()

	def on_show_playback_midi_event(self, midi_note: any, val: any) -> None:
		self.movements.execute_midi_note(midi_note, val)

	def on_connect_event(self, client_ip: str) -> None:
		print(f"Web client connected from IP: {client_ip}")

		# Tell the web frontend what the current voice command status is.
		command = self.voice_input_processor.get_last_voice_command()
		self.web_server.broadcast('voiceCommandUpdate', command)

		self.on_system_info_update()
		self.show_player.get_show_list()
		self.web_server.broadcast('movementInfo', self.movements.get_all_movement_info())
		self.web_server.broadcast('wifiScan', self.wifi_access_points)
		self.wifi_management.scan_wifi_access_points()

	def on_key_event(self, key: any, val: any) -> None:
		# Receive key events from the HTML front end and execute any specified movement
		try:
			self.movements.execute_movement(str(key).lower(), val)
		except Exception as e:
			print(f"Invalid key: {e}")

	def on_retro_mode(self, val: any) -> None:
		self.movements.set_retro_mode(val)

	def on_head_nod_inverted(self, val: any) -> None:
		self.gamepad.head_nod_inverted = val

	def on_mirrored_mode(self, val: any) -> None:
		self.movements.set_mirrored(val)

	def on_mirrored_mode_toggle(self) -> None:
		# Toggle animation mirrored mode (swapping left and right movements)
		new_mirror_mode = not self.movements.b_mirrored
		self.movements.set_mirrored(new_mirror_mode)

	def on_activate_wifi_hotspot(self, activate: bool) -> None:
		if activate:
			self.wifi_management.activate_hotspot()
		elif not activate and self.wifi_management.is_hotspot_active():
			self.wifi_management.deactivate_hotspot_and_reconnect()

	def on_connect_to_wifi_network(self, ssid: str, password: any = None) -> None:
		self.wifi_management.connect_to_wifi(ssid, password)

	def on_web_tts_event(self, val: any) -> None:
		dispatcher.send(signal="voiceInputEvent", id="ttsSubmitted")
		self.voice_input_processor.generate_and_play_tts(val)


if __name__ == "__main__":
	animatronic = Pasqually()
	animatronic.run()
