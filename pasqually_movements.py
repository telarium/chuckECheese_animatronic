import time
from threading import Thread

class Struct():
    key = '' # A keyboard key press assigned to this movement
    outputPin1 = None # First IO pin on the Arduino
    outputPin2 = None # Optional second IO pin (the inverse state of pin 1)
    midiNote = 0 # A MIDI note assigned to this movement to be recorded in a sequencer
    linkKey = None # A keyboard key that binds this movement to another (optional)
    linkedMovement = None # The movement we want to bind to this link (optional)

class Movement:
    all = []

    def __init__(self, GPIO, DIRECTION_OUTPUT):
       self.gpio = GPIO

       self.rightShoulderIn = Struct()
       self.rightShoulderIn.key = 'y'
       self.rightShoulderIn.outputPin1 = 132 # CSI-D0
       self.rightShoulderIn.midiNote = 50
       self.all.append( self.rightShoulderIn )
       
       self.rightShoulderOut = Struct()
       self.rightShoulderOut.key = 'u'
       self.rightShoulderOut.outputPin1 = 133 #CSI-D1
       self.rightShoulderOut.midiNote = 51
       self.rightShoulderOut.linkKey = 'r'
       self.rightShoulderOut.linkedMovement = self.rightShoulderIn
       self.all.append( self.rightShoulderOut )
       
       self.rightArm = Struct()
       self.rightArm.key = 'j'
       self.rightArm.outputPin1 = 134 #CSI-D2
       self.rightArm.outputPin2 = 135 #CSI-D3
       self.rightArm.midiNote = 52
       self.all.append( self.rightArm )
       
       self.leftShoulderOut = Struct()
       self.leftShoulderOut.key = 'i'
       self.leftShoulderOut.outputPin1  = 136 #CSI-D4
       self.leftShoulderOut.midiNote = 53
       self.all.append( self.leftShoulderOut )
       
       self.leftShoulderIn = Struct()
       self.leftShoulderIn.key = 'o'
       self.leftShoulderIn.outputPin1 = 137 #CSI-D5
       self.leftShoulderIn.midiNote = 54
       self.leftShoulderIn.linkKey = 't'
       self.leftShoulderIn.linkedMovement = self.leftShoulderOut
       self.all.append( self.leftShoulderIn )
       
       self.leftArm = Struct()
       self.leftArm.key = 'h'
       self.leftArm.outputPin1 = 138 #CSI-D6
       self.leftArm.outputPin2 = 139 #CSI-D7
       self.leftArm.midiNote = 55
       self.all.append( self.leftArm )

       self.mouth = Struct()
       self.mouth.key = 'x'
       self.mouth.outputPin1 = 99 #LCD-D3
       self.mouth.outputPin2 = 100 #LCD-D4
       self.mouth.midiNote = 56
       self.all.append( self.mouth )
       
       self.mustache = Struct()
       self.mustache.key = 'c'
       self.mustache.outputPin1 = 101 #LCD-D5
       self.mustache.midiNote = 57
       self.mustache.linkKey = 'z'
       self.mustache.linkedMovement = self.mouth
       self.all.append( self.mustache )
       
       self.eyesLeft = Struct()
       self.eyesLeft.key = 'q'
       self.eyesLeft.outputPin1 = 102 #LCD-D6
       self.eyesLeft.midiNote = 58
       self.all.append( self.eyesLeft )
       
       self.eyesRight = Struct()
       self.eyesRight.key = 'e'
       self.eyesRight.outputPin1 = 103 #LCD-D7
       self.eyesRight.midiNote = 59
       self.all.append( self.eyesRight )
       
       self.eyesBlink = Struct()
       self.eyesBlink.key = 'v'
       self.eyesBlink.outputPin1 = 106 #LCD-D10
       self.eyesBlink.outputPin2 = 107 #LCD-D11
       self.eyesBlink.midiNote = 60
       self.all.append( self.eyesBlink )
       
       self.bodyLeanUpDown = Struct()
       self.bodyLeanUpDown.key = 's'
       self.bodyLeanUpDown.outputPin1 = 108 #LCD-D12
       self.bodyLeanUpDown.outputPin2 = 109 #LCD-D13
       self.bodyLeanUpDown.midiNote = 61
       self.all.append( self.bodyLeanUpDown )
       
       self.neckLeft = Struct()
       self.neckLeft.key = 'a'
       self.neckLeft.outputPin1 = 110 #LCD-D14
       self.neckLeft.midiNote = 62
       self.all.append( self.neckLeft )
       
       self.neckRight = Struct()
       self.neckRight.key = 'd'
       self.neckRight.outputPin1 = 111 #LCD-D15
       self.neckRight.midiNote = 63
       self.all.append( self.neckRight )
       
       self.headUpDown = Struct()
       self.headUpDown.key = 'w'
       self.headUpDown.outputPin1 = 114 #LCD-D18
       self.headUpDown.outputPin2 = 115 #LCD-D19
       self.headUpDown.midiNote = 64
       self.all.append( self.headUpDown )

       #LCD-D20,21,22?

       for i in self.all:
	  i.outputPin1 = GPIO(i.outputPin1,DIRECTION_OUTPUT)
	  i.outputPin1.open()
	  i.outputPin1.set_high()
          if( i.outputPin2 ):
		i.outputPin2 = GPIO(i.outputPin2,DIRECTION_OUTPUT)
		i.outputPin2.open()
		i.outputPin2.set_high()


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
			i.outputPin1.set_high()
		else:
			i.outputPin1.set_low()

		if( i.outputPin2 ):
			if( val == 1 ):
				i.outputPin2.set_high()
			else:
				i.outputPin1.set_low()				
                break
            elif( i.linkKey and i.linkKey == key and key ):
	        self.executeMovement( i.linkedMovement.key, val )
                break

