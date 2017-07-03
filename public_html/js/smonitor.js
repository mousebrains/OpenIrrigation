var activeEntries = new Set();
var pastEntries = {};
var nextEntries = {};

if (typeof(EventSource) != "undefined") {
	var runningSource = new EventSource("running.php");
	runningSource.onmessage = function(event) {
		let data = JSON.parse(event.data);
                let active = new Set();
                let past = {};
                let pending = {};
                let a = data['dtPast'];
                if (a) { 
		    for (let k in a) { 
		        if (k in past) {
		            past[k] += a[k]; 
                        } else {
		            past[k] = a[k]; 
                        }
                    }
                }
                a = data['dtpActive'];
                if (a) { 
		    for (let k in a) { 
		        active.add(k); 
		        if (k in past) {
		            past[k] += a[k]; 
                        } else {
		            past[k] = a[k]; 
                        }
                    }
                }
                a = data['dtPending'];
                if (a) { 
		    for (let k in a) { 
		        if (k in pending) {
		            pending[k] += a[k]; 
                        } else {
		            pending[k] = a[k]; 
                        }
                    }
                }
                a = data['dtSched'];
                if (a) { 
		    for (let k in a) { 
		        if (k in pending) {
		            pending[k] += a[k]; 
                        } else {
		            pending[k] = a[k]; 
                        }
                    }
                }
                if (a) { for (let k in a) { pending[k] += a[k]; } }
                a = data['dtActive'];
                if (a) { 
		    for (let k in a) { 
		        active.add(k); 
		        if (k in pending) {
		            pending[k] += a[k]; 
                        } else {
		            pending[k] = a[k]; 
                        }
                    }
                }

                for (let k of active) { // Highlight active entries
                    if (!activeEntries.has(k)) {
                        activeEntries.add(k);
                        $("#a" + k).css('background-color', '#8FBC8F');
                    }
                }

                for (let k of activeEntries) { // Make invisble old entries
                    if (!active.has(k)) {
                        activeEntries.delete(k);
                        $("#a" + k).css('background-color', '#000000');
                    }
                }

		for (let k in past) {
		    if (!(k in pastEntries) || (pastEntries[k] != past[k])) {
                        pastEntries[k] = past[k]
                        let m = Math.ceil((past[k] % 3600) / 60);
			$("#p" + k).html(Math.floor(past[k] / 3600).toString() + 
				(m >= 10 ? ":" : ":0") + m.toString());
		    }
		}

		for (let k in pending) {
		    if (!(k in nextEntries) || (nextEntries[k] != pending[k])) {
                        nextEntries[k] = pending[k]
                        let m = Math.ceil((pending[k] % 3600) / 60);
			$("#n" + k).html(Math.floor(pending[k] / 3600).toString() + 
				(m >= 10 ? ":" : ":0") + m.toString());
		    }
		}
	};
}
