let myTableInfo = {};
let myReferenceInfo = {};
let mySecondaryInfo = {};
let statusSource;

function buildTable(info) {
	myTableInfo = info;

	let row = '<tr>';
	row += '<th></th>'; // Delete
	row += '<th></th>'; // Update

	info.forEach(function(x) {
		row += '<th>' + escapeHTML(x['label']) + '</th>';
		myTableName = x['tbl'];
	});
	row += '</tr>';
	$('thead').find('tr').remove(); // remove any added rows
	$('tbody').find('tr').remove(); // remove any added rows
	$('tfoot').find('tr').remove(); // remove any added rows
	$('thead').append().html(row);
	$('tfoot').append().html(row);
}

function mkRefTable(a, x, form) {
	const col = a['col'];
	let val = (x !== null) ? x[col] : null;
	const id = (x !== null) ? x['id'] : null;
	const qMultiple = col in mySecondaryInfo;
	const sec = qMultiple ? mySecondaryInfo[col] : null;
	let msg = "<select name='" + col + (qMultiple ? "[]'" : "'");
	if (a['qrequired'] === true) msg += ' required';
	if (qMultiple) {
		val = (id in sec) ? sec[id].join() : '';  // Redo val for multiples
		msg += ' multiple';
	}
	msg += form;
	myReferenceInfo[col].forEach(function(y) {
		const yid = y['id'];
		msg += "<option value='" + escapeHTML(yid) + "'";
		if ((yid === val) || (qMultiple && (id in sec) && sec[id].includes(yid))) {
			msg += " selected";
		}
		msg += ">" + escapeHTML(y['name']) + "</option>";
	});
	msg += "</select>";
	if (x !== null) {
		msg += "<input type='hidden' name='" + col + "Prev'"
			+ " value='" + escapeHTML(val) + "'" + form;
	}
	return msg;
}

function mkTextArea(a, x, form) {
	const col = a['col'];
	const val = (x !== null) && (col in x) && (x[col] !== null) ? x[col] : "";
	let msg = "<textarea rows='2' cols='20' name='" + col + "'";
	if (a['qrequired'] === true) msg += ' required';
	msg += form;
	msg += escapeHTML(val);
	msg += "</textarea>";
	if (x !== null) {
		msg += "<input type='hidden' name='" + col + "Prev'"
			+ " value='" + escapeHTML(val) + "'" + form;
	}
	return msg;
}

function mkInputField(a, x, form) {
	const col = a['col'];
	const rawVal = (x !== null) && (col in x) && (x[col] !== null) ? x[col] : null;
	const val = rawVal === null ? "" : ("value='" + escapeHTML(rawVal) + "'");
	let msg = "<input type='" + a['inputtype'] + "'";
	if (a['inputtype'] === 'password') msg += " autocomplete='on'";
	if (a['valmin'] !== null) msg += " min='" + a['valmin'] + "'";
	if (a['valmax'] !== null) msg += " max='" + a['valmax'] + "'";
	if (a['valstep'] !== null) msg += " step='" + a['valstep'] + "'";
	msg += " name='" + col + "'" + val;
	if (a['placeholder'] !== '') msg += " placeholder='" + escapeHTML(a['placeholder']) + "'";
	if (a['qrequired'] === true) msg += ' required';
	if ((a['inputtype'] === 'checkbox') && rawVal) msg += ' checked';
	msg += form;
	if (x !== null) msg += "<input type='hidden' name='" + col + "Prev'" + val + form;
	return msg;
}

function buildRow(x, qInsert) {
	const id = (x === null) ? 'Insert' : x['id'];
	const form = " form='f" + id + "'>";
	const tbl = "<input type='hidden' name='tableName' value='" + escapeHTML(myTableName) + "'>";
	let row = "<tr id='tr" + id + "'>";
	if (qInsert) { // Insertion row
		row += "<td colspan=2>";
		row += "<form class='formInsert' id='f" + id + "'>";
		row += tbl;
		row += "<input type='submit' value='Insert'>";
		row += "</form>";
		row += "</td>";
	} else { // data row
		const idIn = "<input type='hidden' name='id' value='" + id + "'>";
		row += "<td><form class='formDelete'>";
		row += tbl;
		row += idIn;
		row += "<input type='submit' value='Delete'>";
		row += "</form></td>";
		row += "<td>";
		row += "<form class='formUpdate' id='f" + id + "'>";
		row += tbl;
		row += idIn;
		row += "<input type='submit' value='Update'>";
		row += "</form>";
		row += "</td>";
	}

	myTableInfo.forEach(function(a) {
		const col = a['col'];
		row += "<td>";
		if (a['inputtype'] === 'textarea') {
			row += mkTextArea(a, x, form);
		} else if (col in myReferenceInfo) {
			row += mkRefTable(a, x, form);
		} else { // normal input
			row += mkInputField(a, x, form);
		}
		row += "</td>";
	});
	row += "</tr>";
	return row;
}

