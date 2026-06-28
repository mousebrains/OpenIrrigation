let statusControllers;
let statusPOCs;

function updateSystemctlStatus(val, id) {
	$(id).html(escapeHTML(val));
	$(id).css('color', val === "active" ? "#000000" : "#FF0000");
}

function updateSystemctl(info) {
	if (info.length !== 2) {
		return;
	}
	updateSystemctlStatus(info[0], '#statusOITDI');
	updateSystemctlStatus(info[1], '#statusOISched');
}

// Inline-filter status badge: degradation %/state, colored by service state.
function updateFilter(f) {
	const el = $('#statusFilter');
	if (!f || !f.state) { // no status row, or not yet classified
		el.html('').attr('class', '').removeAttr('title');
		return;
	}
	let label = 'Filter';
	if (f.degradation !== null && f.degradation !== undefined) {
		label += ` ${f.degradation}%`;
	} else if (f.estDP !== null && f.estDP !== undefined) {
		label += ` ${f.estDP}PSI`;
	} else {
		label += ` ${f.state}`;
	}
	const tip = [];
	if (f.degradation !== null && f.degradation !== undefined) {tip.push(`flow degradation ${f.degradation}%`);}
	if (f.estDP !== null && f.estDP !== undefined) {tip.push(`est dP ${f.estDP} PSI`);}
	if (f.gallons !== null && f.gallons !== undefined) {tip.push(`${f.gallons} gal since clean`);}
	if (f.forecastDays !== null && f.forecastDays !== undefined) {tip.push(`~${f.forecastDays} d to service`);}
	el.html(escapeHTML(label))
		.attr('class', `filter-${f.state}`)
		.attr('title', tip.length ? tip.join(', ') : `filter ${f.state}`);
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
		if ('filter' in data) { // Inline-filter status badge
			updateFilter(data['filter']);
		}
		if ('system' in data) { // systemctl
			updateSystemctl(data['system']);
		}
	});
}
