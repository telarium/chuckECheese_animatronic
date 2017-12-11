import time
import eventlet
import CHIP_IO.GPIO as GPIO
import threading
import json
from pydispatch import dispatcher

# Valve1  -> LCD-D22 -> Eye right
# Valve2  -> LCD-D13 -> Eye left
# Valve3  -> LCD-D20 -> Eyelid Up
# Valve4  -> LCD-D15 -> Eyelid down
# Valve5  -> LCD-D18 -> Mustache
# Valve6  -> NONE
# Valve7  -> LCD-D14 -> Neck down
# Valve8  -> LCD-D19 -> Neck up
# Valve9  -> LCD-D12 -> Left shoulder out
# Valve10 -> LCD-D21 -> Left shoulder in
# Valve11 -> LCD-D10 -> --unused--
# Valve12 -> CSID6   -> --unused--
# Valve13 -> LCD-D6  -> Left arm down
# Valve14 -> CSID4   -> Left arm up
# Valve15 -> LCD-D4  -> Mouth open
# Valve16 -> CSID2   -> Mouth closed
# Valve17 -> LCD-D3  -> Torso left
# Valve18 -> CSID0   -> Torso right
# Valve19 -> LCD-D5  -> Lean forward
# Valve20 -> CSID7   -> Lean Backward
# Valve21 -> LCD-D7  -> Right arm down
# Valve22 -> CSID5   -> Right arm up
# Valve23 -> LCD-D11 -> Right shoulder in
# Valve24 -> CSID3   -> Right shoulder out
# Valve25 -> NONE (24v)
# Valve26 -> CSID1   -> --unused--

class Struct():
	key = '' # A keyboard key press assigned to this movement
	outputPin1 = None # First IO pin on the Arduino
	outputPin2 = None # Optional second IO pin (the inverse state of pin 1)
	midiNote = 0 # A MIDI note assigned to this movement to be recorded in a sequencer
	outputPin1MaxTime = -1 # How much time is pin 1 allowed to be pulled high? (optional, -1 means infinite)
	outputPin2MaxTime = -1 # See above (optional, -1 means infinite)
	outputInverted = False # Invert high/low for this movement (optional)
	callbackFunc = None # A function to call when the value has changed (optional)
	linkKey = None # A keyboard key that binds this movement to another (optional)
	linkedMovement = None # The movement we want to bind to this link (optional)

