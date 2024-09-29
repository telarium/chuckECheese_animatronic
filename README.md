# chuckECheese_animatronic
A project to control an old 1981 Chuck E Cheese animatronic character by the name of Pasqually. Uses CHIP for the microcontroller to control pneumatics through a web interface.

# MIDI
To use Chrome's MIDI capabilities (optional), you must access the HTTPS secure version of the web server.

First, on the Linux device that runs the server, we need to create a certificate:

`openssl req -new -x509 -keyout server.key -out server.crt -days 365 -nodes`

Copy the server.crt to your client machine and import it into Chrome browser under settings.

Make sure "Local Management via HTTPS" is enabled on your router.

You'll also need to install a virtual MIDI device on Windows so that you can record the MIDI data in a sequencer and play it back later:

https://www.nerds.de/en/loopbe1.html
