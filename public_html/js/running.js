var activeData = new Set();
var pastData = new Set();
var pendingData = new Set();

if (typeof(EventSource) != "undefined") {
	var runningSource = new EventSource("running.php");
	runningSource.onmessage = function(event) {
		let data = JSON.parse(event.data);
                let a = data['dtPast'];
                let b = data['dtPending'];
                let c = data['dtActive'];
		if (a) { // Something in the past
			for (let k in a) { // Loop over keys in past
				if ((!b || !(k in b)) && !pastData.has(k) && !activeData.has(k)) {
					$("#n" + k).css('background-color', '#FDF5E6');
				}
			}
		}
		if (b) { // Something in the pending
			for (let k in b) { // Loop over keys in pending
				if (!pendingData.has(k) && !activeData.has(k)) {
					$("#n" + k).css('background-color', '#AFEEEE');
					if (pastData.has(k)) { pastData.delete(k); }
				}
			}
		}

                if (c) { // change from run to stop form, if needed
			for (let k in c) { // Loop over keys
				if (!activeData.has(k)) {
					$("#a" + k).css('display', 'none');
					$("#b" + k).css('display', 'inline');
					$("#n" + k).css('background-color', '#8FBC8F');
					activeData.add(k)
					if (pendingData.has(k)) { pendingData.delete(k); }
					if (pastData.has(k)) { pastData.delete(k); }
				}
				$("#bc" + k).html((c[k]/60).toFixed(1));
			}
		}

		for (let k of pastData) { // Loop over already set keys in past
			if (!a || !(k in a)) {
				$("#n" + k).css('background-color', '#000000');
				pastData.delete(k);
			}
		}

		for (let k of pendingData) { // Loop over already set keys in pending
			if (!b || !(k in b)) {
				$("#n" + k).css('background-color', '#000000');
				pendingData.delete(k);
			}
		}

		for (let k of activeData.keys()) { // Loop over already set keys
			if (!c || !(k in c)) { // change from stop to run form
				$("#a" + k).css('display', 'inline');
				$("#b" + k).css('display', 'none');
				activeData.delete(k);
			}
		}
	};
}
