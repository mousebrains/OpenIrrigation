var myInfo = {};

function mkActionCell(val, name) {
	return "<td><form class='actions'>"
		+ "<input type='hidden' name='action' value='" + val + "'>"
		+ "<input type='submit' value='" + name + "'>"
		+ "</form></td>";
}

function buildActions(pocs) {
	var tbl = $('#topActions');
	var msg ='<tr>';
	msg+= mkActionCell('clearAll', 'Clear All');
	msg+= mkActionCell('allOff', 'All Off');
	for(var key in pocs) {
		msg += "<td><form class='actions'>"
			+ "<input type='hidden' name='action' value='pocOff'>"
			+ "<input type='hidden' name='poc' value='" + key + "'>"
			+ "<input type='submit' value='POC " + pocs[key] + " Off'>"
			+ "</form></td>";
	}
	msg+='</tr>';
	tbl.find('tr').remove(); // Remove rows
	tbl.append(msg);
	$('.actions').submit({'url': 'monitorProcAction.php'}, OI_processForm);
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
	var d = new Date(t * 1000);
	return (d.getMonth() + 1) + '-' + d.getDate() + ' ' + d.getHours() + ':' + 
		('00' + d.getMinutes()).slice(-2);
}

function formatDeltaTime(dt) {
	var hours = Math.floor(dt / 3600);
	var minutes = Math.floor(dt / 60) % 60;
	return hours + ":" + ("00" + minutes).slice(-2);
}

function buildActive(info) {
	OI_clearTimeouts(); // Shutdown any existing timeouts
	if (info.length == 0) { // Empty, so hide it
		$('#activeDiv').css('display', 'none');
		return;
	}
	var tbl = $('#activeTable');
	tbl.find('tbody tr').remove();
	info.forEach(function (x) {
		var id = x[0];
		var key = 'A' + id;
		var eTime = x[7];
		var row = "<tr>";
		row += "<td><form class='active'>"
			+ "<input type='hidden' name='id', value='" + id + "'>"
			+ " <input type='submit' value='Off'>"
			+ "</form></td>";
		row += "<td>" + getStationName(x[0]) + "</td>";
		row += "<td>" + formatTime(x[6]) + "</td>";
		row += "<td>" + formatDeltaTime(eTime - x[6]) + "</td>";
		row += "<td id='" + key + "'></td>";
		row += "<td>" + getProgramName(x[1]) + "</td>";
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
	if (info.length == 0) { // Empty, so hide it
		$('#pendingDiv').css('display', 'none');
		return;
	}
	var tbl = $('#pendingTable');
	tbl.find('tbody tr').remove();
	info.forEach(function (x) {
		var row = "<tr>";
		row += "<td><form class='pending'>"
			+ "<input type='hidden' name='id', value='" + x[0] + "'>"
			+ " <input type='submit' value='Delete'>"
			+ "</form></td>";
		row += "<td>" + getStationName(x[1]) + "</td>";
		row += "<td>" + formatTime(x[3]) + "</td>";
		row += "<td>" + formatDeltaTime(x[4] - x[3]) + "</td>";
		row += "<td>" + getProgramName(x[2]) + "</td>";
		row += "</tr>";
		tbl.append(row);
	});
	$('#pendingDiv').css('display', 'block');
	$('.pending').submit({url: 'monitorPendingRemove.php'}, OI_processForm);
}

function buildPast(info) {
	var tbl = $('#pastTable');
	tbl.find('tbody tr').remove();
	info.forEach(function (x) {
		var row = "<tr>";
		row += "<td>" + getStationName(x[0]) + "</td>";
		row += "<td>" + formatTime(x[7]) + "</td>";
		row += "<td>" + formatDeltaTime(x[8] - x[7]) + "</td>";
		row += "<td>" + getProgramName(x[1]) + "</td>";
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
	var data = JSON.parse(event.data);
	if ('burp' in data) { return; } // Nothing to do on burp messages
	if ('programs' in data) {myInfo['pgm2name'] = data['programs'];} // Update pgm to name
	if ('stations' in data) {myInfo['stn2name'] = data['stations'];} // Update sensor to name
	if ('pocs' in data) {buildActions(data['pocs']);}
	if ('active' in data) {buildActive(data['active'])};
	if ('pending' in data) {buildPending(data['pending'])};
	if ('past' in data) {buildPast(data['past'])};
}

if (typeof(EventSource) != "undefined") {
	var statusSource = new EventSource("monitorStatus.php");
	statusSource.onmessage = receivedStatus;
}
