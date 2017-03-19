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
		a = data["onOff"];
		for (var i = 0; i < a.length; ++i) {
			var t1 = new Date(a[i][1] * 1000);
			var t2 = new Date(a[i][2] * 1000);
			msg += "<br>stn(" + a[i][0] + ") " 
				+ t1.toTimeString().substr(0,9) 
				+ " to " 
				+ t2.toTimeString().substr(0,9); 
		}
		$("#statusBlock").html(msg);
	};
}
