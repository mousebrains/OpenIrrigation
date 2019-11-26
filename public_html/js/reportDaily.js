var myInfo = {}

function mkDate2Col(earliest, today, latest) {
	var now = new Date(today); // Today with UTC midnight
	var eTime = new Date(latest); // Latest with UTC midnight
	var cnt = 0;
	// English!
	var shortNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thur', 'Fri', 'Sat'];

	myInfo['earliest'] = earliest;
	myInfo['today'] = today;
	myInfo['latest'] = latest;
	myInfo['past2col'] = {}
	myInfo['pending2col'] = {}
	myInfo['pastDates'] = [];
	myInfo['pendingDates'] = [];

	for (var t = new Date(earliest); t <= now; t.setDate(t.getDate() + 1)) {
		var a = (t.getUTCMonth() + 1) + '-' + ('0' + t.getUTCDate()).slice(-2);
		myInfo['pastDates'].push(a);
		myInfo['past2col'][a] = cnt;
		++cnt;
	}

	for (var t = now; t <= eTime; t.setDate(t.getDate() + 1)) {
		var a = (t.getUTCMonth() + 1) + '-' + ('0' + t.getUTCDate()).slice(-2);
		myInfo['pendingDates'].push(a);
		myInfo['pending2col'][a] = cnt;
		++cnt;
	}
}

function mkHeaders(tbl) {
	var thead = tbl.find('thead');
	var tfoot = tbl.find('tfoot');
	var nPast = myInfo['pastDates'].length;
	var nPending = myInfo['pendingDates'].length;
	var past = "<tr>";
	var pending = "<th>Today</th>";
	var mid =  "<th rowspan='2'>Station</th><th rowspan='2'>Program</th>";
	var pre = "<tr><th colspan='" + nPast + "'>Recent</th>";
	var post = "<th colspan='" + nPending + "'>Future</th></tr>";

	(myInfo['pastDates'].slice(0,-1)).forEach(function(x) {
		past += "<th>" + x.slice(-5) + "</th>";});
	past += "<th>Today</th>";

	(myInfo['pendingDates'].slice(1)).forEach(function(x) {
		pending += "<th>" + x.slice(-5) + "</th>";}) + "<tr>";

	thead.append(pre + mid + post);
	thead.append(past + pending);
	tfoot.append(past + mid + pending);
	tfoot.append(pre + post);
}

function mkBodyRow(id, name, program, rowCount) {
	var color = " style='background-color:" + ((rowCount & 0x01) ? "#fcbe03;'" : "#03cffc;'");
	var cnt = 0;
	var line = "<tr>";
	myInfo['pastDates'].forEach(function(x) {
		line += "<td id='R" + id + "C" + cnt + "'></td>";
		++cnt;
	});

	line += "<th" + color + ">" + name + "</th><th" + color + ">" + program + "</th>";

	myInfo['pendingDates'].forEach(function(x) {
		line += "<td id='R" + id + "C" + cnt + "'></td>";
		++cnt;
	});
	return line + "</tr>";
}

function mkBody(tbl, info) {
	var cnt = 0;
	info.forEach(function(x) {
		tbl.append(mkBodyRow(x[0], x[1], x[2], ++cnt));
	});
}

function buildTable(info, earliest, today, latest) {
	var tbl = $('#report');

	mkDate2Col(earliest, today, latest);

	tbl.find('tr').remove(); // Drop all the existing rows
	mkHeaders(tbl);
	mkBody(tbl.find('tbody'), info);
}

function mkTime(dt) {
	var hours = Math.floor(dt / 3600);
	var minutes = Math.floor(dt / 60) % 60;
	return hours + ":" + ("00" + minutes).slice(-2);
}

function mkKey(id, d, key) {
	return '#R' + id + 'C' + (((key in myInfo) && (d in myInfo[key])) ? myInfo[key][d] : 'XX');
}

function displayTimes(data) {
	var past = {} // indexed by pgmdate/station
	var pending = {} // indexed by pgmdate/station

	if ('timeouts' in myInfo) { // Clear existing timeouts
		for (var key in myInfo['timeouts']) { clearTimeout(myInfo['timeouts'][key]); }
	}
	myInfo['timeouts'] = {};

	data['past'].forEach(function(x) {
		var id = x[0];
		var d = x[1];
		var dt = parseFloat(x[2]);
		var key = mkKey(id, d, 'past2col');
		$(key).html(mkTime(dt));
		if (!(id in past)) {past[id] = {};}
		past[id][d] = dt;
	});
	data['pending'].forEach(function(x) {
		var id = x[0];
		var d = x[1];
		var dt = parseFloat(x[2]);
		var key = mkKey(id, d, 'pending2col');
		$(key).html(mkTime(dt));
		if (!(id in pending)) {pending[id] = {};}
		pending[id][d] = dt;
	});

	OI_clearTimeouts();

	data['active'].forEach(function(x) {
		var id = x[0];
		var d = x[1];
		var t0 = parseFloat(x[2]);
		var t1 = parseFloat(x[3]);
		var now = Date.now() / 1000;
		var pre0 = (id in past) && (d in past[id]) ? past[id][d] : 0;
		var pre1 = (id in pending) && (d in pending[id]) ? pending[id][d] : 0;
		var key0 = mkKey(id, d, 'past2col');
		var key1 = mkKey(id, d, 'pending2col');
		OI_timeUpDown(key0, key1, t0, t1, pre0, pre1, null);
	});
}

function receivedStatus(event) {
	var data = JSON.parse(event.data);
	if ('burp' in data) { return; } // Nothing to do on burp messages
	if (('info' in data) 
		|| (!('earliest' in myInfo) || (myInfo['earliest'] != data['earliest']))
		|| (!('today' in myInfo) || (myInfo['today'] != data['today']))
		|| (!('latest' in myInfo) || (myInfo['latest'] != data['latest']))) {
		// rebuild the full table
		buildTable(data['info'], data['earliest'], data['today'], data['latest']);
	}
	if ('active' in data) {displayTimes(data);}
}

if (typeof(EventSource) != "undefined") {
	var statusSource = new EventSource("reportDailyStatus.php");
	statusSource.onmessage = receivedStatus;
}
