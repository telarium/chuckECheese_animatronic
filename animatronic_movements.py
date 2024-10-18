import time
import threading

# Valve1  -> 0x20, GP0	-> Eye right
# Valve2  -> 0x21, GP4	-> Eye left
# Valve3  -> 0x20, GP1	-> Eyelid Up
# Valve4  -> 0x21, GP5	-> Eyelid down
# Valve5  -> 0x20, GP2	-> Mustache
# Valve6  -> NONE
# Valve7  -> 0x20, GP3	-> Neck down
# Valve8  -> 0x21, GP6	-> Neck up
# Valve9  -> 0x20, GP4	-> Left shoulder out
# Valve10 -> 0x21, GP7	-> Left shoulder in
# Valve11 -> 0x20, GP5	-> --unused--
# Valve12 -> 0x23, GP0	-> --unused--
# Valve13 -> 0x20, GP6	-> Left arm down
# Valve14 -> 0x23, GP1	-> Left arm up
# Valve15 -> 0x20, GP7	-> Mouth open
# Valve16 -> 0x23, GP2	-> Mouth closed
# Valve17 -> 0x21, GP0	-> Neck/torso left
# Valve18 -> 0x23, GP3	-> Neck/torso right
# Valve19 -> 0x21, GP1	-> Lean forward
# Valve20 -> 0x23, GP4	-> Lean Backward
# Valve21 -> 0x21, GP2	-> Right arm down
# Valve22 -> 0x23, GP5	-> Right arm up
# Valve23 -> 0x21, GP3	-> Right shoulder in
# Valve24 -> 0x23, GP6	-> Right shoulder out
# Valve25 -> NONE (COM 24v)
# Valve26 -> 0x23, GP7	-> --unused--

