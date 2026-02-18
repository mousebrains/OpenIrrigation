function receivedStatus(event) {
	const data = JSON.parse(event.data);
	if ('burp' in data) { return; } // Nothing to do on burp messages
	data.forEach((x) => {
		const t = new Date(x[1] * 1000);
		$('#messages').prepend('<tr>'
			+ `<th>${escapeHTML(x[0])}</th>`
			+ `<td>${t.toLocaleString()}</td>`
			+ `<td>${escapeHTML(x[2])}</td>`
			+ '</tr>');
	});
}

if (typeof EventSource !== "undefined") {
	const statusSource = OI_connectSSE("processStatus.php", receivedStatus);
}
