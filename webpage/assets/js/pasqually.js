// pasqually.js

// Determine the protocol (ws:// or wss://) based on the current page protocol
const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const socketUrl = `${protocol}${document.domain}:${location.port}`;

// Connect to the WebSocket
const socket = io.connect(socketUrl);

socket.on('connect', () => {
    socket.emit('onConnect', { data: "I'm connected!" });
});

/**
 * Truncate a string to a specified maximum length, adding ellipsis if truncated.
 * @param {string} str - The string to truncate.
 * @param {number} maxLength - The maximum allowed length of the string.
 * @returns {string} - The truncated string with ellipsis if needed.
 */
function truncateString(str, maxLength) {
    return str.length > maxLength ? `${str.slice(0, maxLength - 3)}...` : str;
}

/**
 * Detect if the current device is a mobile device (Android/iOS).
 * @returns {boolean} - True if mobile device, else false.
 */
function isMobileDevice() {
    const ua = navigator.userAgent.toLowerCase();
    return /android|iphone|ipad|ipod/.test(ua);
}

// Consolidated DOMContentLoaded Event Listener
document.addEventListener('DOMContentLoaded', () => {
    handleMobileKeypadVisibility();
    setupWifiPopupEvents();
    setupModeCheckboxes();
    setupSubmitTTS();
    setupShowControlButtons();
    setupHotspotLink(); // Initialize hotspot link functionality
    setupPasswordEnterKey(); // Initialize Enter key functionality for password input
});

// Handle visibility of keypad images on mobile devices
function handleMobileKeypadVisibility() {
    if (!isMobileDevice()) return;

    const keypadImages = ['images/keypad-l.png', 'images/keypad-r.png'];
    keypadImages.forEach(src => {
        const img = document.querySelector(`img[src="${src}"]`);
        if (img) {
            const container = img.closest('.box');
            if (container) container.style.display = 'none';
        }
    });
}

let bHotspotActive = false;

// Update system information displayed on the page
socket.on('systemInfo', (msg) => {
    bHotspotActive = msg.hotspot_status;
    if (bHotspotActive === true) {
        setHotspotLinkText("Deactivate Hotspot");
    } else {
        setHotspotLinkText("Activate Hotspot");
    }
    msg.wifi_ssid = truncateString(msg.wifi_ssid, 20);

    const newMsg = `
        <p>
            Wifi: <a href="#" id="wifiSSIDLink">${msg.wifi_ssid}</a><i>(${msg.wifi_signal}%)</i><br>
            Pressure: ${msg.psi} PSI<br>
            CPU: ${msg.cpu}%<br>
            RAM: ${msg.ram}%<br>
            Disk Usage: ${msg.disk}%<br>
            Temp: ${msg.temperature}°C<br>
        </p>
    `;
    const sysInfoElement = document.getElementById("sysInfo");
    if (sysInfoElement) {
        sysInfoElement.innerHTML = newMsg;

        // Add event listener to the WiFi SSID link
        const wifiLink = document.getElementById('wifiSSIDLink');
        if (wifiLink) {
            wifiLink.addEventListener('click', (e) => {
                e.preventDefault();
                openWifiPopup();
            });
        }
    } else {
        console.warn('System Info element not found!');
    }
});

/**
 * Update the voice command status displayed on the page.
 * @param {string} id - The status identifier.
 * @param {string} value - The value associated with the status.
 */
function updateVoiceCommandStatus(id, value) {
    let statusText = "";

    switch (id) {
        case "idle":
            statusText = "Waiting for 'Hey chef'...";
            break;
        case "wakeWord":
            statusText = "Listening...";
            break;
        case "command":
            statusText = `Executing command '${value}'`;
            break;
        case "chatGPTSend":
            statusText = `Heard '${value}'`;
            break;
        case "deepseekSend":
            statusText = `Heard '${value}'`;
            break;
        case "transcribing":
            statusText = "Transcribing...";
            break;
        case "chatGPTReceive":
            statusText = "Responding...";
            populateTTSInput(value);
            break;
        case "deepseekReceive":
            statusText = "Responding...";
            populateTTSInput(value);
            break;
        case "micNotFound":
            statusText = "No microphone detected";
            break;
        case "error":
            statusText = "Disabled!";
            break;
        case "ttsSubmitted":
            statusText = "Processing...";
            break;
        case "ttsComplete":
            statusText = "Waiting...";
            const submitButton = document.getElementById('submitTTSButton');
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.classList.remove('disabled');
            }
            break;
        default:
            statusText = "Unknown status";
    }

    const statusElement = document.getElementById('voiceCommandStatus');
    if (statusElement) {
        statusElement.innerHTML = `Voice Command Status: <span>${statusText}</span>`;
    } else {
        console.warn('Voice Command Status element not found!');
    }
}

