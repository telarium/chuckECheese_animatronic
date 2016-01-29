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

    def __init__(self, gpio):
       self.gpio = gpio

       self.rightShoulderIn = Struct()
       self.rightShoulderIn.key = 'y'
       self.rightShoulderIn.outputPin1 = 36
       self.rightShoulderIn.midiNote = 50
       self.all.append( self.rightShoulderIn )
       
       self.rightShoulderOut = Struct()
       self.rightShoulderOut.key = 'u'
       self.rightShoulderOut.outputPin1 = 42
       self.rightShoulderOut.midiNote = 51
       self.rightShoulderOut.linkKey = 'r'
       self.rightShoulderOut.linkedMovement = self.rightShoulderIn
       self.all.append( self.rightShoulderOut )
       
       self.rightArm = Struct()
       self.rightArm.key = 'j'
       self.rightArm.outputPin1 = 32
       self.rightArm.outputPin2 = 30
       self.rightArm.midiNote = 52
       self.all.append( self.rightArm )
       
       self.leftShoulderOut = Struct()
       self.leftShoulderOut.key = 'i'
       self.leftShoulderOut.outputPin1 = 22
       self.leftShoulderOut.midiNote = 53
       self.all.append( self.leftShoulderOut )
       
       self.leftShoulderIn = Struct()
       self.leftShoulderIn.key = 'o'
       self.leftShoulderIn.outputPin1 = 10
       self.leftShoulderIn.midiNote = 54
       self.leftShoulderIn.linkKey = 't'
       self.leftShoulderIn.linkedMovement = self.leftShoulderOut
       self.all.append( self.leftShoulderIn )
       
       self.leftArm = Struct()
       self.leftArm.key = 'h'
       self.leftArm.outputPin1 = 52
       self.leftArm.outputPin2 = 11
       self.leftArm.midiNote = 55
       self.all.append( self.leftArm )

       self.mouth = Struct()
       self.mouth.key = 'x'
       self.mouth.outputPin1 = 6
       self.mouth.outputPin2 = 28
       self.mouth.midiNote = 56
       self.all.append( self.mouth )
       
       self.mustache = Struct()
       self.mustache.key = 'c'
       self.mustache.outputPin1 = 26
       self.mustache.midiNote = 57
       self.mustache.linkKey = 'z'
       self.mustache.linkedMovement = self.mouth
       self.all.append( self.mustache )
       
       self.eyesLeft = Struct()
       self.eyesLeft.key = 'q'
       self.eyesLeft.outputPin1 = 9
       self.eyesLeft.midiNote = 58
       self.all.append( self.eyesLeft )
       
       self.eyesRight = Struct()
       self.eyesRight.key = 'e'
       self.eyesRight.outputPin1 = 24
       self.eyesRight.midiNote = 59
       self.all.append( self.eyesRight )
       
       self.eyesBlink = Struct()
       self.eyesBlink.key = 'v'
       self.eyesBlink.outputPin1 = 34
       self.eyesBlink.outputPin2 = 40
       self.eyesBlink.midiNote = 60
       self.all.append( self.eyesBlink )
       
       self.bodyLeanUpDown = Struct()
       self.bodyLeanUpDown.key = 's'
       self.bodyLeanUpDown.outputPin1 = 50
       self.bodyLeanUpDown.outputPin2 = 12
       self.bodyLeanUpDown.midiNote = 61
       self.all.append( self.bodyLeanUpDown )
       
       self.neckLeft = Struct()
       self.neckLeft.key = 'a'
       self.neckLeft.outputPin1 = 46
       self.neckLeft.midiNote = 62
       self.all.append( self.neckLeft )
       
       self.neckRight = Struct()
       self.neckRight.key = 'd'
       self.neckRight.outputPin1 = 38
       self.neckRight.midiNote = 63
       self.all.append( self.neckRight )
       
       self.headUpDown = Struct()
       self.headUpDown.key = 'w'
       self.headUpDown.outputPin1 = 48
       self.headUpDown.outputPin2 = 8
       self.headUpDown.midiNote = 64
       self.all.append( self.headUpDown )

       for i in self.all:
          gpio.setup( i.outputPin1 , "out" )
          gpio.set( i.outputPin1, 1 )
          if( i.outputPin2 ):
            gpio.setup( i.outputPin2 , "out" )
            gpio.set( i.outputPin1, 0 )
    
    def executeMovement( self, key, val, serialFunc ):
        for i in self.all:
            if( i.key == key and key and val ):
                # Stuff should go here
                break
            elif( i.linkKey and i.linkKey == key and key and val ):
                serialFunc( i.key + str(val) )
                serialFunc( i.linkedMovement.key + str(val) )
                break
