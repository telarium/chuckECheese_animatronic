// pasqually.js

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

var showList = [];
socket.on('showListLoaded', function(data) {
    showList = ["-- Select A Show! --"]; // Clear the current list
    for (var i = 0; i < data.length; i++) {
        showList.push(data[i]);
    }

    // Populate the dropdown
    const dropdown = document.querySelector('select[name="Show List"]');
    dropdown.innerHTML = ''; // Clear existing options

    showList.forEach(item => {
        const option = document.createElement('option');
        option.value = item; // Use the value from the showList
        option.textContent = item; // Display the value in the dropdown
        dropdown.appendChild(option);
    });

    console.log('Dropdown updated:', showList);
});

document.getElementById('playButton').addEventListener('click', function() {
    const dropdown = document.getElementById('showListDropdown');
    const selectedShow = dropdown.value; // Get the selected dropdown value
    
    if (selectedShow) {
        if (dropdown.selectedIndex === 0) {
            alert('Mama mia! Please select a show first!');
        } else {
            socket.emit('showPlay',selectedShow);
            console.log(`Playing show: ${selectedShow}`);
        }
    } else {
        console.warn('No show selected.');
    }
});

document.getElementById('pauseButton').addEventListener('click', function() {
    socket.emit('showPause');
    console.log(`Pausing show`);
});

document.getElementById('stopButton').addEventListener('click', function() {
    socket.emit('showStop');
    console.log(`Stopping show`);
});

var movements = [];
socket.on('movementInfo', function(data){
    // Data is a two dimensional array. First index is the assigned keyboard key, second is the assigned MIDI note
    for (var i = 0; i < data.length; i++) {
        var movement = {
            key: data[i][0],
            midiNote: data[i][1],
            lastTime: 0
        };
        movements.push(movement);
    }
});

socket.on('gamepadKeyEvent', function(data){
    // Data is a two dimensional array. First index is the assigned keyboard key, second is the value
    key = data[0];
    val = data[1];
    for (var i = 0; i < movements.length; i++) {
        if (movements[i].key == key.toLowerCase()) {
            sendKey(key,val,false,false)
        }
    }
});

function sendKey(key, num, bBroadcast, bMuteMidi) {
    for (var i = 0; i < movements.length; i++) {
        if (!movements[i].lastTime) {
            movements[i].lastTime = 0;
        }
        if (movements[i].key == key.toLowerCase() && (window.performance.now() - movements[i].lastTime > 1)) {
            if( bBroadcast) // Do we broadcast this event over the web socket?
            {
                socket.emit('onKeyPress', {keyVal: key, val: num});
            }
            if( !bMuteMidi )
            {
                playMIDINote(movements[i].midiNote, num);
            }
            movements[i].lastTime = window.performance.now();
            break;  // Stop further iterations once the key event is sent
        }
    }
}

var down = new Set(); // Use a Set to store pressed keys

function doKeyDown(event) {
    var charCode = (typeof event.which == "number") ? event.which : event.keyCode;
    if (!down.has(charCode)) { // first press
        sendKey(String.fromCharCode(charCode), 1, true, false);
        down.add(charCode); // Add key to the Set
    }
}