class Movement:
	all = []

	# Callback function for eyes to do a best attempt to re-center the eyeballs when keys are released.
	def onEyeMove( self, movement, val ):
		if val == 0 and self.leftShoulder.keyIsPressed != True and self.rightShoulder.keyIsPressed != True:
			pin = None
			if movement == self.eyesLeft:
				pin = self.eyesRight.outputPin1
			elif movement == self.eyesRight:
				pin = self.eyesLeft.outputPin1

			if pin:
				# Move eyes in the opposite direction for a split second.
				# This will actuate the springs and hopefully re-center the eyeballs.
				self.setPin(pin,1)
				time.sleep(0.05)
				# Don't disable output if user has pressed another eye key
				if self.eyesRight.keyIsPressed != True and self.eyesLeft.keyIsPressed != True:
					self.setPin(pin,0)

	# Callback function for eyes to attempt a half-blink... or, as I call it, the "stink eye"
	def onEyeBlinkHalf(self, movement, val):
		try:
			blinked = self.eyesBlinkHalf.bBlinked
		except:
			self.eyesBlinkHalf.bBlinked = False

		print self.eyesBlinkHalf.bBlinked

		self.setPin(self.eyesBlinkFull.outputPin2, 0)
		if val == 1 and self.eyesBlinkHalf.bBlinked != True:
			self.eyesBlinkHalf.bBlinked = True
			time.sleep(0.020)
			self.setPin(self.eyesBlinkHalf.outputPin1, 0)
		elif val == 1 and self.eyesBlinkHalf.bBlinked == True:
			self.eyesBlinkHalf.bBlinked = Falsedis
			self.setPin(self.eyesBlinkHalf.outputPin1, 0)
			self.executeMovement(self.eyesBlinkFull.key,0)
			time.sleep(0.025)
			self.setPin(self.eyesBlinkFull.outputPin2, 0)

	def __init__(self):
		self.bThreadStarted = False	

		# Define all of our movements here.
		self.rightShoulder = Struct()
		self.rightShoulder.key = 'o'
		self.rightShoulder.gamepadButton = 10
		self.rightShoulder.outputPin2 = 'CSID3'
		self.rightShoulder.outputPin1 = 'LCD-D11'
		self.rightShoulder.outputPin2MaxTime = 0.5
		self.rightShoulder.outputPin1MaxTime = 60*10
		self.rightShoulder.midiNote = 50
		self.all.append( self.rightShoulder )
       
		self.rightArm = Struct()
		self.rightArm.key = 'l'
		self.rightArm.gamepadButton = 6
		self.rightArm.outputPin2 = 'CSID5'
		self.rightArm.outputPin1 = 'LCD-D7'
		self.rightArm.outputPin2MaxTime = -1
		self.rightArm.outputPin1MaxTime = 0.75
		self.rightArm.midiNote = 52
		self.all.append( self.rightArm )
       
		self.leftShoulder = Struct()
		self.leftShoulder.key = 'u'
		self.leftShoulder.gamepadButton = 9
		self.leftShoulder.outputPin2 = 'LCD-D12'
		self.leftShoulder.outputPin1 = 'LCD-D21'
		self.leftShoulder.outputPin2MaxTime = 0.5
		self.leftShoulder.outputPin1MaxTime = 60*10
		self.leftShoulder.linkKey = 'i'
		self.leftShoulder.linkedMovement = self.rightShoulder
		self.leftShoulder.midiNote = 53
		self.all.append( self.leftShoulder )
       
		self.leftArm = Struct()
		self.leftArm.key = 'j'
		self.leftArm.gamepadButton = 5
		self.leftArm.outputPin2 = 'CSID4'
		self.leftArm.outputPin1 = 'LCD-D6'
		self.leftArm.outputPin2MaxTime = -1
		self.leftArm.outputPin1MaxTime = 0.75
		self.leftArm.linkKey = 'k'
		self.leftArm.linkedMovement = self.rightArm
		self.leftArm.midiNote = 55
		self.all.append( self.leftArm )

		self.mouth = Struct()
		self.mouth.key = 'x'
		self.mouth.gamepadButton = 1
		self.mouth.outputPin1 = 'LCD-D4'
		self.mouth.outputPin2 = 'CSID2'
		self.mouth.outputPin1MaxTime = 0.75
		self.mouth.outputPin2MaxTime = 0.75
		self.mouth.midiNote = 56
		self.all.append( self.mouth )
       
		self.mustache = Struct()
		self.mustache.key = 'c'
		self.mustache.gamepadButton = 1
		self.mustache.outputPin1 = 'LCD-D18'
		self.mustache.outputPin1MaxTime = 60*5
		self.mustache.midiNote = 57
		self.mustache.linkKey = 'z'
		self.mustache.linkedMovement = self.mouth
		self.all.append( self.mustache )
       
		self.eyesLeft = Struct()
		self.eyesLeft.key = 'q'
		self.eyesLeft.gamepadButton = 3
		self.eyesLeft.outputPin1 = 'LCD-D22'
		self.eyesLeft.outputPin1MaxTime = 60*10
		self.eyesLeft.midiNote = 58
		self.eyesLeft.callbackFunc = self.onEyeMove
		self.all.append( self.eyesLeft )
       
		self.eyesRight = Struct()
		self.eyesRight.key = 'e'
		self.eyesRight.gamepadButton = 2
		self.eyesRight.outputPin1 = 'LCD-D13'
		self.eyesRight.outputPin1MaxTime = 60*10
		self.eyesRight.midiNote = 59
		self.eyesRight.callbackFunc = self.onEyeMove
		self.all.append( self.eyesRight )
       
		self.eyesBlinkFull = Struct()
		self.eyesBlinkFull.key = 'w'
		self.eyesBlinkFull.gamepadButton = 4
		self.eyesBlinkFull.outputPin1 = 'LCD-D15'
		self.eyesBlinkFull.outputPin2 = 'LCD-D20'
		self.eyesBlinkFull.outputPin1MaxTime = 0.25
		self.eyesBlinkFull.outputPin2MaxTime = 0.25
		self.eyesBlinkFull.midiNote = 60
		self.all.append( self.eyesBlinkFull )

		self.eyesBlinkHalf = Struct()
		self.eyesBlinkHalf.key = 'r'
		self.eyesBlinkHalf.outputPin1 = 'LCD-D15'
		self.eyesBlinkHalf.outputPin1MaxTime = 0.25
		self.eyesBlinkHalf.midiNote = 61
		self.eyesBlinkHalf.callbackFunc = self.onEyeBlinkHalf
		self.all.append( self.eyesBlinkHalf )
       
		self.bodyLeanUp = Struct()
		self.bodyLeanUp.key = 'm'
		self.bodyLeanUp.outputPin1 = 'LCD-D5'
		self.bodyLeanUp.outputInverted = True
		self.bodyLeanUp.midiNote = 62
		self.all.append( self.bodyLeanUp ) 

		self.bodyLeanDown = Struct()
		self.bodyLeanDown.key = 'n'
		self.bodyLeanDown.gamepadButton = 14
		self.bodyLeanDown.outputPin1 = 'CSID7'
		self.bodyLeanDown.outputPin1MaxTime = 2
		self.bodyLeanDown.midiNote = 63
		self.all.append( self.bodyLeanDown )
       
		self.neckLeft = Struct()
		self.neckLeft.key = 'a'
		self.neckLeft.gamepadButton = 15
		self.neckLeft.outputPin1 = 'LCD-D3'
		self.neckLeft.outputPin1MaxTime = 0.8
		self.neckLeft.midiNote = 64
		self.all.append( self.neckLeft )
       
		self.neckRight = Struct()
		self.neckRight.key = 'd'
		self.neckRight.gamepadButton = 16
		self.neckRight.outputPin1 = 'CSID0'
		self.neckRight.outputPin1MaxTime = 0.8
		self.neckRight.midiNote = 65
		self.all.append( self.neckRight )
       
		self.headUpDown = Struct()
		self.headUpDown.key = 's'
		self.headUpDown.gamepadButton = 13
		self.headUpDown.outputPin1 = 'LCD-D14'
		self.headUpDown.outputPin2 = 'LCD-D19'
		self.headUpDown.outputPin1MaxTime = 60*60
		self.headUpDown.midiNote = 66
		self.all.append( self.headUpDown )
		
		for i in self.all:
			i.keyIsPressed = False
			val = GPIO.LOW
			try:
				if i.outputInverted == True:
					val = GPIO.HIGH
			except:
				i.outputInverted = False

			i.pin1Time = 0
			
			GPIO.cleanup(i.outputPin1)
			GPIO.setup(i.outputPin1,GPIO.OUT)
			self.setPin(i.outputPin1, val)
			if( i.outputPin2 ):
				i.pin2Time = 0
				GPIO.cleanup(i.outputPin2)
				GPIO.setup(i.outputPin2,GPIO.OUT)
				self.setPin(i.outputPin2, 1-val)

	# Fromat MIDI notes into a string to pass to the HTML front end
	# This way, javascript key presses can control MIDI events directly
	def getJSON( self ):
		jsonData = '{"movements": ['
		for i in self.all:
			jsonData = jsonData + '{"key":"' + i.key + '","midiNote":"' + str(i.midiNote) + '"},'

		jsonData = jsonData[:-1]
		jsonData = jsonData + ']}'

		return json.loads(jsonData)

	# Monitor state of IO and disable any that have been left on past the maximum allowed time.
	def updatePins(self):
		while self:
			time.sleep(0.1)
			for i in self.all:
				if i.outputPin1MaxTime > -1 and i.pin1Time > 0:
					i.pin1Time-=0.1
					if i.pin1Time <= 0:
						i.pin1Time = 0
						self.setPin(i.outputPin1, 0)
				
				if i.outputPin2MaxTime > -1 and i.pin2Time > 0:
					i.pin2Time-=0.1
					if i.pin2Time <= 0:
						i.pin2Time = 0
						self.setPin(i.outputPin2, 0)

	def setPin( self, pin, val ):
		GPIO.output(pin,val)

	def executeMovement( self, key, val ):
		for i in self.all:
			bDoCallback = False
			if( i.key == key and key ):
				print i.key
				if val == 1 and i.keyIsPressed == False:
					i.keyIsPressed = True
					bDoCallback = True
				elif val == 0 and i.keyIsPressed == True:
					i.keyIsPressed = False
					bDoCallback = True

				if i.outputInverted == True:
					val = 1 - val

				self.setPin(i.outputPin1, val)
				if( val == 1 ):
					i.pin1Time = i.outputPin1MaxTime
				else:
					i.pin1Time = 0

				if( i.outputPin2 ):
					self.setPin(i.outputPin2, 1-val)
					if( val == 1 ):
						i.pin2Time = 0
					else:
						i.pin2Time = i.outputPin2MaxTime

				func = i.callbackFunc
				try:
					# If a callback function has been defined for this movement, execute in a thread.
					if bDoCallback:
						t = threading.Thread(target=i.callbackFunc, args = (i,val))
						t.setDaemon(True)
						t.start()
				except:
					pass

				dispatcher.send(signal="movementEvent",key=key, val=val, midiNote=i.midiNote)
				break
			elif( i.linkKey and i.linkKey == key and key ):
				# Execute any other movements that are linked to this movement
				self.executeMovement( i.key, val )
			        self.executeMovement( i.linkedMovement.key, val )
				break

		if self.bThreadStarted == False:
			self.bThreadStarted = True
			t = threading.Thread(target=self.updatePins, args = ())
			t.setDaemon(True)
			t.start()

	def executeGamepad(self,button,val):
		for i in self.all:
				try:
					if button == i.gamepadButton:
						self.executeMovement(i.key,val)
				except:
						i.gamepadButton = -1
			