socket.on('voiceCommandUpdate', ({ id, value }) => updateVoiceCommandStatus(id, value));

// Handle show list loading
let showList = [];
socket.on('showListLoaded', (data) => {
    showList = ["-- Select A Show! --", ...data];

    const dropdown = document.querySelector('select[name="Show List"]');
    if (dropdown) {
        dropdown.innerHTML = ''; // Clear existing options

        showList.forEach(item => {
            const option = document.createElement('option');
            option.value = item;
            option.textContent = item;
            dropdown.appendChild(option);
        });
    } else {
        console.warn('Show List dropdown not found!');
    }
});

// Handle play, pause, and stop buttons for shows
function setupShowControlButtons() {
    const playButton = document.getElementById('playButton');
    const pauseButton = document.getElementById('pauseButton');
    const stopButton = document.getElementById('stopButton');

    if (playButton) {
        playButton.addEventListener('click', () => {
            const dropdown = document.getElementById('showListDropdown');
            const selectedShow = dropdown ? dropdown.value : null;

            if (selectedShow) {
                if (dropdown.selectedIndex === 0) {
                    alert('Mama mia! Please select a show first!');
                } else {
                    socket.emit('showPlay', selectedShow);
                    console.log(`Playing show: ${selectedShow}`);
                }
            } else {
                console.warn('No show selected.');
            }
        });
    } else {
        console.warn('Play Button not found!');
    }

    if (pauseButton) {
        pauseButton.addEventListener('click', () => {
            socket.emit('showPause');
            console.log('Pausing show');
        });
    } else {
        console.warn('Pause Button not found!');
    }

    if (stopButton) {
        stopButton.addEventListener('click', () => {
            socket.emit('showStop');
            console.log('Stopping show');
        });
    } else {
        console.warn('Stop Button not found!');
    }
}

// Handle WiFi scans
let wifiSSIDs = [];
socket.on('wifiScan', (data) => {
    wifiSSIDs = data;
});

// Handle movement information (related to MIDI and key presses)
let movements = [];
socket.on('movementInfo', (data) => {
    // Data is a two-dimensional array. First index is assigned keyboard key, second is assigned MIDI note
    movements = data.map(item => ({
        key: item[0].toLowerCase(),
        midiNote: item[1],
        lastTime: 0
    }));
});

/**
 * Send a key event.
 * @param {string} key - The key pressed.
 * @param {number} value - The value associated with the key event (e.g., 1 for keydown, 0 for keyup).
 * @param {boolean} broadcast - Whether to broadcast this key event.
 * @param {boolean} muteMidi - Whether to mute MIDI playback for this key event.
 */
function sendKey(key, value, broadcast, muteMidi) {
    const currentTime = window.performance.now();

    for (const movement of movements) {
        if (movement.key === key.toLowerCase() && (currentTime - movement.lastTime > 1)) {
            if (broadcast) {
                socket.emit('onKeyPress', { keyVal: key, val: value });
            }
            if (!muteMidi) {
                playMIDINote(movement.midiNote, value);
            }
            movement.lastTime = currentTime;
            break;
        }
    }
}

// Handle keyboard events
const down = new Set();

function doKeyDown(event) {
    // Prevent handling if focus is on the TTS input or WiFi password input
    if (event.target.id === 'ttsInput' || event.target.id === 'wifiPassword') {
        return;
    }

    const charCode = event.which || event.keyCode;
    if (!down.has(charCode)) { // first press
        sendKey(String.fromCharCode(charCode), 1, true, false);
        down.add(charCode); // Add key to the Set
    }
}

function doKeyUp(event) {
    // Prevent handling if focus is on the TTS input or WiFi password input
    if (event.target.id === 'ttsInput' || event.target.id === 'wifiPassword') {
        return;
    }

    const charCode = event.which || event.keyCode;
    if (down.has(charCode)) { // only send if key was previously pressed
        sendKey(String.fromCharCode(charCode), 0, true, false);
        down.delete(charCode); // Remove key from the Set
    }
}

document.addEventListener('keydown', doKeyDown);
document.addEventListener('keyup', doKeyUp);

// MIDI Handling
let midiAccess = null;
let midiOutputPort = null;

