# chuckECheese_animatronic
A project to retrofit an old 1981 Chuck E Cheese animatronic character named Pasqually, using as Raspberry PI to control pneumatics through a web interface. You know, for fun.

# MIDI
To use Chrome's MIDI capabilities (optional), you must access the HTTPS secure version of the web server.

First, on the Linux device that runs the server, we need to create a certificate:

`openssl req -new -x509 -keyout server.key -out server.crt -days 365 -nodes`

Copy the server.crt to your client machine and import it into Chrome browser under settings.

Make sure "Local Management via HTTPS" is enabled on your router.

You'll also need to install a virtual MIDI device on Windows so that you can record the MIDI data in a sequencer and play it back later:

https://www.nerds.de/en/loopbe30.html

Set it up so that it runs at least two MIDI ports. By default, port 1 will be used to output MIDI from the web frontend to the MIDI sequencer of your choice. To play MIDI from your sequencer to the web server, set the sequencer's MIDI output to be port 2.
