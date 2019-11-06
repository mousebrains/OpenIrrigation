var statusControllers;
var statusPOCs;

if (typeof(EventSource) != "undefined") {
	var statusSource = new EventSource("status.php");
	statusSource.onmessage = function(event) {
		var data = JSON.parse(event.data);
		if ('controllers' in data) {statusControllers = data['controllers'];}
		if ('pocs' in data) {statusPOCs = data['pocs'];}
		if ('simulation' in data) {
			if (data['simulation']) {
				$("#statusSimulation").html("Simulation");
			} else {
				$("#statusSimulation").html("");
			}
		}
                if ('ctl' in data) { // Current
			var t = new Date(data['tcurrent'] * 1000);
			$('#statusCurrent').html(statusControllers[data['ctl']]
				+ ' ' + data['volts'] + 'V ' + data['mamps'] + 'mA'
				+ ' ' + t.toTimeString().substr(0,9)
			);
		}
                if ('poc' in data) { // Flow
			var t = new Date(data['tflow'] * 1000);
			$('#statusFlow').html(statusPOCs[data['poc']]
				+ ' ' + data['flow'] + 'GPM'
				+ ' ' + t.toTimeString().substr(0,9)
			);
		}
		if ('non' in data) { // Number on
			$('#statusActive').html('#On=' + data['non']);
			$('#statusPending').html('#Pend=' + data['npending']);
		}
	};
}
