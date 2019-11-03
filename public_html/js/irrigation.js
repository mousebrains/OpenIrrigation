// Collection of utility functions for use in the OpenIrrigation system

var OI_timeouts = {}; // map of pending timeouts

function OI_clearTimeouts() {
	for(var key in OI_timeouts) {
		clearTimeout(OI_timeouts[key]);
	}
} // OI_clearTImeouts()

function OI_timeDown(key, eTime) { // Display H:MM from now to eTime in $(key)
	var dt = eTime - (Date.now() / 1000);
	var dt1 = dt + 0.5; // For display purposes
	var hours = Math.floor(dt1 / 3600);
	var mins = Math.floor(dt1 / 60) % 60;
	var msg = hours + ':' + ('00' + mins).slice(-2);
	var resid = 60;
	if (dt <= 120) {
		msg += ':' + ('00' + Math.floor(dt1 % 60)).slice(-2);
		resid = 10; // Count down by 10 second intervals
	}
	if (dt > 0) {
		$(key).html(msg);
		var dtNext = Math.max(1, dt % resid);
		// console.log('key=' + key + ' dt=' + dt + ' nxt=' + dtNext);
		OI_timeouts[key] = setTimeout(OI_timeDown, dtNext * 1000, key, eTime);
	} else if (key in OI_timeouts) {
		$(key).html('');
		delete OI_timeouts[key];
	}
} // OI_timeDown

function OI_timeUpDown(key0, key1, sTime, eTime, offset0, offset1) { 
	// Count time up for key0/sTime and down for key1/eTime
	var now = Date.now() / 1000;
	var dt = now - sTime;
	var dt1 = dt + offset0 + 0.5; // For display purposes
	var hours = Math.floor(dt1 / 3600);
	var mins = Math.floor(dt1 / 60) % 60;
	$(key0).html(hours + ':' + ('00' + mins).slice(-2));

	dt = eTime - now;
	dt1 = dt + offset1 + 0.5; // For display purposes
	hours = Math.floor(dt1 / 3600);
	mins = Math.floor(dt1 / 60) % 60;
	msg = hours + ':' + ('00' + mins).slice(-2);
	resid = 60;
	if (dt <= 120) {
		msg += ':' + ('00' + Math.floor(dt1 % 60)).slice(-2);
		resid = 10; // Count down by 10 second intervals
	}
	if (dt > 0) {
		$(key1).html(msg);
		var dtNext = Math.max(1, dt % resid);
		// console.log('key=' + key1 + ' dt=' + dt + ' nxt=' + dtNext);
		OI_timeouts[key1] = setTimeout(OI_timeUpDown, dtNext * 1000, 
			key0, key1, sTime, eTime, offset0, offset1);
	} else if (key1 in OI_timeouts) {
		$(key1).html('');
		delete OI_timeouts[key1];
	}
} // OI_timeDown
