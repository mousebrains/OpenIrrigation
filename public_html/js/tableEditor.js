var myTableInfo = {};

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
		var val = (x == null) ? "" : " value='" + x[col] + "'";
		row += "<td><input";
		row += " type='" + a['inputtype'] + "'";
		if (a['valmin'] != null) {row += " min='" + a['valmin'] + "'";}
		if (a['valmax'] != null) {row += " max='" + a['valmax'] + "'";}
		if (a['valstep'] != null) {row += " step='" + a['valstep'] + "'";}
		row += " name='" + col + "'" + val;
		if (a['placeholder'] != '') {
			row += " placeholder='" + a['placeholder'] + "'";
		}
		if (a['qrequired'] == 't') {row += ' required';}
		row += form;
		if (x != null) {
			row += "<input type='hidden' name='" + col + "Prev'" + val + form;
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
		tbl.append(buildRow(x, false));
	});
	tbl.append(buildRow(null, true));
	$('.formDelete').submit({'url': 'tableRowDelete.php'}, OI_processForm);
	$('.formUpdate').submit({'url': 'tableRowUpdate.php'}, OI_processForm);
	$('.formInsert').submit({'url': 'tableRowInsert.php'}, OI_processForm);
}

function receivedStatus(event) {
	var data = JSON.parse(event.data);
	if ('burp' in data) { return; } // Nothing to do on burp messages
	if ('info' in data) {buildTable(data['info']);}
	if ('data' in data) {buildBody(data['data']);}
}

if (typeof(EventSource) != "undefined") {
	var statusSource = new EventSource("tableStatus.php?tbl=" + myTableName);
	statusSource.onmessage = receivedStatus;
	$('title').html('Table Editor ' + myTableName);
}
