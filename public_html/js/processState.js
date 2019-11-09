function receivedStatus(event) {
	var data = JSON.parse(event.data);
	if ('burp' in data) { return; } // Nothing to do on burp messages
	data.forEach(function(x) {
		var t = new Date(x[1] * 1000);
		$('#messages').prepend('<tr>' 
			+ '<th>' + x[0] + '</th>'
			+ '<td>' + t.toLocaleString() + '</td>'
			+ '<td>' + x[2] + '</td>'
			+ '</tr>');
	});
}

if (typeof(EventSource) != "undefined") {
	var statusSource = new EventSource("processStatus.php");
	statusSource.onmessage = receivedStatus;
}
