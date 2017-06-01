var activeEntries = {};
var colorEntries = {};

if (typeof(EventSource) != "undefined") {
	var runningSource = new EventSource("running.php");
	runningSource.onmessage = function(event) {
		let data = JSON.parse(event.data);
                let color = {};
                let active = {};
                let a = data['dtPast'];
                if (a) { for (let k in a) { color[k] = "#FDDEB3"; } }
                a = data['dtPending'];
                if (a) { for (let k in a) { color[k] = "#AFEEEE"; } }
                a = data['dtSched'];
                if (a) { 
			for (let k in a) { 
				color[k] = "#4F8C4F";
				active[k] = a[k];
			} 
		}
                a = data['dtActive'];
                if (a) { 
			for (let k in a) { 
				color[k] = "#8FBC8F"; 
				active[k] = a[k];
			} 
		}

                for (let k in colorEntries) {
                  	if (!(k in color)) {
				$("#n" + k).css('background-color', '#000000');
				delete colorEntries[k];
			}
		}

                for (let k in color) {
                  	if (!(k in color) || (colorEntries[k] != color[k])) {
				$("#n" + k).css('background-color', color[k]);
				colorEntries[k] = color[k];
			}
		}

		for (let k in activeEntries) {
			if (!(k in active)) {
				$("#a" + k).css('display', 'inline');
				$("#b" + k).css('display', 'none');
				delete activeEntries[k];
			}
		}

		for (let k in active) {
			if (!(k in activeEntries)) {
				$("#a" + k).css('display', 'none');
				$("#b" + k).css('display', 'inline');
				activeEntries[k] = 1;
			}
                        let m = Math.ceil((active[k] % 3600) / 60);
			$("#bc" + k).html(Math.floor(active[k] / 3600).toString() + 
				(m >= 10 ? ":" : ":0") + m.toString());
		}
	};
}
