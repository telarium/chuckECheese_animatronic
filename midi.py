import mido
import eventlet

eventlet.monkey_patch()

class MIDI:
    def __init__(self, callback=None):
        self.port = None
        self.input_port = None
        self.callback = callback
        self.input_thread = None

        self.open_port()

    def find_midi_port_output(self):
        # Finds a MIDI output port with "MIDI" in its name.
        ports = mido.get_output_names()
        for port in ports:
            if 'MIDI' in port:
                print(f"Found MIDI port: {port}")
                return port
        print("No MIDI port found with 'MIDI' in its name.")
        return None

    def find_midi_input_port(self):
        # Finds a MIDI input port with "MIDI" in its name.
        ports = mido.get_input_names()
        for port in ports:
            if 'MIDI' in port:
                print(f"Found MIDI input port: {port}")
                return port
        print("No MIDI input port found with 'MIDI' in its name.")
        return None

    def open_input_port(self):
        input_port_name = self.find_midi_input_port()

        if input_port_name:
            try:
                self.input_port = mido.open_input(input_port_name)
                print(f"Opened MIDI input port: {input_port_name}")
                self.start_input_thread()
            except Exception as e:
                print(f"Error opening MIDI input port '{input_port_name}': {e}")
        else:
            print("No valid MIDI input port found to open.")

    def open_port(self):
        port_name_output = self.find_midi_port_output()

        if port_name_output:
            try:
                self.port = mido.open_output(port_name_output)
                print(f"Opened MIDI output port: {port_name_output}")
            except Exception as e:
                print(f"Error opening MIDI output port '{port_name_output}': {e}")
        else:
            print("No valid MIDI output port found to open.")

        self.open_input_port()

    def send_note_on(self, note, velocity=127):
        if self.port is None:
            self.open_port()

        if self.port:
            msg = mido.Message('note_on', note=note, velocity=velocity)
            self.port.send(msg)
            print(f"Sent note_on: note={note}, velocity={velocity}")

    def send_note_off(self, note, velocity=127):
        if self.port is None:
            self.open_port()

        if self.port:
            msg = mido.Message('note_off', note=note, velocity=velocity)
            self.port.send(msg)
            print(f"Sent note_off: note={note}, velocity={velocity}")

    def start_input_thread(self):
        """
        Starts a non-blocking thread using eventlet to listen for incoming MIDI messages.
        """
        self.input_thread = eventlet.spawn(self.listen_for_input)

    def listen_for_input(self):
        """
        Continuously listens for incoming MIDI messages and triggers the callback when a note event is received.
        This function runs asynchronously using eventlet to avoid blocking the main program.
        """
        if self.input_port:
            while True:
                for msg in self.input_port.iter_pending():
                    if self.callback and msg.type in ['note_on', 'note_off']:
                        # Call the callback with the message details
                        self.callback(msg)
                    print(f"Received MIDI message: {msg}")
                eventlet.sleep(0.01)  # Yield control to other green threads

    def close(self):
        """
        Closes the MIDI output and input ports, and stops the input thread.
        """
        if self.input_thread:
            self.input_thread.kill()
            print("Stopped MIDI input thread.")
        
        if self.port:
            self.port.close()
            print("Closed MIDI output port.")
        if self.input_port:
            self.input_port.close()
            print("Closed MIDI input port.")