// Request MIDI access
if (navigator.requestMIDIAccess) {
    navigator.requestMIDIAccess({ sysex: false })
        .then(onMIDISuccess)
        .catch(onMIDIFailure);
} else {
    console.log("No MIDI support in your browser. Try using HTTPS");
}

// Object to keep track of the state (on/off) of each MIDI note
const noteState = {};

/**
 * Play or stop a MIDI note.
 * @param {number} midiNote - The MIDI note number.
 * @param {number} val - 1 to play, 0 to stop.
 */
function playMIDINote(midiNote, val) {
    if (midiOutputPort && midiAccess) {
        const isOn = val === 1;
        const newState = isOn ? 'on' : 'off';

        // Check if the state has changed
        if (noteState[midiNote] === newState) {
            return; // No change, skip
        }
        noteState[midiNote] = newState;

        // Prepare the MIDI message
        const status = isOn ? 0x90 : 0x80; // Note-On (0x90) or Note-Off (0x80)
        const velocity = isOn ? 0x7F : 0x40; // Full velocity for Note-On, default release velocity for Note-Off

        const output = midiAccess.outputs.get(midiOutputPort);
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

/**
 * Handle incoming MIDI messages.
 * @param {MIDIMessageEvent} event - The MIDI message event.
 */
function onMIDIMessage(event) {
    const [statusByte, noteNumber, velocity] = event.data;
    const command = statusByte >> 4;
    const portName = event.target.name; // Name of the MIDI port

    // When using LoopBe30, MIDI ports with "01" in the name are reserved only for output
    if (portName.startsWith("01. ")) {
        return;
    }

    // Find any keyboard value that is assigned to this MIDI note
    movements.forEach(movement => {
        if (movement.midiNote === noteNumber) {
            if (command === 9 && velocity > 0) {
                // Note On
                sendKey(movement.key, 1, true, true);
            } else if (command === 8 || (command === 9 && velocity === 0)) {
                // Note Off
                sendKey(movement.key, 0, true, true);
            }
        }
    });
}

/**
 * Handle successful MIDI access.
 * @param {MIDIAccess} midi - The MIDI access object.
 */
function onMIDISuccess(midi) {
    midiAccess = midi;
    const outputs = Array.from(midiAccess.outputs.values());
    console.log("Available MIDI Outputs:", outputs);

    if (outputs.length > 0) {
        midiOutputPort = outputs[0].id; // Select the first available MIDI output port
        console.log(`Selected MIDI Output: ${outputs[0].name} (ID: ${outputs[0].id})`);
    } else {
        console.warn('No MIDI output ports available.');
    }

    midiAccess.inputs.forEach(input => {
        input.onmidimessage = onMIDIMessage;
    });
}

/**
 * Handle MIDI access failure.
 * @param {Error} e - The error object.
 */
function onMIDIFailure(e) {
    console.log("No access to MIDI devices or your browser doesn't support WebMIDI API. Please use WebMIDIAPIShim", e);
}

// Mode Handling (Mirrored & Retro)
function setupModeCheckboxes() {
    const mirroredModeCheckbox = document.getElementById('mirroredModeCheckbox');
    const retroModeCheckbox = document.getElementById('retroModeCheckbox');

    if (mirroredModeCheckbox) {
        // Initialize Mirrored Mode based on saved preference
        const mirroredModeEnabled = localStorage.getItem('mirroredModeEnabled') === 'true';
        mirroredModeCheckbox.checked = mirroredModeEnabled;

        // Add event listener for Mirrored Mode checkbox
        mirroredModeCheckbox.addEventListener('change', function () {
            // Toggle the mirroredModeEnabled boolean
            bMirroredModeEnabled = this.checked;
            // Save preference to localStorage
            localStorage.setItem('mirroredModeEnabled', this.checked);
            socket.emit('onMirroredMode', this.checked);

            // Perform actions based on the new state
            if (this.checked) {
                performFlipAnimation();
            } else {
                reverseFlipAnimation(); // Define this function if needed
            }

            console.log(`Mirrored Mode is now ${this.checked ? 'Enabled' : 'Disabled'}`);
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
            if (mainContent) {
                mainContent.classList.add('retro-mode-active');
            }
        }

        // Add event listener for Retro Mode checkbox
        retroModeCheckbox.addEventListener('change', function () {
            const mainContent = document.getElementById('main');
            if (mainContent) {
                if (this.checked) {
                    mainContent.classList.add('retro-mode-active');
                } else {
                    mainContent.classList.remove('retro-mode-active');
                }
                socket.emit('onRetroMode', this.checked);

                // Save preference to localStorage
                localStorage.setItem('retroModeEnabled', this.checked);
            } else {
                console.warn('Main content element not found!');
            }
        });
    } else {
        console.warn('Retro Mode Checkbox not found!');
    }
}

/**
 * Perform flip animation on the main content.
 */
function performFlipAnimation() {
    const mainContent = document.getElementById('main');
    if (!mainContent) {
        console.warn('Main content element not found!');
        return;
    }

    mainContent.classList.add('flip-animation');

    // Remove the class after animation completes to allow re-triggering
    const removeAnimation = () => {
        mainContent.classList.remove('flip-animation');
        mainContent.removeEventListener('animationend', removeAnimation);
    };

    mainContent.addEventListener('animationend', removeAnimation);
}

/**
 * Reverse the flip animation on the main content.
 * @note: You need to define this function based on your animation requirements.
 */
function reverseFlipAnimation() {
    const mainContent = document.getElementById('main');
    if (mainContent) {
        // If you have a specific reverse animation, trigger it here.
        // For example, toggling a class or manipulating styles.
        // This is a placeholder for your reverse animation logic.
        console.log('Reverse flip animation triggered.');
    } else {
        console.warn('Main content element not found!');
    }
}

// Submit TTS Handling
function setupSubmitTTS() {
    const submitButton = document.getElementById('submitTTSButton');
    const ttsInput = document.getElementById('ttsInput');

    if (submitButton) {
        submitButton.addEventListener('click', submitTTS);
    } else {
        console.warn('Submit TTS Button not found!');
    }

    if (ttsInput) {
        ttsInput.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                submitTTS();
            }
        });
    } else {
        console.warn('TTS Input field not found!');
    }
}

