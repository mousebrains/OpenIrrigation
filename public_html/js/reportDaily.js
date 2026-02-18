let myInfo = {};

function addToMyInfo(cnt, t, dateKey, colKey) {
	const year = t.getUTCFullYear();
	const mon = t.getUTCMonth() + 1;
	const dom = ('0' + t.getUTCDate()).slice(-2);
	const a = mon + '-' + dom;
	const key = year + '-' + ('0' + mon).slice(-2) + '-' + dom;
	myInfo[dateKey].push(a);
	myInfo[colKey][key] = cnt;
	return cnt + 1;
}

function mkDate2Col(earliest, today, latest) {
	const now = new Date(today); // Today with UTC midnight
	const eTime = new Date(latest); // Latest with UTC midnight
	let cnt = 0;

	myInfo['earliest'] = earliest;
	myInfo['today'] = today;
	myInfo['latest'] = latest;
	myInfo['past2col'] = {};
	myInfo['pending2col'] = {};
	myInfo['pastDates'] = [];
	myInfo['pendingDates'] = [];

	for (let t = new Date(earliest); t <= now; t.setDate(t.getDate() + 1)) {
		cnt = addToMyInfo(cnt, t, 'pastDates', 'past2col');
	}

	for (let t = now; t <= eTime; t.setDate(t.getDate() + 1)) {
		cnt = addToMyInfo(cnt, t, 'pendingDates', 'pending2col');
	}
}

function mkHeaders(tbl) {
	const thead = tbl.find('thead');
	const tfoot = tbl.find('tfoot');
	const nPast = myInfo['pastDates'].length;
	const nPending = myInfo['pendingDates'].length;
	let past = "<tr>";
	let pending = "<th>Today</th>";
	const mid =  "<th rowspan='2'>Station</th><th rowspan='2'>Program</th>";
	const pre = "<tr><th colspan='" + nPast + "'>Recent</th>";
	const post = "<th colspan='" + nPending + "'>Future</th></tr>";

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
	const color = " style='background-color:" + ((rowCount & 0x01) ? "#fcbe03;'" : "#03cffc;'");
	let cnt = 0;
	let line = "<tr>";
	myInfo['pastDates'].forEach(function(x) {
		line += "<td id='R" + id + "C" + cnt + "'></td>";
		++cnt;
	});

	line += "<th" + color + ">" + escapeHTML(name) + "</th><th" + color + ">" + escapeHTML(program) + "</th>";

	myInfo['pendingDates'].forEach(function(x) {
		line += "<td id='R" + id + "C" + cnt + "'></td>";
		++cnt;
	});
	return line + "</tr>";
}

function mkBody(tbl, info) {
	let cnt = 0;
	info.forEach(function(x) {
		tbl.append(mkBodyRow(x[0], x[1], x[2], ++cnt));
	});
}

function buildTable(info, earliest, today, latest) {
	const tbl = $('#report');

	mkDate2Col(earliest, today, latest);

	tbl.find('tr').remove(); // Drop all the existing rows
	mkHeaders(tbl);
	mkBody(tbl.find('tbody'), info);
}

function mkTime(dt) {
	const hours = Math.floor(dt / 3600);
	const minutes = Math.floor(dt / 60) % 60;
	return hours + ":" + ("00" + minutes).slice(-2);
}

function mkKey(id, d, key) {
	return '#R' + id + 'C' + (((key in myInfo) && (d in myInfo[key])) ? myInfo[key][d] : 'XX');
}

function displayTimes(data) {
	const past = {}; // indexed by pgmdate/station
	const pending = {}; // indexed by pgmdate/station

	if ('timeouts' in myInfo) { // Clear existing timeouts
		for (const key in myInfo['timeouts']) { clearTimeout(myInfo['timeouts'][key]); }
	}
	myInfo['timeouts'] = {};

	data['past'].forEach(function(x) {
		const id = x[0];
		const d = x[1];
		const dt = parseFloat(x[2]);
		const key = mkKey(id, d, 'past2col');
		$(key).html(mkTime(dt));
		if (!(id in past)) {past[id] = {};}
		past[id][d] = dt;
	});
	data['pending'].forEach(function(x) {
		const id = x[0];
		const d = x[1];
		const dt = parseFloat(x[2]);
		const key = mkKey(id, d, 'pending2col');
		$(key).html(mkTime(dt));
		if (!(id in pending)) {pending[id] = {};}
		pending[id][d] = dt;
	});

	OI_clearTimeouts();

	data['active'].forEach(function(x) {
		const id = x[0];
		const d = x[1];
		const t0 = parseFloat(x[2]);
		const t1 = parseFloat(x[3]);
		const now = Date.now() / 1000;
		const pre0 = (id in past) && (d in past[id]) ? past[id][d] : 0;
		const pre1 = (id in pending) && (d in pending[id]) ? pending[id][d] : 0;
		const key0 = mkKey(id, d, 'past2col');
		const key1 = mkKey(id, d, 'pending2col');
		OI_timeUpDown(key0, key1, t0, t1, pre0, pre1, null);
	});
}

function receivedStatus(event) {
	const data = JSON.parse(event.data);
	if ('burp' in data) { return; } // Nothing to do on burp messages
	if (('info' in data)
		|| (!('earliest' in myInfo) || (myInfo['earliest'] !== data['earliest']))
		|| (!('today' in myInfo) || (myInfo['today'] !== data['today']))
		|| (!('latest' in myInfo) || (myInfo['latest'] !== data['latest']))) {
		// rebuild the full table
		buildTable(data['info'], data['earliest'], data['today'], data['latest']);
	}
	if ('active' in data) {displayTimes(data);}
}

if (typeof(EventSource) !== "undefined") {
	const statusSource = new EventSource("reportDailyStatus.php");
	statusSource.onmessage = receivedStatus;
}
