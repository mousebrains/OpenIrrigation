let indexInfo = {'active': new Set(), 'pending': new Set(), 'past': new Set(), 'all': new Set()};
let dtInfo = {'hoursFuture': 12, 'hoursPast': 12};

function procForm(event) {
	const id = $(this).attr('id').slice(-2); // Form's id
	OI_processSubmit(event, 'indexProcess.php', $(this).serialize());
	$(`#rt${id}`).val(''); // reset the value
	$(`#${id}`).css('background-color', '#00A0DD'); // Set row color
}

function buildTable(info, tblID, runLabel, stopLabel) {
	const tbl = $(tblID);
	tbl.find('tbody tr').remove(); // Drop existing rows in body
	info.forEach((x) => {
		const key = x[0]; // Sensor ID
		const name = x[1]; // Station name
		let msg = "";
		let inputs = `<input type='hidden' name='id' value='${key}'>`;
		if (x.length > 2) {
			inputs += `<input type='hidden' name='poc' value='${x[2]}'>`;
		}
		msg += `<tr id='${key}'>`;
		msg += "<td class='tooltip' onclick=''>"; // onclick for ios/safari hover to work
		msg += `<span class='tooltiptext tooltip-left' id='tt${key}'>Nada</span>`;
		msg += `${escapeHTML(name)}</td>`;
		msg += "<td style='text-align:right;'>";
		msg += `<span id='a${key}' style='display:inline;'>`;
		msg += `<form class='indexForm' id='f${key}'>`;
		msg += inputs;
		msg += `<input type='number' name='time' id='rt${key}'`;
		msg += 		" title='Number of minutes'";
		msg +=		" min='0.1' max='300' step='0.1'>";
		msg += `<input type='submit' value='${runLabel}'>`;
		msg += "</form>";
		msg += "</span>";
		msg += `<span id='b${key}' style='display:none;'>`;
		msg += `<span id='bc${key}'></span>`;
		msg += `<form class='indexForm' id='g${key}' style='display:inline;'>`;
		msg += inputs;
		msg += `<input type='submit' value='${stopLabel}'>`;
		msg += "</form>";
		msg += "</span>";
		msg += "</td></tr>";
		tbl.append(msg);
	});
} // build Table

function mkTime(dt) { // Convert dt seconds to h:mm:ss
	const hours = Math.floor(dt / 3600);
	const mins = ("00" + Math.floor(dt / 60) % 60).slice(-2);
	const secs = ("00" + Math.floor(dt % 60)).slice(-2);
	return hours + ":" + mins + ":" + secs;
}

function mkToolTip(key, data) {
	let msg = '';
	if (key in data['active']) {
		const dt = data['active'][key][0][1] - data['active'][key][0][0];
		msg += `Current: ${mkTime(dt)}`;
	}
	if (key in data['pending']) {
		let dt = 0;
		data['pending'][key].forEach((x) => {dt += x[1] - x[0];});
		if (msg !== '') {msg += "<br />";}
		msg += `Next ${dtInfo['hoursFuture']}Hr: ${mkTime(dt)}`;
	}
	if (key in data['past']) {
		let dt = 0;
		data['past'][key].forEach((x) => {dt += x[1] - x[0];});
		if (msg !== '') {msg += "<br />";}
		msg += `Prev ${dtInfo['hoursPast']}Hr: ${mkTime(dt)}`;
	}
	return msg;
}

function adjustColors(data) {
	const info = {};
	info['pending'] = new Set(Object.keys(data['pending']));
	info['active'] = new Set(Object.keys(data['active']));
	info['past'] = new Set(Object.keys(data['past']));
	info['all'] = new Set([...info['pending'], ...info['active'], ...info['past']]);
	// Take out of pending and past everything that is active
	info['pending'] = new Set([...info['pending']].filter(x => !info['active'].has(x)));
	info['past'] = new Set([...info['past']].filter(x => !info['active'].has(x)));
	// Take out of and everything that is pending
	info['past'] = new Set([...info['past']].filter(x => !info['pending'].has(x)));
	const all2Clear = new Set([...indexInfo['all']].filter(x => !info['all'].has(x)));
	const active2Set = new Set([...info['active']].filter(x => !indexInfo['active'].has(x)));
	const pending2Set = new Set([...info['pending']].filter(x => !indexInfo['pending'].has(x)));
	const past2Set = new Set([...info['past']].filter(x => !indexInfo['past'].has(x)));

	OI_clearTimeouts(); // Shutdown any existing timeouts

	all2Clear.forEach((x) => {
		$(`#${x}`).css('background-color', '');
		$(`#a${x}`).css('display', 'inline');
		$(`#b${x}`).css('display', 'none');
		$(`#tt${x}`).html('Nada');
	});
	active2Set.forEach((x) => {
		$(`#${x}`).css('background-color', '#8FBC8F');
		$(`#a${x}`).css('display', 'none');
		$(`#b${x}`).css('display', 'inline');
		$(`#tt${x}`).html(mkToolTip(x, data));
	});
	pending2Set.forEach((x) => {
		$(`#${x}`).css('background-color', '#DDA0DD');
		$(`#a${x}`).css('display', 'inline');
		$(`#b${x}`).css('display', 'none');
		$(`#tt${x}`).html(mkToolTip(x, data));
	});
	past2Set.forEach((x) => {
		$(`#${x}`).css('background-color', '#FDDEB3');
		$(`#a${x}`).css('display', 'inline');
		$(`#b${x}`).css('display', 'none');
		$(`#tt${x}`).html( mkToolTip(x, data));
	});

	// info['times'] = data['active']; // For time left calculation
	indexInfo = info; // For the next pass
	// indexUpdateTimes();

	if (indexInfo['active'].size) { // Something active
		indexInfo['etime'] = {};
		indexInfo['active'].forEach((key) => {
			indexInfo['etime'][key] = data['active'][key][0][1];
			OI_timeDown(`#bc${key}`, indexInfo['etime'][key], null);
		});
	}

}

function receivedStatus(event) {
	const data = JSON.parse(event.data);
	if ('burp' in data) { return; } // Nothing to do on burp messages
	if (('info' in data) || ('pocs' in data)) {
		if ('info' in data) {buildTable(data['info'], '#stnTable', 'Run', 'Off');}
		if ('pocs' in data) {
			buildTable(data['pocs'], '#pocTable', 'Off', 'Open');
			$('#pocBlock').css('display', 'inline');
		}
		$('.indexForm').submit(procForm); // Attach to all forms
		if ('hoursPast' in data) {dtInfo['hoursPast'] = data['hoursPast'];}
		if ('hoursFuture' in data) {dtInfo['hoursFuture'] = data['hoursFuture'];}
	}
	if ('active' in data) { adjustColors(data); }
}

if (typeof EventSource !== "undefined") {
	const statusSource = OI_connectSSE("indexStatus.php", receivedStatus);
}
