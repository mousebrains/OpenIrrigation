var statusCurrent;
var statusSensor;
var statusOn;
var statusPending;

if (typeof(EventSource) != "undefined") {
  var statusSource = new EventSource("status.php");
  statusSource.onmessage = function(event) {
		let data = JSON.parse(event.data);
                let msg = '';
                if ('curr' in data) {
                  let a = data['curr'];
                  let msg = '';
                  for (let i = 0; i < a.length; ++i) {
                    let b = a[i];
                    let t = new Date(b[1] * 1000);
                    if (i != 0) {msg += ", ";}
                    msg += b[0] + " " + t.toTimeString().substr(0,9) + " " + b[2] + " V " + b[3] + " mA";
                  }
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
                    let t = new Date(b[1] * 1000);
                    if (i != 0) { msg += ", "; }
                    msg += b[0] + " " + t.toTimeString().substr(0,9) + " " + b[2] + " GPM";
                  }
                  if (msg != statusSensor) {
                    $("#statusFlow").html(statusSensor);
                    statusSensor = msg;
                  }
                }
                if (('nOn' in data) && (data['nOn'] != statusOn)) {
                  statusOn = data['nOn'];
                  $("#statusActive").html("#On=" + statusOn);
                }
                if (('nPend' in data) && (data['nPend'] != statusPending)) {
                  statusPending = data['nPend'];
                  $("#statusPending").html("#Pending=" + statusPending);
                }
	};
}
