import time
import CHIP_IO.GPIO as GPIO
from threading import Thread

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
	linkKey = None # A keyboard key that binds this movement to another (optional)
	linkedMovement = None # The movement we want to bind to this link (optional)

class Movement:
	all = []

	def __init__(self):

		self.rightShoulderIn = Struct()
		self.rightShoulderIn.key = 'y'
		self.rightShoulderIn.outputPin1 = 'LCD-D11'
		self.rightShoulderIn.midiNote = 50
		self.all.append( self.rightShoulderIn )
       
		self.rightShoulderOut = Struct()
		self.rightShoulderOut.key = 'u'
		self.rightShoulderOut.outputPin1 = 'CSID3'
		self.rightShoulderOut.midiNote = 51
		self.all.append( self.rightShoulderOut )
       
		self.rightArm = Struct()
		self.rightArm.key = 'j'
		self.rightArm.outputPin1 = 'CSID5'
		self.rightArm.outputPin2 = 'LCD-D7'
		self.rightArm.midiNote = 52
		self.all.append( self.rightArm )
       
		self.leftShoulderOut = Struct()
		self.leftShoulderOut.key = 'i'
		self.leftShoulderOut.outputPin1  = 'LCD-D12'
		self.leftShoulderOut.linkKey = 'r'
                self.leftShoulderOut.linkedMovement = self.rightShoulderOut
		self.leftShoulderOut.midiNote = 53
		self.all.append( self.leftShoulderOut )
       
		self.leftShoulderIn = Struct()
		self.leftShoulderIn.key = 'o'
		self.leftShoulderIn.outputPin1 = 'LCD-D21'
		self.leftShoulderIn.midiNote = 54
		self.leftShoulderIn.linkKey = 't'
		self.leftShoulderIn.linkedMovement = self.rightShoulderIn
		self.all.append( self.leftShoulderIn )
       
		self.leftArm = Struct()
		self.leftArm.key = 'h'
		self.leftArm.outputPin1 = 'CSID4'
		self.leftArm.outputPin2 = 'LCD-D6'
		self.leftArm.midiNote = 55
		self.all.append( self.leftArm )

		self.mouth = Struct()
		self.mouth.key = 'x'
		self.mouth.outputPin1 = 'LCD-D4'
		self.mouth.outputPin2 = 'CSID2'
		self.mouth.midiNote = 56
		self.all.append( self.mouth )
       
		self.mustache = Struct()
		self.mustache.key = 'c'
		self.mustache.outputPin1 = 'LCD-D18'
		self.mustache.midiNote = 57
		self.mustache.linkKey = 'z'
		self.mustache.linkedMovement = self.mouth
		self.all.append( self.mustache )
       
		self.eyesLeft = Struct()
		self.eyesLeft.key = 'q'
		self.eyesLeft.outputPin1 = 'LCD-D22'
		self.eyesLeft.midiNote = 58
		self.all.append( self.eyesLeft )
       
		self.eyesRight = Struct()
		self.eyesRight.key = 'e'
		self.eyesRight.outputPin1 = 'LCD-D13'
		self.eyesRight.midiNote = 59
		self.all.append( self.eyesRight )
       
		self.eyesBlink = Struct()
		self.eyesBlink.key = 'v'
		self.eyesBlink.outputPin1 = 'LCD-D15'
		self.eyesBlink.outputPin2 = 'LCD-D20'
		self.eyesBlink.midiNote = 60
		self.all.append( self.eyesBlink )
       
		self.bodyLeanUpDown = Struct()
		self.bodyLeanUpDown.key = 's'
		self.bodyLeanUpDown.outputPin1 = 'LCD-D5'
		self.bodyLeanUpDown.outputPin2 = 'CSID7'
		self.bodyLeanUpDown.midiNote = 61
		self.all.append( self.bodyLeanUpDown )
       
		self.neckLeft = Struct()
		self.neckLeft.key = 'a'
		self.neckLeft.outputPin1 = 'LCD-D3'
		self.neckLeft.midiNote = 62
		self.all.append( self.neckLeft )
       
		self.neckRight = Struct()
		self.neckRight.key = 'd'
		self.neckRight.outputPin1 = 'CSID0'
		self.neckRight.midiNote = 63
		self.all.append( self.neckRight )
       
		self.headUpDown = Struct()
		self.headUpDown.key = 'w'
		self.headUpDown.outputPin1 = 'LCD-D14'
		self.headUpDown.outputPin2 = 'LCD-D19'
		self.headUpDown.midiNote = 64
		self.all.append( self.headUpDown )

		#LCD-D20,21,22?
		GPIO.cleanup()

		for i in self.all:
			GPIO.cleanup(i.outputPin1)
			GPIO.setup(i.outputPin1,GPIO.OUT)
			GPIO.output(i.outputPin1, GPIO.LOW)
			if( i.outputPin2 ):
				GPIO.cleanup(i.outputPin2)
				GPIO.setup(i.outputPin2,GPIO.OUT)
				GPIO.output(i.outputPin2, GPIO.LOW)

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

	def executeMovement( self, key, val ):
		for i in self.all:
	            	if( i.key == key and key ):
				if( val == 1 ):
					GPIO.output(i.outputPin1, 1)
				else:
					GPIO.output(i.outputPin1, 0)

				if( i.outputPin2 ):
					if( val == 1 ):
						GPIO.output(i.outputPin2, 0)
					else:
						GPIO.output(i.outputPin2, 1)
				break
			elif( i.linkKey and i.linkKey == key and key ):
			        self.executeMovement( i.linkedMovement.key, val )
				break
