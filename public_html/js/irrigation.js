// Collection of utility functions for use in the OpenIrrigation system

let OI_timeouts = {}; // map of pending timeouts and when they were generated

function escapeHTML(s) {
	if (s === null || s === undefined) return '';
	return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function OI_clearTimeouts() {
	for (const key in OI_timeouts) {
		clearTimeout(OI_timeouts[key][0]);
	}
	OI_timeouts = {};
} // OI_clearTImeouts()

function OI_timeDown(key, eTime, prevNow) { // Display H:MM from now to eTime in $(key)
	const now = Date.now() / 1000;
	const dt = eTime - now;
	const dt1 = dt + 0.5; // For display purposes
	const hours = Math.floor(dt1 / 3600);
	const mins = Math.floor(dt1 / 60) % 60;
	let msg = hours + ':' + ('00' + mins).slice(-2);
	let resid = 60;
	if (dt <= 120) {
		msg += ':' + ('00' + Math.floor(dt1 % 60)).slice(-2);
		resid = 10; // Count down by 10 second intervals
	}
	$(key).html((dt > 0) ? msg : "");
	if ((dt > 0) && (!(key in OI_timeouts) || (OI_timeouts[key][1] === prevNow))) {
		const dtNext = Math.max(1, dt % resid) * 1000;
		const id = setTimeout(OI_timeDown, dtNext, key, eTime, now);
		OI_timeouts[key] = [id, now];
	} else if ((key in OI_timeouts) && (OI_timeouts[key][1] === prevNow)) {
		delete OI_timeouts[key];
	}
} // OI_timeDown

function OI_timeUpDown(key0, key1, sTime, eTime, offset0, offset1, prevNow) {
	// Count time up for key0/sTime and down for key1/eTime
	const now = Date.now() / 1000;
	let dt = now - sTime;
	let dt1 = dt + offset0 + 0.5; // For display purposes
	let hours = Math.floor(dt1 / 3600);
	let mins = Math.floor(dt1 / 60) % 60;
	$(key0).html(hours + ':' + ('00' + mins).slice(-2));

	dt = eTime - now;
	dt1 = dt + offset1 + 0.5; // For display purposes
	hours = Math.floor(dt1 / 3600);
	mins = Math.floor(dt1 / 60) % 60;
	let msg = hours + ':' + ('00' + mins).slice(-2);
	let resid = 60;
	if (dt <= 120) {
		msg += ':' + ('00' + Math.floor(dt1 % 60)).slice(-2);
		resid = 10; // Count down by 10 second intervals
	}
	$(key1).html((dt > 0) ? msg : '');
	if ((dt > 0) && (!(key1 in OI_timeouts) || (OI_timeouts[key1][1] === prevNow))) {
		const dtNext = Math.max(1, dt % resid) * 1000;
		const id = setTimeout(OI_timeUpDown, dtNext,
			key0, key1, sTime, eTime, offset0, offset1, now);
		OI_timeouts[key1] = [id, now];
	} else if ((key1 in OI_timeouts) && (OI_timeouts[key1][1] === prevNow)) {
		delete OI_timeouts[key1];
	}
} // OI_timeUpDown

function OI_processSubmit(event, url, formData) { // Submission of form data to url
	// Form submission and alert on failure
	console.log(url);
	console.log(formData);
	$.ajax({
		type: 'POST', // Post the form data
		url: url, // Script to process this form
		data: formData, // form data to be posted
		dataType: 'json', // returned data format
		encode: true
	}).done(function(data){
		console.log(data);
		if (('success' in data) && !data['success']) {
			alert(data['message']);
		}
	});
	event.preventDefault();
}

function OI_processForm(event) { // argument to .submit({'url':...}, OI_processForm)
	OI_processSubmit(event, event.data['url'], $(this).serialize());
}