/**
 * Submit the TTS input to the backend.
 */
function submitTTS() {
    const inputField = document.getElementById('ttsInput');
    const submitButton = document.getElementById('submitTTSButton'); // Get the Submit button
    const inputText = inputField ? inputField.value.trim() : '';

    if (inputText) {
        console.log(`Submitted TTS Text: ${inputText}`);
        // Disable the Submit button to prevent multiple submissions
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.classList.add('disabled');
        }

        socket.emit('onWebTTSSubmit', inputText);
    } else {
        console.warn('No text entered for TTS submission.');
    }

    // Clear the input field after submission
    if (inputField) {
        inputField.value = '';
    }
}

/**
 * Populate the TTS input box with a given string.
 * @param {string} text - The text to populate in the TTS input.
 */
function populateTTSInput(text) {
    const inputField = document.getElementById('ttsInput');
    if (inputField) {
        inputField.value = text; // Replace any existing text
        console.log(`Populated TTS Input with: ${text}`);
    } else {
        console.warn('TTS Input field not found!');
    }
}

// WiFi Popup Handling
function setupWifiPopupEvents() {
    const closePopupButton = document.getElementById('closeWifiPopup');
    const connectButton = document.getElementById('connectWifiButton');
    const popupOverlay = document.getElementById('wifiPopup');

    // Close popup when close button is clicked
    if (closePopupButton) {
        closePopupButton.addEventListener('click', closeWifiPopup);
    } else {
        console.warn('Close WiFi Popup button not found!');
    }

    // Handle Connect button click
    if (connectButton) {
        connectButton.addEventListener('click', () => {
            const passwordInput = document.getElementById('wifiPassword');
            const password = passwordInput ? passwordInput.value.trim() : '';

            if (selectedSSID && password) {
                connectToWifi(selectedSSID, password);
                closeWifiPopup();
            } else {
                alert('Please select a WiFi network and enter the password.');
            }
        });
    } else {
        console.warn('Connect WiFi Button not found!');
    }

    // Optional: Close popup when clicking outside the popup content
    if (popupOverlay) {
        popupOverlay.addEventListener('click', (e) => {
            if (e.target === popupOverlay) {
                closeWifiPopup();
            }
        });
    } else {
        console.warn('WiFi Popup overlay not found!');
    }
}

/**
 * Open the WiFi selection popup.
 */
function openWifiPopup() {
    populateWifiList(); // Populate the list before showing
    const popup = document.getElementById('wifiPopup');
    if (popup) {
        popup.style.display = 'flex';
    } else {
        console.warn('WiFi Popup element not found!');
    }
}

/**
 * Close the WiFi selection popup.
 */
