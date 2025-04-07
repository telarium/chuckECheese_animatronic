import subprocess
from pydispatch import dispatcher
import mido
from typing import Optional, List

class MIDI:
	def __init__(self, input_port_name: Optional[str] = None, output_port_name: Optional[str] = None) -> None:
		# Load the virtual MIDI module using modprobe.
		try:
			subprocess.run(["sudo", "modprobe", "snd-virmidi"], check=True)
			print("Loaded snd-virmidi module.")
		except subprocess.CalledProcessError as e:
			print(f"Error loading snd-virmidi module: {e}")
			raise

		# Now get the list of available MIDI port names using mido.
		input_ports: List[str] = mido.get_input_names()
		output_ports: List[str] = mido.get_output_names()

		# Debug: Print all available port names
		# print("Available MIDI Input Ports:", input_ports)
		# print("Available MIDI Output Ports:", output_ports)

		# Use provided port names or find a default port containing "uhost"
		self.input_port_name: Optional[str] = input_port_name or self._find_default_port(input_ports)
		self.output_port_name: Optional[str] = output_port_name or self._find_default_port(output_ports)

		if not self.input_port_name or not self.output_port_name:
			raise RuntimeError("Could not find valid MIDI input/output ports.")

		# Open the MIDI input and output ports.
		self.inport = mido.open_input(self.input_port_name, callback=self._midi_callback)
		self.outport = mido.open_output(self.output_port_name)
		# print(f"MIDI Input opened on: {self.input_port_name}")
		# print(f"MIDI Output opened on: {self.output_port_name}")

	def _find_default_port(self, port_list: List[str]) -> Optional[str]:
		# Look for a port with 'uhost' (case insensitive)
		for port in port_list:
			if 'uhost' in port.lower():
				return port
		return port_list[0] if port_list else None

	def _midi_callback(self, message: mido.Message) -> None:
		# Callback function that is called when a MIDI message is received.
		# (Note: fixed the variable name 'velocity' to 'value')
		# print("Received MIDI message:", message)
		if message.type in ['note_on', 'note_off']:
			note = message.note
			value = 1 if message.velocity >= 100 else 0
			dispatcher.send(signal='showPlaybackMidiEvent', midi_note=note, val=value)

	def send_message(self, note: int, value: int) -> None:
		if value == 1:
			# Note on message with full velocity
			msg = mido.Message('note_on', note=note, velocity=127)
		else:
			# Note off message with lowest velocity
			msg = mido.Message('note_off', note=note, velocity=0)
		self.outport.send(msg)
		# print(f"Sent MIDI message: {msg}")

# Example usage:
if __name__ == "__main__":
	midi = MIDI()
	# Keep the application running to receive callbacks
	input("Press Enter to exit...\n")
