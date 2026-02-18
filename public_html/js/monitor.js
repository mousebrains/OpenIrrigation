let myInfo = {};

function buildActions(pocs) {
	const tbl = $('#topActions');
	let msg ='<tr>';
	msg += "<th><form id='clearAll'><input type='submit' value='Clear All'></form></th>";
	msg += "<th><form id='allOff'><input type='submit' value='All Off'></form></th>";
	for (const key in pocs) {
		msg += "<td><form class='pocOff'>"
			+ "<input type='hidden' name='poc' value='" + key + "'>"
			+ "<input type='submit' value='POC " + escapeHTML(pocs[key]) + " Off'>"
			+ "</form></td>";
	}
	msg+='</tr>';
	tbl.find('tr').remove(); // Remove rows
	tbl.append(msg);
	$('.pocOff').submit({'url': 'monitorPocOff.php'}, OI_processForm);
	$('#clearAll').submit({'url': 'monitorClearAll.php'}, OI_processForm);
	$('#allOff').submit({'url': 'monitorAllOff.php'}, OI_processForm);
}

function getStationName(id) {
	return ('stn2name' in myInfo) && (id in myInfo['stn2name']) ?
		myInfo['stn2name'][id] : 'Got Me!';
}

function getProgramName(id) {
	return ('pgm2name' in myInfo) && (id in myInfo['pgm2name']) ?
		myInfo['pgm2name'][id] : 'Got Me!';
}

function formatTime(t) {
	const d = new Date(t * 1000);
	return (d.getMonth() + 1) + '-' + d.getDate() + ' ' + d.getHours() + ':' +
		('00' + d.getMinutes()).slice(-2);
}

function formatDeltaTime(dt) {
	const hours = Math.floor(dt / 3600);
	const minutes = Math.floor(dt / 60) % 60;
	return hours + ":" + ("00" + minutes).slice(-2);
}

function buildActive(info) {
	OI_clearTimeouts(); // Shutdown any existing timeouts
	if (info.length === 0) { // Empty, so hide it
		$('#activeDiv').css('display', 'none');
		return;
	}
	const tbl = $('#activeTable');
	tbl.find('tbody tr').remove();
	info.forEach(function (x) {
		const id = x[0];
		const key = 'A' + id;
		const eTime = x[7];
		let row = "<tr>";
		row += "<td><form class='active'>"
			+ "<input type='hidden' name='id', value='" + id + "'>"
			+ " <input type='submit' value='Off'>"
			+ "</form></td>";
		row += "<td>" + escapeHTML(getStationName(x[0])) + "</td>";
		row += "<td>" + formatTime(x[6]) + "</td>";
		row += "<td>" + formatDeltaTime(eTime - x[6]) + "</td>";
		row += "<td id='" + key + "'></td>";
		row += "<td>" + escapeHTML(getProgramName(x[1])) + "</td>";
		row += "<td>" + x[2] + "</td>";
		row += "<td>" + x[3] + "</td>";
		row += "<td>" + x[4] + "</td>";
		row += "<td>" + x[5] + "</td>";
		row += "</tr>";
		tbl.append(row);
		OI_timeDown('#' + key, eTime, null);
	});
	$('#activeDiv').css('display', 'block');
	$('.active').submit({url: 'monitorActiveOff.php'}, OI_processForm);
}

function buildPending(info) {
	if (info.length === 0) { // Empty, so hide it
		$('#pendingDiv').css('display', 'none');
		return;
	}
	const tbl = $('#pendingTable');
	tbl.find('tbody tr').remove();
	info.forEach(function (x) {
		let row = "<tr>";
		row += "<td><form class='pending'>"
			+ "<input type='hidden' name='id', value='" + x[0] + "'>"
			+ " <input type='submit' value='Delete'>"
			+ "</form></td>";
		row += "<td>" + escapeHTML(getStationName(x[1])) + "</td>";
		row += "<td>" + formatTime(x[3]) + "</td>";
		row += "<td>" + formatDeltaTime(x[4] - x[3]) + "</td>";
		row += "<td>" + escapeHTML(getProgramName(x[2])) + "</td>";
		row += "</tr>";
		tbl.append(row);
	});
	$('#pendingDiv').css('display', 'block');
	$('.pending').submit({url: 'monitorPendingRemove.php'}, OI_processForm);
}

function buildPast(info) {
	const tbl = $('#pastTable');
	info.forEach(function (x) {
		let row = "<tr>";
		row += "<td>" + escapeHTML(getStationName(x[0])) + "</td>";
		row += "<td>" + formatTime(x[7]) + "</td>";
		row += "<td>" + formatDeltaTime(x[8] - x[7]) + "</td>";
		row += "<td>" + escapeHTML(getProgramName(x[1])) + "</td>";
		row += "<td>" + x[2] + "</td>";
		row += "<td>" + x[3] + "</td>";
		row += "<td>" + x[4] + "</td>";
		row += "<td>" + x[5] + "</td>";
		row += "<td>" + x[6] + "</td>";
		row += "</tr>";
		tbl.prepend(row);
	});
	$('#pastDiv').css('display', 'block');
}

function receivedStatus(event) {
	const data = JSON.parse(event.data);
	if ('burp' in data) { return; } // Nothing to do on burp messages
	if ('programs' in data) {myInfo['pgm2name'] = data['programs'];} // Update pgm to name
	if ('stations' in data) {myInfo['stn2name'] = data['stations'];} // Update sensor to name
	if ('pocs' in data) {buildActions(data['pocs']);}
	if ('active' in data) {buildActive(data['active'])};
	if ('pending' in data) {buildPending(data['pending'])};
	if ('past' in data) {buildPast(data['past'])};
}

if (typeof(EventSource) !== "undefined") {
	const statusSource = new EventSource("monitorStatus.php");
	statusSource.onmessage = receivedStatus;
	$('#clearAll').submit({'url': 'monitorClearAll.php'}, OI_processForm);
	$('#allOff').submit({'url': 'monitorAllOff.php'}, OI_processForm);
}
