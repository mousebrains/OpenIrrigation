// Collection of utility functions for use in the OpenIrrigation system

let OI_timeouts = {}; // map of pending timeouts and when they were generated

$.ajaxPrefilter((options) => {
	const token = document.getElementById('oi-csrf')?.dataset.token;
	if (token && !options.crossDomain) {
		options.headers = {...options.headers, 'X-CSRF-Token': token};
	}
});

function escapeHTML(s) {
	if (s === null || s === undefined) {return '';}
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
	let msg = `${hours}:${('00' + mins).slice(-2)}`;
	let resid = 60;
	if (dt <= 120) {
		msg += `:${('00' + Math.floor(dt1 % 60)).slice(-2)}`;
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
	$(key0).html(`${hours}:${('00' + mins).slice(-2)}`);

	dt = eTime - now;
	dt1 = dt + offset1 + 0.5; // For display purposes
	hours = Math.floor(dt1 / 3600);
	mins = Math.floor(dt1 / 60) % 60;
	let msg = `${hours}:${('00' + mins).slice(-2)}`;
	let resid = 60;
	if (dt <= 120) {
		msg += `:${('00' + Math.floor(dt1 % 60)).slice(-2)}`;
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

function OI_toast(message, isError) {
	const toast = document.createElement('div');
	toast.className = `oi-toast${isError ? ' oi-toast-error' : ''}`;
	toast.textContent = message;
	document.body.appendChild(toast);
	toast.offsetHeight; // Trigger reflow for animation
	toast.classList.add('oi-toast-show');
	setTimeout(() => {
		toast.classList.remove('oi-toast-show');
		setTimeout(() => { toast.remove(); }, 300);
	}, 4000);
}

function OI_connectSSE(url, onMessage) {
	const statusEl = document.getElementById('sse-status');
	let source = null;
	let closed = false;
	let retryTimer = null;
	let backoff = 0; // ms before our own reconnect; doubles up to a minute
	let lost = false; // toast once per outage, not once per failed retry

	function attach() {
		if (closed) {return;}
		clearTimeout(retryTimer);
		retryTimer = null;
		const es = new EventSource(url);
		source = es;
		es.onopen = () => {
			backoff = 0;
			if (statusEl) {statusEl.textContent = '';}
		};
		es.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				if (data.error) {
					OI_toast(data.error, true);
				} else {
					lost = false;
				}
			} catch {
				// Not JSON or parse error — pass through
			}
			onMessage(event);
		};
		es.onerror = () => {
			if (statusEl) {statusEl.textContent = 'Connection lost';}
			if (!lost) {
				lost = true;
				OI_toast('SSE connection lost — retrying', true);
			}
			// After a dropped stream EventSource retries by itself
			// (CONNECTING), but an HTTP error such as nginx's 502 or 504
			// closes it for good (CLOSED): then reconnect ourselves.
			if (es.readyState === EventSource.CLOSED && source === es && !retryTimer && !closed) {
				backoff = Math.min(backoff ? 2 * backoff : 2000, 60000);
				retryTimer = setTimeout(attach, backoff);
			}
		};
	}

	attach();

	// iOS Safari kills idle SSE during backgrounding/WiFi power-save and its
	// auto-reconnect is unreliable. On foreground, force a fresh connection
	// rather than waiting for the browser to figure out the socket is dead.
	document.addEventListener('visibilitychange', () => {
		if (closed) {return;}
		if (document.visibilityState === 'visible' &&
		    source && source.readyState !== EventSource.OPEN) {
			try {source.close();} catch {/* ignore */}
			attach();
		}
	});

	return {
		close() {
			closed = true;
			clearTimeout(retryTimer);
			if (source) {source.close();}
		},
		get readyState() {return source ? source.readyState : EventSource.CLOSED;},
	};
}

let OI_csrfRefresh = null; // in-flight token fetch, shared by concurrent retries

// The CSRF token lives in the PHP session, which expires while a page sits
// open (SSE traffic does not refresh it). Fetch the current session's token,
// starting a new session if need be, into the page.
function OI_refreshCSRF() {
	if (!OI_csrfRefresh) {
		OI_csrfRefresh = $.ajax({type: 'GET', url: 'csrfToken.php', dataType: 'json', cache: false})
			.then((data) => {
				const el = document.getElementById('oi-csrf');
				if (el && data.token) {el.dataset.token = data.token;}
			})
			.always(() => {OI_csrfRefresh = null;});
	}
	return OI_csrfRefresh;
}

function OI_processSubmit(event, url, formData) { // Submission of form data to url
	// Form submission and alert on failure
	const send = (retried) => $.ajax({
		type: 'POST', // Post the form data
		url: url, // Script to process this form
		data: formData, // form data to be posted
		dataType: 'json', // returned data format
		encode: true
	}).done((data) => {
		if (('success' in data) && !data['success']) {
			OI_toast(data['message'], true);
		}
	}).fail((jqXHR, textStatus) => {
		let reply = jqXHR.responseJSON;
		if (reply === undefined) {
			try {reply = JSON.parse(jqXHR.responseText);} catch {reply = null;}
		}
		if (!retried && jqXHR.status === 403 && reply?.message === 'Invalid CSRF token') {
			// Expired session: get a fresh token and try once more
			OI_refreshCSRF().then(() => send(true),
				() => OI_toast('Session expired; reload the page', true));
			return;
		}
		const message = reply?.message ?? `Request failed: ${textStatus}`;
		OI_toast(message, true);
	});
	send(false);
	event.preventDefault();
}

function OI_processForm(event) { // argument to .submit({'url':...}, OI_processForm)
	OI_processSubmit(event, event.data['url'], $(this).serialize());
}