class Struct():
	key = '' # A keyboard key press assigned to this movement
	description = "" # A handy description of this movement
	outputPin1 = [] # Index 0 is the I2C address for the GPIO expander, index 1 is the assigned pin on the GPIO expander
	outputPin2 = [] # Optional second IO pin array, usually the inverse state of outputPin1 (see comment above)
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
				self.setPin(pin,1,movement)
				time.sleep(0.04)
				# Don't disable output if user has pressed another eye key
				if self.eyesRight.keyIsPressed != True and self.eyesLeft.keyIsPressed != True:
					self.setPin(pin,0,movement)

	# Callback function for eyes to attempt a half-blink... or, as I call it, the "stink eye"
	def onEyeBlinkHalf(self, movement, val):
		try:
			blinked = self.eyesBlinkHalf.bBlinked
		except:
			self.eyesBlinkHalf.bBlinked = False

		self.setPin(self.eyesBlinkFull.outputPin2, 0, self.eyesBlinkFull)
		if val == 1 and self.eyesBlinkHalf.bBlinked != True:
			self.eyesBlinkHalf.bBlinked = True
			time.sleep(0.020)
			self.setPin(self.eyesBlinkHalf.outputPin1, 0, self.eyesBlinkFull)
		elif val == 1 and self.eyesBlinkHalf.bBlinked == True:
			self.eyesBlinkHalf.bBlinked = False
			self.setPin(self.eyesBlinkHalf.outputPin1, 0, self.eyesBlinkFull)
			self.executeMovement(self.eyesBlinkFull.key,0)
			time.sleep(0.025)
			self.setPin(self.eyesBlinkFull.outputPin2, 0, self.eyesBlinkFull)

	def __init__(self, gpio):
		self.gpio = gpio
		self.bThreadStarted = False	

		# Define all of our movements here.
		self.rightShoulder = Struct()
		self.rightShoulder.description = "Shoulder R"
		self.rightShoulder.key = 'o'
		self.rightShoulder.outputPin2 = [0x23, 6] # Shoulder out
		self.rightShoulder.outputPin1 = [0x21, 3] # Shoulder in
		#self.rightShoulder.outputPin2MaxTime = 0.5
		#self.rightShoulder.outputPin1MaxTime = 60*10
		self.rightShoulder.midiNote = 50
		self.all.append( self.rightShoulder )

		self.rightArm = Struct()
		self.rightArm.key = 'l'
		self.rightArm.description = "Elbow R"
		self.rightArm.outputPin2 = [0x23, 5] # Arm up
		self.rightArm.outputPin1 = [0x21, 2] # Arm down
		self.rightArm.outputPin2MaxTime = -1
		#self.rightArm.outputPin1MaxTime = 0.75
		self.rightArm.midiNote = 52
		self.all.append( self.rightArm )
       
		self.leftShoulder = Struct()
		self.leftShoulder.description = "Shoulder L"
		self.leftShoulder.key = 'u'
		self.leftShoulder.outputPin2 = [0x20, 4] # Shoulder out
		self.leftShoulder.outputPin1 = [0x21, 7] # Shoulder in
		#self.leftShoulder.outputPin2MaxTime = 0.5
		#self.leftShoulder.outputPin1MaxTime = 60*10
		#self.leftShoulder.linkKey = 'i'
		#self.leftShoulder.linkedMovement = self.rightShoulder
		self.leftShoulder.midiNote = 53
		self.all.append( self.leftShoulder )
       
		self.leftArm = Struct()
		self.leftArm.description = "Elbow L"
		self.leftArm.key = 'j'
		self.leftArm.outputPin2 = [0x23, 1] # Arm up
		self.leftArm.outputPin1 = [0x20, 6] # Arm down
		#self.leftArm.outputPin2MaxTime = -1
		#self.leftArm.outputPin1MaxTime = 0.75
		#self.leftArm.linkKey = 'k'
		#self.leftArm.linkedMovement = self.rightArm
		self.leftArm.midiNote = 55
		self.all.append( self.leftArm )

		self.mouth = Struct()
		self.mouth.description = "Mouth"
		self.mouth.key = 'x'
		self.mouth.outputPin1 = [0x20, 7] # Mouth open
		self.mouth.outputPin2 = [0x23, 2] # Mouth close
		#self.mouth.outputPin1MaxTime = 0.75
		#self.mouth.outputPin2MaxTime = 0.75
		self.mouth.midiNote = 56
		self.all.append( self.mouth )
       
		self.mustache = Struct()
		self.mustache.description = "Mustache"
		self.mustache.key = 'z'
		self.mustache.outputPin1 = [0x20, 2]
		#self.mustache.outputPin1MaxTime = 60*5
		self.mustache.midiNote = 57
		#self.mustache.linkKey = 'c'
		self.mustache.linkedMovement = self.mouth
		self.all.append( self.mustache )
       
		self.eyesLeft = Struct()
		self.eyesLeft.description = "Eyes L"
		self.eyesLeft.key = 'q'
		self.eyesLeft.outputPin1 = [0x21, 4]
		#self.eyesLeft.outputPin1MaxTime = 60*10
		self.eyesLeft.midiNote = 58
		self.eyesLeft.callbackFunc = self.onEyeMove
		self.all.append( self.eyesLeft )
       
		self.eyesRight = Struct()
		self.eyesRight.description = "Eyes R"
		self.eyesRight.key = 'e'
		self.eyesRight.outputPin1 = [0x20, 0]
		#self.eyesRight.outputPin1MaxTime = 60*10
		self.eyesRight.midiNote = 59
		self.eyesRight.callbackFunc = self.onEyeMove
		self.all.append( self.eyesRight )
       
		self.eyesBlinkFull = Struct()
		self.eyesBlinkFull.description = "Eyes Blink"
		self.eyesBlinkFull.key = 'w'
		self.eyesBlinkFull.outputPin1 = [0x21, 5] # Eyes close
		self.eyesBlinkFull.outputPin2 = [0x20, 1] # Eyes open
		#self.eyesBlinkFull.outputPin1MaxTime = 0.25
		#self.eyesBlinkFull.outputPin2MaxTime = 0.25
		self.eyesBlinkFull.midiNote = 60
		self.all.append( self.eyesBlinkFull )
       
		self.bodyLeanUp = Struct()
		self.bodyLeanUp.description = "Lean Forward"
		self.bodyLeanUp.key = 'm'
		self.bodyLeanUp.outputPin1 = [0x21, 1] # Lean forward
		self.bodyLeanUp.outputInverted = True
		self.bodyLeanUp.midiNote = 62
		self.all.append( self.bodyLeanUp ) 

		self.bodyLeanDown = Struct()
		self.bodyLeanDown.description = "Lean Back"
		self.bodyLeanDown.key = 'n'
		self.bodyLeanDown.outputPin1 = [0x23, 4] # Lean backward
		#self.bodyLeanDown.outputPin1MaxTime = 2
		self.bodyLeanDown.midiNote = 63
		self.all.append( self.bodyLeanDown )
       
		self.neckLeft = Struct()
		self.neckLeft.description = "Head L"
		self.neckLeft.key = 'a'
		self.neckLeft.outputPin1 = [0x21, 0]
		#self.neckLeft.outputPin1MaxTime = 0.8
		self.neckLeft.midiNote = 64
		self.all.append( self.neckLeft )
       
		self.neckRight = Struct()
		self.neckRight.description = "Head R"
		self.neckRight.key = 'd'
		self.neckRight.outputPin1 = [0x23, 3]
		#self.neckRight.outputPin1MaxTime = 0.8
		self.neckRight.midiNote = 65
		self.all.append( self.neckRight )
       
		self.headUpDown = Struct()
		self.headUpDown.description = "Head Down"
		self.headUpDown.key = 's'
		self.headUpDown.outputPin1 = [0x20, 3] # Head down
		self.headUpDown.outputPin2 = [0x21, 6] # Head up
		#self.headUpDown.outputPin1MaxTime = 60*60
		self.headUpDown.midiNote = 66
		self.all.append( self.headUpDown )

		for i in self.all:
			i.keyIsPressed = False
			val = 0
			try:
				if i.outputInverted == True:
					val = 1
			except:
				i.outputInverted = False

			i.pin1Time = 0

			self.setPin(i.outputPin1, val, i)
			if( i.outputPin2 ):
				i.pin2Time = 0
				self.setPin(i.outputPin2, 1-val, i)

	# Fromat MIDI notes into a string to pass to the HTML front end
	# This way, javascript key presses can control MIDI events directly
	def getMidiNotes( self ):
		fullString = ""
		midiNote1 = None
		midiNote2 = None

		for i in self.all:
			fullString += i.key
			midiNote1 = str(i.midiNote)
			if( len(midiNote1 ) < 2 ):
				midiNote1 = "0" + midiNote1
		
			fullString+=midiNote1+"00"

			if( i.linkKey ):
				fullString+=","+i.linkKey+midiNote1
				midiNote2 = str(i.linkedMovement.midiNote)
				if( len(midiNote2) < 2 ):
					midiNote2 = "0" + midiNote2

				fullString+=midiNote2

			fullString+=","
			
		return fullString

	def getKeyboardKeys(self):
		keys = []
		for i in self.all:
			keys.append(i.key)

		return keys

	# Monitor state of IO and disable any that have been left on past the maximum allowed time.
	def updatePins(self):
		while self:
			time.sleep(0.1)
			for i in self.all:
				if i.outputPin1MaxTime > -1 and i.pin1Time > 0:
					i.pin1Time-=0.1
					if i.pin1Time <= 0:
						i.pin1Time = 0
						self.setPin(i.outputPin1, 0, i)
				
				if i.outputPin2MaxTime > -1 and i.pin2Time > 0:
					i.pin2Time-=0.1
					if i.pin2Time <= 0:
						i.pin2Time = 0
						self.setPin(i.outputPin2, 0, i)

	# Set the GPIO pin state. When using the MCP23008 GPIO expander, index 0 of the pin value is the I2C address of the GPIO bank... 
	# ...and index 1 is the assigned pin on the MCP23008. For example, "0x20 pin 1"
	def setPin( self, pin, val, movement ):
			self.gpio.set_pin_from_address(pin[0], pin[1], val)

	def executeMovement( self, key, val ):
		bDoCallback = False
		for i in self.all:
			if( i.key == key and key ):
				if val == 1 and i.keyIsPressed == False:
					i.keyIsPressed = True
					bDoCallback = True
				elif val == 0 and i.keyIsPressed == True:
					i.keyIsPressed = False
					bDoCallback = True

				if bDoCallback:

					if i.outputInverted == True:
						val = 1 - val

					print(f"{i.description}: {val}")

					self.setPin(i.outputPin1, val, i)

					if( val == 1 ):
						i.pin1Time = i.outputPin1MaxTime
					else:
						i.pin1Time = 0

					if( i.outputPin2 ):
						self.setPin(i.outputPin2, 1-val, i)
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

		return bDoCallback
			