function closeWifiPopup() {
    const popup = document.getElementById('wifiPopup');
    if (popup) {
        popup.style.display = 'none';
    } else {
        console.warn('WiFi Popup element not found!');
    }
}

/**
 * Populate the WiFi networks list in the popup.
 */
function populateWifiList() {
    const wifiListDiv = document.getElementById('wifiList');
    if (!wifiListDiv) {
        console.warn('WiFi List container not found!');
        return;
    }

    wifiListDiv.innerHTML = ''; // Clear existing list

    if (wifiSSIDs.length === 0) {
        wifiListDiv.innerHTML = '<p style="color: #fff; text-align: center;">No WiFi networks found.</p>';
        return;
    }

    wifiSSIDs.forEach(ap => {
        const wifiItem = document.createElement('div');
        wifiItem.classList.add('wifi-item');
        wifiItem.dataset.ssid = ap.ssid;
        wifiItem.innerHTML = `
            <span>${ap.ssid}</span>
            <span>${ap.signal_strength}%</span>
        `;
        wifiItem.addEventListener('click', () => selectWifi(ap.ssid));
        wifiListDiv.appendChild(wifiItem);
    });
}

let selectedSSID = null;

/**
 * Handle WiFi network selection.
 * @param {string} ssid - The SSID of the selected WiFi network.
 */
function selectWifi(ssid) {
    selectedSSID = ssid;
    const wifiItems = document.querySelectorAll('.wifi-item');
    wifiItems.forEach(item => {
        item.style.backgroundColor = item.dataset.ssid === ssid ? 'rgba(255, 255, 255, 0.2)' : '';
    });
}

/**
 * Connect to the selected WiFi network with the provided password.
 * @param {string} ssid - The SSID of the WiFi network.
 * @param {string} password - The password for the WiFi network.
 */
function connectToWifi(ssid, password) {
    socket.emit('onConnectToWifi', { ssid, password });
    console.log(`Connecting to WiFi SSID: ${ssid}`);
    alert('Attempting to connect to WiFi network. Please wait...');
}

// Second DOMContentLoaded Listener Removed
// Removed the duplicate DOMContentLoaded listener to prevent multiple event listeners

/**
 * Sets the text of the hotspot hyperlink.
 * @param {string} text - The text to display for the hotspot link.
 */
function setHotspotLinkText(text) {
    const hotspotLink = document.getElementById('hotspotLink');
    if (hotspotLink) {
        hotspotLink.textContent = text;
    } else {
        console.warn('Hotspot Link element not found!');
    }
}

/**
 * Handles the hotspot setup when the hyperlink is clicked.
 */
function setHotspot() {
    // Placeholder for hotspot setup logic
    bHotspotActive = !bHotspotActive;

    socket.emit('onSetHotspot', bHotspotActive);

    if (bHotspotActive === true) {
        alert("Hotspot activating...");
    } else {
        alert("Hotspot deactivating. Attempting to reconnect to WiFi...");
    }

    // Optionally, update the hotspot link text based on the new state
    if (bHotspotActive) {
        setHotspotLinkText("Deactivate Hotspot");
    } else {
        setHotspotLinkText("Activate Hotspot");
    }
}

/**
 * Initializes the event listener for the hotspot hyperlink.
 */
function setupHotspotLink() {
    const hotspotLink = document.getElementById('hotspotLink');
    if (hotspotLink) {
        hotspotLink.addEventListener('click', (e) => {
            e.preventDefault(); // Prevent default hyperlink behavior
            setHotspot(); // Call the hotspot setup function
            closeWifiPopup(); // Close the WiFi popup
        });
    } else {
        console.warn('Hotspot Link element not found!');
    }
}

/**
 * Initializes the Enter key functionality for the WiFi password input.
 * When Enter is pressed, it triggers the Connect button if conditions are met.
 */
function setupPasswordEnterKey() {
    const wifiPasswordInput = document.getElementById('wifiPassword');
    const connectButton = document.getElementById('connectWifiButton');

    if (wifiPasswordInput && connectButton) {
        wifiPasswordInput.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // Prevent form submission or default behavior

                // Check if a WiFi network is selected and password is entered
                if (selectedSSID && wifiPasswordInput.value.trim() !== '') {
                    connectButton.click(); // Trigger the Connect button click
                } else {
                    alert('Please select a WiFi network and enter the password.');
                }
            }
        });
    } else {
        console.warn('WiFi Password input or Connect button not found!');
    }
}
