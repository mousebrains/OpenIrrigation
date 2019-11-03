// Collection of utility functions for use in the OpenIrrigation system

var OI_timeouts = {}; // map of pending timeouts and when they were generated

function OI_clearTimeouts() {
	for(var key in OI_timeouts) {
		clearTimeout(OI_timeouts[key][0]);
	}
	OI_timeouts = {};
} // OI_clearTImeouts()

function OI_timeDown(key, eTime, prevNow) { // Display H:MM from now to eTime in $(key)
	var now = Date.now() / 1000;
	var dt = eTime - now;
	var dt1 = dt + 0.5; // For display purposes
	var hours = Math.floor(dt1 / 3600);
	var mins = Math.floor(dt1 / 60) % 60;
	var msg = hours + ':' + ('00' + mins).slice(-2);
	var resid = 60;
	if (dt <= 120) {
		msg += ':' + ('00' + Math.floor(dt1 % 60)).slice(-2);
		resid = 10; // Count down by 10 second intervals
	}
	$(key).html((dt > 0) ? msg : "");
	if ((dt > 0) && (!(key in OI_timeouts) || (OI_timeouts[key][1] == prevNow))) {
		var dtNext = Math.max(1, dt % resid) * 1000;
		var id = setTimeout(OI_timeDown, dtNext, key, eTime, now);
		OI_timeouts[key] = [id, now];
	} else if ((key in OI_timeouts) && (OI_timeouts[key][1] == prevNow)) {
		delete OI_timeouts[key];
	}
} // OI_timeDown

function OI_timeUpDown(key0, key1, sTime, eTime, offset0, offset1, prevNow) { 
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
	$(key1).html((dt > 0) ? msg : '');
	if ((dt > 0) && (!(key in OI_timeouts) || (OI_timeouts[key][1] == prevNow))) {
		var dtNext = Math.max(1, dt % resid) * 1000;
		var id = setTimeout(OI_timeUpDown, dtNext, 
			key0, key1, sTime, eTime, offset0, offset1, now);
		OI_timeouts[key] = [id, now];
	} else if ((key in OI_timeouts) && (OI_timeouts[key][1] == prevNow)) {
		delete OI_timeouts[key];
	}
} // OI_timeDown
