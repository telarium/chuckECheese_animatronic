function popup() {
	alert("Hello World")
}

function init() {
	var d = new Date()
	//webiopi().callMacro( "setDateAndTime", [d.getFullYear(), d.getMonth()+1, d.getDate(), d.getHours(), d.getMinutes(), d.getSeconds()] );
}

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
		sendKey( charCode, 1 )
		down[charCode] = true; // record that the key's down
	}
}
    
document.onkeyup = doKeyUp;
function doKeyUp(event){
	var charCode = (typeof event.which == "number") ? event.which : event.keyCode
	down[charCode] = null;
	sendKey( charCode, 0 )
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
