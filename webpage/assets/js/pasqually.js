var socket = io.connect('http://' + document.domain + ':' + location.port);
var midiInputs = null
var midiOutputs = null

socket.on('connect', function() {
	socket.emit('onConnect', {data: 'I\'m connected!'});
});

socket.on('systemInfo', function(msg){
    //Response test
    newMsg = '<p>CPU: ' + msg.cpu + '%, RAM: ' + msg.ram + '%</p>';
    document.getElementById("sysInfo").innerHTML = newMsg;
});

socket.on('movement', function(movement){
    playMIDINote(movement.midiNote,movement.val)
});

var midiNotes = []

function sendKey(key, num){
	socket.emit('onKeyPress', {keyVal: key, val: num});
}
    
var down = {}; // store down keys to prevent repeated keypresses
document.onkeydown = doKeyDown;

function doKeyDown(event){
	var charCode = (typeof event.which == "number") ? event.which : event.keyCode
	if (down[charCode] == null) { // first press
		sendKey( String.fromCharCode(charCode), 1 )
		down[charCode] = true; // record that the key's down
	}
}
    
document.onkeyup = doKeyUp;
function doKeyUp(event){
	var charCode = (typeof event.which == "number") ? event.which : event.keyCode
	down[charCode] = null;
	sendKey( String.fromCharCode(charCode), 0 )
	down[charCode] = null
	sendKey( String.fromCharCode(charCode), 0 )
}

// request MIDI access
if (navigator.requestMIDIAccess) {
    navigator.requestMIDIAccess({
        sysex: false
    }).then(onMIDISuccess, onMIDIFailure);
} else {
    alert("No MIDI support in your browser.");
}

function playMIDINote(midiNote,val) {
	if (val == 1) {
		val = 144 // Typical note-on MIDI value
	} else {
		val = 128 // Typical note-off MIDI value
	}
	velocity = 128
	for(i = 0; i < midiOutputs.length; i++){
		midiOutputs[i].send( [val, midiNote, velocity])
	}
}

// midi functions
function onMIDISuccess(midiAccess) {
    // when we get a succesful response, run this code
    console.log('MIDI Access Object', midiAccess);
    midiInputs = midiAccess.inputs.values();
    midiOutputs = midiAccess.outputs.values()
}

function onMIDIFailure(e) {
    // when we get a failed response, run this code
    console.log("No access to MIDI devices or your browser doesn't support WebMIDI API. Please use WebMIDIAPIShim " + e);
}