function doKeyUp(event) {
    var charCode = (typeof event.which == "number") ? event.which : event.keyCode;
    if (down.has(charCode)) { // only send if key was previously pressed
        sendKey(String.fromCharCode(charCode), 0, true, false);
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
    console.log("No MIDI support in your browser. Try using HTTPS");
}

// Object to keep track of the state (on/off) of each MIDI note
var noteState = {};

function playMIDINote(midiNote, val) {
    if (midiOutputPort) {
        var velocity = 0x40; // Default release velocity

        // Determine the intended state (on or off)
        var isOn = val === 1;
        var newState = isOn ? 'on' : 'off';

        // Check if the state has changed
        if (noteState[midiNote] === newState) {
            return; // No change, skip sending the MIDI message
        }

        // Update the noteState object with the new state
        noteState[midiNote] = newState;

        // Prepare the MIDI message
        var status = isOn ? 0x90 : 0x80; // Note-On (0x90) or Note-Off (0x80)
        velocity = isOn ? 0x7f : velocity; // Full velocity for Note-On

        var output = midiAccess.outputs.get(midiOutputPort);
        if (output) {
            console.log(`Sending MIDI ${newState.toUpperCase()} event for note ${midiNote} to port: ${output.name} (ID: ${output.id})`);
            output.send([status, midiNote, velocity]);
        } else {
            console.warn(`MIDI output port with ID ${midiOutputPort} not found.`);
        }
    } else {
        console.warn("No MIDI output port selected.");
    }
}


function onMIDIMessage(event) {
    var data = event.data; // MIDI data [statusByte, dataByte1, dataByte2]
    var statusByte = data[0];
    var noteNumber = data[1]; // MIDI note number
    var velocity = data[2];   // Note velocity

    var command = statusByte >> 4;
    var portName = event.target.name; // Name of the MIDI port

    // When using LoopBe30, MIDI ports with "01" in the name are reserved only for output to a MIDI sequencer.
    if (portName.startsWith("01. ")) {
        //console.warn(`Ignoring MIDI event from unexpected port: ${portName}`);
        return;
    }

    // Find any keyboard value that is assigned to this MIDI note
    for (var i = 0; i < movements.length; i++) {
        if (movements[i].midiNote == noteNumber)
        {
            if (command === 9 && velocity > 0) {
                // Note On message
                sendKey(movements[i].key, 1, true, true);
            } else if (command === 8 || (command === 9 && velocity === 0)) {
                // Note Off message
                sendKey(movements[i].key, 0, true, true);
            }
        }
    }
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

/* ======= New Code for Mirrored and Retro Modes ======= */

// Function to perform flip animation
function performFlipAnimation() {
    const mainContent = document.getElementById('main');
    mainContent.classList.add('flip-animation');

    // Remove the class after animation completes to allow re-triggering
    mainContent.addEventListener('animationend', function handler() {
        mainContent.classList.remove('flip-animation');
        mainContent.removeEventListener('animationend', handler);
    });
}

// Add event listeners for Mirrored Mode and Retro Mode checkboxes
document.addEventListener('DOMContentLoaded', function() {
    const mirroredModeCheckbox = document.getElementById('mirroredModeCheckbox');
    const retroModeCheckbox = document.getElementById('retroModeCheckbox');

    if (mirroredModeCheckbox) {
        // Initialize Mirrored Mode based on saved preference
        const mirroredModeEnabled = localStorage.getItem('mirroredModeEnabled') === 'true';
        mirroredModeCheckbox.checked = mirroredModeEnabled;

        if (mirroredModeEnabled) {
            // Optionally, perform initial flip or apply styles if needed
            // Since the flip is transient, no persistent changes are applied
            // If you wish to have a persistent mirrored state, additional styles would be required
        }

        // Add event listener for Mirrored Mode checkbox
        mirroredModeCheckbox.addEventListener('change', function() {
            performFlipAnimation();

            // Save preference to localStorage
            localStorage.setItem('mirroredModeEnabled', this.checked);
            socket.emit('onMirroredMode', this.checked);
        });
    } else {
        console.warn('Mirrored Mode Checkbox not found!');
    }

    if (retroModeCheckbox) {
        // Initialize Retro Mode based on saved preference
        const retroModeEnabled = localStorage.getItem('retroModeEnabled') === 'true';
        retroModeCheckbox.checked = retroModeEnabled;

        if (retroModeEnabled) {
            const mainContent = document.getElementById('main');
            mainContent.classList.add('retro-mode-active');
        }

        // Add event listener for Retro Mode checkbox
        retroModeCheckbox.addEventListener('change', function() {
            const mainContent = document.getElementById('main');
            if (this.checked) {
                mainContent.classList.add('retro-mode-active');
                
            } else {
                mainContent.classList.remove('retro-mode-active');
            }
            socket.emit('onRetroMode', this.checked);

            // Save preference to localStorage
            localStorage.setItem('retroModeEnabled', this.checked);
        });
    } else {
        console.warn('Retro Mode Checkbox not found!');
    }
});

/* ======= End of Mirrored and Retro Modes Code ======= */
