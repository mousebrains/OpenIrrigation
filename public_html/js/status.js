var statusCurrent;
var statusSensor;
var statusnOn;
var statusnPending;

if (typeof(EventSource) != "undefined") {
	var statusSource = new EventSource("status.php");
	statusSource.onmessage = function(event) {
		let data = JSON.parse(event.data);
                let msg = '';
                if ('curr' in data) {
                  let a = data['curr'];
                  let t = new Date(a[0] * 1000);
                  let msg = t.toTimeString().substr(0,9) + a[1] + " V " + a[2] + " mA";
                  if (msg != statusCurrent) {
                    $("#statusCurrent").html(msg);
                    statusCurrent = msg;
                  }
                }
                if ('sensor' in data) {
                  let a = data['sensor'];
                  let msg = '';
                  for (let i = 0; i < a.length; ++i) {
                    let b = a[i];
                    let t = new Date(b[0] * 1000);
                    let key = b[1];
                    if (i != 0) { msg += ", "; }
                    if (key in sensorMap) {
                      let info = sensorMap[key];
                      let flow = (b[2] * info['K']) - info['offset'];
                      msg += info['name'] + "=" + Math.max(0,flow).toFixed(1);
                    } else {
                      msg += "sensor(" + key + ")=" + b[2];
                    }
                  }
                  if (msg != statusSensor) {
                    $("#statusFlow").html(statusSensor);
                    statusSensor = msg;
                  }
                }
                if (('nOn' in data) && (data['nOn'] != statusOn)) {
                  statusnOn = data['nOn'];
                  $("#statusActive").html("#On=" + statusOn);
                }
                if (('nPend' in data) && (data['nPend'] != statusnPending)) {
                  statusnPending = data['nPend'];
                  $("#statusPending").html("#Pending=" + statusnPending);
                }
	};
}
