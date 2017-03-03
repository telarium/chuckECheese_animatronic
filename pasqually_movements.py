import time
import CHIP_IO.GPIO as GPIO
from threading import Thread

# Valve1  -> LCD_D22 -> Eye right
# Valve2  -> LCD_D13 -> Eye left
# Valve3  -> LCD_D20 -> Eyelid Up
# Valve4  -> LCD_D15 -> Eyelid down
# Valve5  -> LCD_D18 -> Mustache
# Valve6  -> NONE
# Valve7  -> LCD_D14 -> Neck down
# Valve8  -> LCD_D19 -> Neck up
# Valve9  -> LCD_D12 -> Left shoulder out
# Valve10 -> LCD_D21 -> Left shoulder in
# Valve11 -> LCD_D10 -> 
# Valve12 -> CSI_D6  -> 
# Valve13 -> LCD_D6  -> Left arm down
# Valve14 -> CSI_D4  -> Left arm up
# Valve15 -> LCD_D4  -> Mouth open
# Valve16 -> CSI_D2  -> Mouth closed
# Valve17 -> LCD_D3  -> Torso left
# Valve18 -> CSI_D0  -> Torso right
# Valve19 -> LCD_D5  -> Lean forward
# Valve20 -> CSI_D7  -> Lean Backward
# Valve21 -> LCD_D7  -> Right arm down
# Valve22 -> CSI_D5  -> Right arm up
# Valve23 -> LCD_D11 -> Right shoulder in
# Valve24 -> CSI_D3  -> Right shoulder out
# Valve25 -> NONE (24v)
# Valve26 -> CSI_D1  -> 

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
		self.rightShoulderIn.outputPin1 = 'CSID0'
		self.rightShoulderIn.midiNote = 50
		self.all.append( self.rightShoulderIn )
       
		self.rightShoulderOut = Struct()
		self.rightShoulderOut.key = 'u'
		self.rightShoulderOut.outputPin1 = 'CSID1'
		self.rightShoulderOut.midiNote = 51
		self.rightShoulderOut.linkKey = 'r'
		self.rightShoulderOut.linkedMovement = self.rightShoulderIn
		self.all.append( self.rightShoulderOut )
       
		self.rightArm = Struct()
		self.rightArm.key = 'j'
		self.rightArm.outputPin1 = 'CSID2'
		self.rightArm.outputPin2 = 'CSID3'
		self.rightArm.midiNote = 52
		self.all.append( self.rightArm )
       
		self.leftShoulderOut = Struct()
		self.leftShoulderOut.key = 'i'
		self.leftShoulderOut.outputPin1  = 'CSID4'
		self.leftShoulderOut.midiNote = 53
		self.all.append( self.leftShoulderOut )
       
		self.leftShoulderIn = Struct()
		self.leftShoulderIn.key = 'o'
		self.leftShoulderIn.outputPin1 = 'CSID5'
		self.leftShoulderIn.midiNote = 54
		self.leftShoulderIn.linkKey = 't'
		self.leftShoulderIn.linkedMovement = self.leftShoulderOut
		self.all.append( self.leftShoulderIn )
       
		self.leftArm = Struct()
		self.leftArm.key = 'h'
		self.leftArm.outputPin1 = 'CSID6'
		self.leftArm.outputPin2 = 'CSID7'
		self.leftArm.midiNote = 55
		self.all.append( self.leftArm )

		self.mouth = Struct()
		self.mouth.key = 'x'
		self.mouth.outputPin1 = 'LCD-D3'
		self.mouth.outputPin2 = 'LCD-D4'
		self.mouth.midiNote = 56
		self.all.append( self.mouth )
       
		self.mustache = Struct()
		self.mustache.key = 'c'
		self.mustache.outputPin1 = 'LCD-D5'
		self.mustache.midiNote = 57
		self.mustache.linkKey = 'z'
		self.mustache.linkedMovement = self.mouth
		self.all.append( self.mustache )
       
		self.eyesLeft = Struct()
		self.eyesLeft.key = 'q'
		self.eyesLeft.outputPin1 = 'LCD-D6'
		self.eyesLeft.midiNote = 58
		self.all.append( self.eyesLeft )
       
		self.eyesRight = Struct()
		self.eyesRight.key = 'e'
		self.eyesRight.outputPin1 = 'LCD-D7'
		self.eyesRight.midiNote = 59
		self.all.append( self.eyesRight )
       
		self.eyesBlink = Struct()
		self.eyesBlink.key = 'v'
		self.eyesBlink.outputPin1 = 'LCD-D10'
		self.eyesBlink.outputPin2 = 'LCD-D11'
		self.eyesBlink.midiNote = 60
		self.all.append( self.eyesBlink )
       
		self.bodyLeanUpDown = Struct()
		self.bodyLeanUpDown.key = 's'
		self.bodyLeanUpDown.outputPin1 = 'LCD-D12'
		self.bodyLeanUpDown.outputPin2 = 'LCD-D13'
		self.bodyLeanUpDown.midiNote = 61
		self.all.append( self.bodyLeanUpDown )
       
		self.neckLeft = Struct()
		self.neckLeft.key = 'a'
		self.neckLeft.outputPin1 = 'LCD-D14'
		self.neckLeft.midiNote = 62
		self.all.append( self.neckLeft )
       
		self.neckRight = Struct()
		self.neckRight.key = 'd'
		self.neckRight.outputPin1 = 'LCD-D15'
		self.neckRight.midiNote = 63
		self.all.append( self.neckRight )
       
		self.headUpDown = Struct()
		self.headUpDown.key = 'w'
		self.headUpDown.outputPin1 = 'LCD-D18'
		self.headUpDown.outputPin2 = 'LCD-D22'
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
		name1 = "LCD-D20"
		name2 = "LCD-D15"
		GPIO.setup(name1,GPIO.OUT)
		GPIO.setup(name2,GPIO.OUT)
		GPIO.output(name1, 0)
		GPIO.output(name2, 0)
		if val == 1:
			GPIO.output(name1,1)
			print("ON!" )
		else:
			GPIO.output(name2,1)
			print("OFF!" )

		'''
		for i in self.all:
            	if( i.key == key and key ):
			if( val == 1 ):
				GPIO.output(i.outputPin1, 1)
			else:
				GPIO.output(i.outputPin1, 0)

			if( i.outputPin2 ):
				if( val == 1 ):
					GPIO.output(i.outputPin2, 1)
				else:
					GPIO.output(i.outputPin2, 0)
			break
		elif( i.linkKey and i.linkKey == key and key ):
		        self.executeMovement( i.linkedMovement.key, val )
			break
		'''

