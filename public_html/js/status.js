if (typeof(EventSource) != "undefined") {
	var source = new EventSource("status.php");
	source.onmessage = function(event) {
		var data = JSON.parse(event.data);
		var a = data["curr"];
		var msg = '';
		if (a.length) {
			var t = new Date(a[0] * 1000);
			msg = t.toTimeString().substr(0,9) + " " + a[1] + " V " + a[2] +  " mA";
		}
		a = data["sensor"];
		for (var i = 0; i < a.length; ++i) {
			var t = new Date(a[i][0] * 1000);
			var key = a[i][1];
			msg += ", " + t.toTimeString().substr(0,9);
			if (key in sensorMap) {
				var flow = (a[i][2]*sensorMap[key]['K'])-sensorMap[key]['offset'];
 				msg += " " + sensorMap[key]['name'] + "=" 
					+ Math.max(0,flow).toFixed(1);
			} else {
 				msg += " sensor(" + key + ")=" + a[i][2];
			}
		}
                msg += ", nOn=" + data["nOn"];
                msg += ", nPend=" + data["nPend"];
		$("#statusBlock").html(msg);
	};
}
