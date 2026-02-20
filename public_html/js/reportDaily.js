const myInfo = {};

function addToMyInfo(cnt, t, dateKey, colKey) {
	const year = t.getUTCFullYear();
	const mon = t.getUTCMonth() + 1;
	const dom = String(t.getUTCDate()).padStart(2, '0');
	const a = `${mon}-${dom}`;
	const key = `${year}-${String(mon).padStart(2, '0')}-${dom}`;
	myInfo[dateKey].push(a);
	myInfo[colKey][key] = cnt;
	return cnt + 1;
}

function mkDate2Col(earliest, today, latest) {
	const now = new Date(today); // Today with UTC midnight
	const eTime = new Date(latest); // Latest with UTC midnight
	let cnt = 0;

	myInfo.earliest = earliest;
	myInfo.today = today;
	myInfo.latest = latest;
	myInfo.past2col = {};
	myInfo.pending2col = {};
	myInfo.pastDates = [];
	myInfo.pendingDates = [];

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
	const nPast = myInfo.pastDates.length;
	const nPending = myInfo.pendingDates.length;
	let past = "<tr>";
	let pending = "<th>Today</th>";
	const mid =  "<th rowspan='2'>Station</th><th rowspan='2'>Program</th>";
	const pre = `<tr><th colspan='${nPast}'>Recent</th>`;
	const post = `<th colspan='${nPending}'>Future</th></tr>`;

	myInfo.pastDates.slice(0, -1).forEach((x) => {
		past += `<th>${x.slice(-5)}</th>`;});
	past += "<th>Today</th>";

	myInfo.pendingDates.slice(1).forEach((x) => {
		pending += `<th>${x.slice(-5)}</th>`;});

	thead.append(pre + mid + post);
	thead.append(past + pending);
	tfoot.append(past + mid + pending);
	tfoot.append(pre + post);
}

function mkBodyRow(id, name, program, rowCount) {
	const color = ` style='background-color:${(rowCount & 0x01) ? "#fcbe03;'" : "#03cffc;'"}`;
	let cnt = 0;
	let line = "<tr>";
	myInfo.pastDates.forEach(() => {
		line += `<td id='R${id}C${cnt}'></td>`;
		++cnt;
	});

	line += `<th${color}>${escapeHTML(name)}</th><th${color}>${escapeHTML(program)}</th>`;

	myInfo.pendingDates.forEach(() => {
		line += `<td id='R${id}C${cnt}'></td>`;
		++cnt;
	});
	return line + "</tr>";
}

function mkBody(tbl, info) {
	let cnt = 0;
	info.forEach((x) => {
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
	return `${hours}:${String(minutes).padStart(2, '0')}`;
}

function mkKey(id, d, key) {
	return `#R${id}C${(((key in myInfo) && (d in myInfo[key])) ? myInfo[key][d] : 'XX')}`;
}

function buildTargetMap(arr) {
	const map = {};
	arr.forEach((x) => {
		const id = x[0];
		const d = x[1];
		const target = parseFloat(x[2]);
		if (!(id in map)) {map[id] = {};}
		map[id][d] = target;
	});
	return map;
}

function colorCell(key, dt, target) {
	if (target > 0 && dt / target <= 0.95) {
		$(key).css('background-color', '#ffe0b2').attr('title', `Target: ${mkTime(target)}`);
	} else {
		$(key).css('background-color', '').removeAttr('title');
	}
}

function displayTimes(data) {
	const past = {}; // indexed by sensor/date
	const pending = {}; // indexed by sensor/date
	const pastTargets = buildTargetMap(data.pastTargets || []);
	const pendingTargets = buildTargetMap(data.pendingTargets || []);
	const todayTargets = {};
	(data.todayTargets || []).forEach((x) => {
		todayTargets[x[0]] = parseFloat(x[1]);
	});
	const today = myInfo.today;

	if ('timeouts' in myInfo) { // Clear existing timeouts
		Object.values(myInfo.timeouts).forEach((id) => { clearTimeout(id); });
	}
	myInfo.timeouts = {};

	// First pass: populate maps and set cell HTML (no coloring yet)
	data.past.forEach((x) => {
		const id = x[0];
		const d = x[1];
		const dt = parseFloat(x[2]);
		const key = mkKey(id, d, 'past2col');
		$(key).html(mkTime(dt));
		if (!(id in past)) {past[id] = {};}
		past[id][d] = dt;
	});
	data.pending.forEach((x) => {
		const id = x[0];
		const d = x[1];
		const dt = parseFloat(x[2]);
		const key = mkKey(id, d, 'pending2col');
		$(key).html(mkTime(dt));
		if (!(id in pending)) {pending[id] = {};}
		pending[id][d] = dt;
	});

	// Second pass: color cells
	data.past.forEach((x) => {
		const id = x[0];
		const d = x[1];
		const key = mkKey(id, d, 'past2col');
		if (d === today) {
			const combined = (past[id][d] || 0) + ((id in pending && today in pending[id]) ? pending[id][today] : 0);
			colorCell(key, combined, todayTargets[id] || 0);
		} else {
			const target = (id in pastTargets) && (d in pastTargets[id]) ? pastTargets[id][d] : 0;
			colorCell(key, past[id][d], target);
		}
	});
	data.pending.forEach((x) => {
		const id = x[0];
		const d = x[1];
		const key = mkKey(id, d, 'pending2col');
		if (d === today) {
			const combined = ((id in past && today in past[id]) ? past[id][today] : 0) + (pending[id][d] || 0);
			colorCell(key, combined, todayTargets[id] || 0);
		} else {
			const target = (id in pendingTargets) && (d in pendingTargets[id]) ? pendingTargets[id][d] : 0;
			colorCell(key, pending[id][d], target);
		}
	});

	OI_clearTimeouts();

	data.active.forEach((x) => {
		const id = x[0];
		const d = x[1];
		const t0 = parseFloat(x[2]);
		const t1 = parseFloat(x[3]);
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
		|| (!('earliest' in myInfo) || (myInfo.earliest !== data.earliest))
		|| (!('today' in myInfo) || (myInfo.today !== data.today))
		|| (!('latest' in myInfo) || (myInfo.latest !== data.latest))) {
		// rebuild the full table
		buildTable(data.info, data.earliest, data.today, data.latest);
	}
	if ('active' in data) {displayTimes(data);}
}

if (typeof EventSource !== "undefined") {
	const statusSource = OI_connectSSE("reportDailyStatus.php", receivedStatus);
}
