var myTableInfo = {};
var myReferenceInfo = {};
var mySecondaryInfo = {};

function buildTable(info) {
	myTableInfo = info;

	var row = '<tr>';
	row += '<th></th>'; // Delete
	row += '<th></th>'; // Update

	info.forEach(function(x) {
		row += '<th>' + x['label'] + '</th>';
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
	var col = a['col'];
	var val = (x != null) ? x[col] : null;
	var id = (x != null) ? x['id'] : null;
	var qMultiple = col in mySecondaryInfo;
	var sec = qMultiple ? mySecondaryInfo[col] : null;
	var msg = "<select name='" + col + (qMultiple ? "[]'" : "'");
	if (a['qrequired'] == true) msg += ' required';
	if (qMultiple) {
		val = (id in sec) ? sec[id].join() : '';  // Redo val for multiples
		msg += ' multiple';
	}
	msg += form;
	myReferenceInfo[col].forEach(function(y) {
		var yid = y['id'];
		msg += "<option value='" + yid + "'";
		if ((yid == val) || (qMultiple && (id in sec) && sec[id].includes(yid))) {
			msg += " selected";
		} 
		msg += ">" + y['name'] + "</option>";
	});
	msg += "</select>";
	if (x != null) {
		msg += "<input type='hidden' name='" + col + "Prev'"
			+ " value='" + val + "'" + form;
	}
	return msg;
}

function mkTextArea(a, x, form) {
	var col = a['col'];
	var val = (x != null) && (col in x) && (x[col] != null) ? x[col] : "";
	var msg = "<textarea rows='2' cols='20' name='" + col + "'";
	if (a['qrequired'] == true) msg += ' required';
	msg += form;
	msg += val;
	msg += "</textarea>";
	if (x != null) {
		msg += "<input type='hidden' name='" + col + "Prev'"
			+ " value='" + val + "'" + form;
	}
	return msg;
}

function mkInputField(a, x, form) {
	var col = a['col'];
	var rawVal = (x != null) && (col in x) && (x[col] != null) ? x[col] : null 
	var val = rawVal == null ? "" : ("value='" + rawVal + "'");
	var msg = "<input type='" + a['inputtype'] + "'";
	if (a['inputtype'] == 'password') msg += " autocomplete='on'";
	if (a['valmin'] != null) msg += " min='" + a['valmin'] + "'";
	if (a['valmax'] != null) msg += " max='" + a['valmax'] + "'";
	if (a['valstep'] != null) msg += " step='" + a['valstep'] + "'";
	msg += " name='" + col + "'" + val;
	if (a['placeholder'] != '') msg += " placeholder='" + a['placeholder'] + "'";
	if (a['qrequired'] == true) msg += ' required';
	if ((a['inputtype'] == 'checkbox') && rawVal) msg += ' checked';
	msg += form;
	if (x != null) msg += "<input type='hidden' name='" + col + "Prev'" + val + form;
	return msg;
}

function buildRow(x, qInsert) {
	var id = (x == null) ? 'Insert' : x['id'];
	var form = " form='f" + id + "'>";
	var tbl = "<input type='hidden' name='tableName' value='" + myTableName + "'>";
	var row = '<tr>'
	if (qInsert) { // Insertion row
		row += "<td colspan=2>";
		row += "<form class='formInsert' id='f" + id + "'>";
		row += tbl;
		row += "<input type='submit' value='Insert'>";
		row += "</form>";
		row += "</td>";
	} else { // data row
		var idIn = "<input type='hidden' name='id' value='" + id + "'>";
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
		var col = a['col'];
		row += "<td>";
		if (a['inputtype'] == 'textarea') {
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
	var tbl = $('tbody');
	tbl.find('tr').remove(); // remove all rows in the body
	data.forEach(function(x) {
		if (!('qhide' in x) || !x['qhide']) {
			tbl.append(buildRow(x, false));
		}
	});
	tbl.append(buildRow(null, true));
	$('.formDelete').submit({'url': 'tableRowDelete.php'}, OI_processForm);
	$('.formUpdate').submit({'url': 'tableRowUpdate.php'}, OI_processForm);
	$('.formInsert').submit({'url': 'tableRowInsert.php'}, OI_processForm);
}

function receivedStatus(event) {
	var data = JSON.parse(event.data);
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
	if ('data' in data) {buildBody(data['data']);}
}

if (typeof(EventSource) != "undefined") {
	var base = 'tableStatus.php';
	var parts = window.location.href.split('?'); // Get parameters
	var url = parts.length > 1 ? (base + '?' + parts.slice(-1)) : base;
	var statusSource = new EventSource(url);
	statusSource.onmessage = receivedStatus;
	$('title').html('Table Editor ' + myTableName);
}
