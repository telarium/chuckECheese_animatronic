function sendKey(key, num){
	$.ajax({
            type: "GET",
            url: "/onKeyPress/",
            contentType: "application/json; charset=utf-8",
            data: { keyVal: key, val: num }
        });
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
	getMidiNotes()
	down[charCode] = null
	sendKey( String.fromCharCode(charCode), 0 )
}

function getMidiNotes(){
        $.ajax({
            url: '/getMidiNotes',
            data: $('form').serialize(),
            type: 'POST',
            success: function(response) {
                console.log(response);
            },
        });
}

getMidiNotes()

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
