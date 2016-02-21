function popup() {
	alert("Hello World")
}

function init() {
	var d = new Date()
	//webiopi().callMacro( "setDateAndTime", [d.getFullYear(), d.getMonth()+1, d.getDate(), d.getHours(), d.getMinutes(), d.getSeconds()] );
}

function sendKey(key, num){
	webiopi().callMacro("sendWebKey", [String.fromCharCode( key ).toLowerCase(),num] );
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
