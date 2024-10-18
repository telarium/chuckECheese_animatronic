// Determine the protocol (ws:// or wss://) based on the current page protocol
const protocol = (window.location.protocol === 'https:') ? 'wss://' : 'ws://';
const socketUrl = protocol + document.domain + ':' + location.port;

// Connect to the WebSocket
var socket = io.connect(socketUrl);

socket.on('connect', function() {
    socket.emit('onConnect', {data: 'I\'m connected!'});
});

socket.on('systemInfo', function(msg){
    const newMsg = '<p>CPU: ' + msg.cpu + '%<br>RAM: ' + msg.ram + '%<br>Disk Usage: ' + msg.disk + '%<br>Temp: ' + msg.temperature + '°C<br>Wifi Strength: ' + msg.wifi_signal + '%</p>';
    document.getElementById("sysInfo").innerHTML = newMsg;
});

socket.on('wifiScan', function(data){
    console.log(data.networks);
});

var movements = [];

socket.on('movementInfo', function(data){
    for (var i = 0; i < data.length; i++) {
        var movement = {
            key: data[i],
            lastTime: 0
        };
        movements.push(movement);
    }
});

function sendKey(key, num) {
    for (var i = 0; i < movements.length; i++) {
        if (!movements[i].lastTime) {
            movements[i].lastTime = 0;
        }
        if (movements[i].key == key.toLowerCase() && (window.performance.now() - movements[i].lastTime > 1)) {
            socket.emit('onKeyPress', {keyVal: key, val: num});
            playMIDINote(60, num);
            movements[i].lastTime = window.performance.now();
            break;  // Stop further iterations once the key event is sent
        }
    }
}

var down = new Set(); // Use a Set to store pressed keys

function doKeyDown(event) {
    var charCode = (typeof event.which == "number") ? event.which : event.keyCode;
    if (!down.has(charCode)) { // first press
        sendKey(String.fromCharCode(charCode), 1);
        down.add(charCode); // Add key to the Set
    }
}

function doKeyUp(event) {
    var charCode = (typeof event.which == "number") ? event.which : event.keyCode;
    if (down.has(charCode)) { // only send if key was previously pressed
        sendKey(String.fromCharCode(charCode), 0);
        down.delete(charCode); // Remove key from the Set
    }
}

document.onkeydown = doKeyDown;
document.onkeyup = doKeyUp;

var midiAccess = null
var midiOutputPort = null

// request MIDI access
if (navigator.requestMIDIAccess) {
    navigator.requestMIDIAccess({
        sysex: false
    }).then(onMIDISuccess, onMIDIFailure);
} else {
    alert("No MIDI support in your browser.");
}

function playMIDINote(midiNote,val) {
	if (midiOutputPort) {
		var velocity = 0x40 // Release velocity
		if (val == 1) {
			val = 0x90 // Typical note-on MIDI value
			velocity = 0x7f // Full velocity
		} else {
			val = 0x80 // Typical note-off MIDI value
		}
		var output = midiAccess.outputs.get(midiOutputPort);
		output.send([val, midiNote, velocity]) ;
	}
}

function onMIDIMessage( event ) {
	//
}

function onMIDISuccess(midi) {
    // When we successfully initiate the MIDI interface...
	midiAccess = midi
    midiOutputs = midiAccess.outputs.values()
    console.log("init:",midiOutputs)
    for (var output = midiOutputs.next(); output && !output.done; output = midiOutputs.next()) {
		console.log('output',output)
		midiOutputPort = output.value.id
	}
	midiAccess.inputs.forEach( function(entry) {entry.onmidimessage = onMIDIMessage;});
}

function onMIDIFailure(e) {
    console.log("No access to MIDI devices or your browser doesn't support WebMIDI API. Please use WebMIDIAPIShim " + e);
}

var bGamepadActive = false;
var gamepadState = [];
var updateInterval;
    
function findGamepad() {
    return "getGamepads" in navigator;
}

function evalGamepadState() {
    var gp = navigator.getGamepads()[0];
    for (var i = 0; i < gp.buttons.length; i++) {
        if (gamepadState[i] != gp.buttons[i].pressed) {
            gamepadState[i] = gp.buttons[i].pressed;
            var num = gp.buttons[i].pressed ? 1 : 0;
            socket.emit('onGamepadButton', {buttonVal: i + 1, val: num});
        }    
    }
}
    
$(document).ready(function() {
    if (findGamepad()) {
        $(window).on("gamepadconnected", function() {
            bGamepadActive = true;
            console.log("Gamepad detected!");
            updateInterval = window.setInterval(evalGamepadState, 75);
        });

        $(window).on("gamepaddisconnected", function() {
            console.log("Gamepad disconnected!");
            window.clearInterval(updateInterval);
        });

        // Setup an interval for Chrome
        var checkGP = window.setInterval(function() {
            if (navigator.getGamepads()[0]) {
                if (!bGamepadActive) $(window).trigger("gamepadconnected");
                window.clearInterval(checkGP);
            }
        }, 500);
    }
});