function buildBody(data) {
	const tbl = $('tbody');
	tbl.find('tr').remove(); // remove all rows in the body
	data.forEach(function(x) {
		if (!('qhide' in x) || !x['qhide']) {
			tbl.append(buildRow(x, false));
		}
	});
	tbl.append(buildRow(null, true));
	updateActions(tbl);
}

function updateActions(obj) {
	obj.find('.formDelete').submit({'url': 'tableRowDelete.php'}, OI_processForm);
	obj.find('.formUpdate').submit({'url': 'tableRowUpdate.php'}, OI_processForm);
	obj.find('.formInsert').submit({'url': 'tableRowInsert.php'}, OI_processForm);
	obj.find('input,select,textarea').change(inputChanged);
}

function inputChanged(ev) {
	const name = $(this).attr('name');
	const td = $(this).parent(); // TD element above me
	const prev = td.children('input:hidden');
	const prevVal = (prev === undefined) ? undefined : prev.val();

	const tr = td.parent(); // TR element above me

	const qChanged = checkCellChanged($(this).val(), prevVal) ||
		checkRowChanged(tr.children('td'));
	if (qChanged) {
		tr.addClass('rowchanged');
	} else {
		tr.removeClass('rowchanged');
	}
} // inputChanged

function checkCellChanged(val, prevVal) {
	if (Array.isArray(val)) { // multiple select
		val = val.sort().map(Number).join(',');
	}
	return val !== prevVal;
} // checkCellChanged

function checkRowChanged(tds) {
	for (let i = 0; i < tds.length; ++i) {
		const td = tds[i];
		const prev = $(td).children('input:hidden');
		if (prev.length !== 1) continue;
		const prevVal = (prev === undefined) ? undefined : prev.val();
		let item = $(td).children('select');
		if (item.length === 1) {
			if (checkCellChanged(item.val(), prevVal)) return true;
			continue;
		}
		item = $(td).children('input:not(:hidden)');
		if (item.length !== 1) continue;
		if (checkCellChanged(item.val(), prevVal)) return true;
	} // for i
	return false;
} // checkRowChanged

function batchUpdate() { // batch update button pressed
	const trs = $('tbody').children('tr');
	for (let i = 0; i < trs.length; ++i) {
		const tr = trs[i];
		if (!$(tr).hasClass('rowchanged')) continue;
		const frm = $(tr).find('.formUpdate');
		$(frm).submit(); // Update this row
	} // for i
} // batchUpdate

function batchCancel() { // cancel button pressed
	const trs = $('tbody').children('tr');
	for (let i = 0; i < trs.length; ++i) {
		const tr = trs[i];
		if (!$(tr).hasClass('rowchanged')) continue; // Nothing to reset to
		const frm = $(tr).find('.formUpdate');
		$(frm)[0].reset(); // Reset to default values
		$(tr).removeClass('rowchanged'); // No longer changed
	} // for i
} // batchCancel

function receivedStatus(event) {
	const data = JSON.parse(event.data);
	if ('burp' in data) { return; } // Nothing to do on burp messages
	if ('message' in data) {
		alert(data['message']);
		statusSource.close();
		return;
	}
	if ('ref' in data) {myReferenceInfo = data['ref'];}
	if ('secondary' in data) {mySecondaryInfo = data['secondary'];}
	if ('info' in data) {
		buildTable(data['info']);
		buildBody([]); // For insert row
	}
	if ('action' in data) {
		const trID = '#tr' + data['id'];
		if (data['action'] === 'DELETE') {
			$(trID).remove();
			return;
		}
		if (data['action'] === 'INSERT') {
			$('#trInsert').before(buildRow(data['data'][0], false));
			$('#trInsert').replaceWith(buildRow(null, true));
			updateActions($(trID));
			updateActions($('#trInsert'));
			return;
		}
		if (data['action'] === 'UPDATE') {
			$(trID).replaceWith(buildRow(data['data'][0], false));
			$(trID).addClass('haschanged');
			updateActions($(trID));
			return;
		}
		console.log('Unrecognized action, "' + data['action'] + '"');
		console.log(data);
		return;
	}
	if ('data' in data) {buildBody(data['data']);}
}

if (typeof(EventSource) !== "undefined") {
	const base = 'tableStatus.php';
	const parts = window.location.href.split('?'); // Get parameters
	const url = parts.length > 1 ? (base + '?' + parts.slice(-1)) : base;
	statusSource = new EventSource(url);
	statusSource.onmessage = receivedStatus;
	$('title').html('Table Editor ' + escapeHTML(myTableName));

	$('#batchUpdate').click(batchUpdate);
	$('#batchCancel').click(batchCancel);
}
