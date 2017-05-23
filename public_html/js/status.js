if (typeof(EventSource) != "undefined") {
	var statusSource = new EventSource("status.php");
	statusSource.onmessage = function(event) {
		let data = JSON.parse(event.data);
		let a = data["curr"];
		let msg = '';
		if (a.length) {
			let t = new Date(a[0] * 1000);
			msg = t.toTimeString().substr(0,9) + " " + a[1] + " V " + a[2] +  " mA";
		}
		a = data["sensor"];
		for (let i = 0; i < a.length; ++i) {
			let t = new Date(a[i][0] * 1000);
			let key = a[i][1];
			msg += ", " + t.toTimeString().substr(0,9);
			if (key in sensorMap) {
				let flow = (a[i][2]*sensorMap[key]['K'])-sensorMap[key]['offset'];
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
