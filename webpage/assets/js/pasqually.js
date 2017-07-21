var socket = io.connect('http://' + document.domain + ':' + location.port);

socket.on('connect', function() {
	socket.emit('onConnect', {data: 'I\'m connected!'});
});

socket.on('systemInfo', function(msg){
    //Response test
    newMsg = '<p>CPU: ' + msg.cpu + '%, RAM: ' + msg.ram + '%</p>';
    document.getElementById("sysInfo").innerHTML = newMsg;
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
		findMidiNote(String.fromCharCode(charCode),1)
	}
}
    
document.onkeyup = doKeyUp;
function doKeyUp(event){
	var charCode = (typeof event.which == "number") ? event.which : event.keyCode
	down[charCode] = null;
	sendKey( String.fromCharCode(charCode), 0 )
	down[charCode] = null
	sendKey( String.fromCharCode(charCode), 0 )
	findMidiNote(String.fromCharCode(charCode),0)
}

function getMidiNotes(){

}

getMidiNotes()

function findMidiNote( key, val ) {
	key = key.toLowerCase();
	noteMessage1 = null;
	noteMessage2 = null;
	for (i = 0; i < midiNotes.length; i++) {
		if( midiNotes[i].key == key ) {
			if( val == 1 ) {
				val = 0x90;
			} else {
				val = 0x80;
			}
			noteMessage1 = [val, midiNotes[i].midiNote1, 0x7f];
			console.log(noteMessage1 )
		}
	}	
}

// request MIDI access
if (navigator.requestMIDIAccess) {
    navigator.requestMIDIAccess({
        sysex: false
    }).then(onMIDISuccess, onMIDIFailure);
} else {
    alert("No MIDI support in your browser.");
}

// midi functions
function onMIDISuccess(midiAccess) {
    // when we get a succesful response, run this code
    console.log('MIDI Access Object', midiAccess);
}

function onMIDIFailure(e) {
    // when we get a failed response, run this code
    console.log("No access to MIDI devices or your browser doesn't support WebMIDI API. Please use WebMIDIAPIShim " + e);
}

