let statusControllers;
let statusPOCs;

function updateSystemctlStatus(val, id) {
	$(id).html(escapeHTML(val));
	$(id).css('color', val === "active" ? "#000000" : "#FF0000");
}

function updateSystemctl(info) {
	if (info.length !== 2) {
		console.log('Invalid systemctl info block');
		console.log(info);
		return;
	}
	updateSystemctlStatus(info[0], '#statusOITDI');
	updateSystemctlStatus(info[1], '#statusOISched');
}

$('#runScheduler').submit({'url': 'runScheduler.php'}, OI_processForm);

// Hamburger menu: click/touch toggle (replaces hover-only)
$('#topdropbtn').on('click', (e) => {
	e.preventDefault();
	$('#top-dropdown-content').toggleClass('open');
	$('#topdropdown').toggleClass('open');
});
$(document).on('click', (e) => {
	if (!$(e.target).closest('#topdropdown').length) {
		$('#top-dropdown-content').removeClass('open');
		$('#topdropdown').removeClass('open');
	}
});
$('#top-dropdown-content a').on('click', () => {
	$('#top-dropdown-content').removeClass('open');
	$('#topdropdown').removeClass('open');
});

if (typeof EventSource !== "undefined") {
	const statusSource = OI_connectSSE("status.php", (event) => {
		const data = JSON.parse(event.data);
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
			const t = new Date(data['tcurrent'] * 1000);
			$('#statusCurrent').html(`${escapeHTML(statusControllers[data['ctl']])} ${data['volts']}V ${data['mamps']}mA ${t.toTimeString().slice(0,9)}`);
		}
                if ('poc' in data) { // Flow
			const t = new Date(data['tflow'] * 1000);
			$('#statusFlow').html(`${escapeHTML(statusPOCs[data['poc']])} ${data['flow']}GPM ${t.toTimeString().slice(0,9)}`);
		}
		if ('non' in data) { // Number on
			$('#statusActive').html(`#On=${data['non']}`);
			$('#statusPending').html(`#Pend=${data['npending']}`);
		}
		if ('system' in data) { // systemctl
			updateSystemctl(data['system']);
		}
	});
}
