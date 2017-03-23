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
			console.log(t);
			msg += ", " + t.toTimeString().substr(0,9) + " sensor(" + a[i][1] + ")=" + a[i][2];
		}
                msg += ", nOn=" + data["nOn"];
		$("#statusBlock").html(msg);
	};
}
