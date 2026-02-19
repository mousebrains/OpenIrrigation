var etChart = null;

function dailyClick(id) {
	void id;
	// TODO: implement daily ET chart
}

function yearlyClick(id) {
	var cb = document.getElementById('y' + id);
	if (!cb.checked) {
		if (etChart) {
			etChart.destroy();
			etChart = null;
		}
		return;
	}

	// Uncheck other Annual checkboxes so only one is active
	$('input[id^="y"]').not(cb).prop('checked', false);

	$.ajax({
		type: 'POST',
		url: 'etAnnual.php',
		data: { codigo: id },
		dataType: 'json'
	}).done(function(rows) {
		if (rows && rows.success === false) {
			OI_toast(rows.message, true);
			return;
		}
		renderAnnualChart(rows || []);
	}).fail(function(jqXHR, textStatus) {
		OI_toast('Request failed: ' + textStatus, true);
	});
}

function renderAnnualChart(rows) {
	if (etChart) {
		etChart.destroy();
		etChart = null;
	}

	// Convert DOY to pseudo-dates in leap year 2024 for time axis display
	var meanPts = [];
	var upperPts = [];
	var lowerPts = [];

	for (var i = 0; i < rows.length; i++) {
		var doy = Number(rows[i][0]);
		var mean = Number(rows[i][1]);
		var sd = rows[i][2] !== null ? Number(rows[i][2]) : 0;

		// Build a Date from day-of-year in 2024 (leap year)
		var d = new Date(2024, 0, doy);
		var t = d.getTime();

		meanPts.push({ x: t, y: mean });
		upperPts.push({ x: t, y: mean + sd });
		lowerPts.push({ x: t, y: Math.max(0, mean - sd) });
	}

	var ctx = document.getElementById('etChart').getContext('2d');
	etChart = new Chart(ctx, {
		type: 'line',
		data: {
			datasets: [
				{
					label: '+1\u03c3',
					data: upperPts,
					borderColor: 'transparent',
					backgroundColor: 'rgba(54, 162, 235, 0.15)',
					fill: '+1',
					pointRadius: 0,
					tension: 0.3
				},
				{
					label: 'Mean ET',
					data: meanPts,
					borderColor: 'rgba(54, 162, 235, 1)',
					backgroundColor: 'rgba(54, 162, 235, 1)',
					fill: false,
					pointRadius: 0,
					borderWidth: 2,
					tension: 0.3
				},
				{
					label: '\u20131\u03c3',
					data: lowerPts,
					borderColor: 'transparent',
					backgroundColor: 'transparent',
					fill: false,
					pointRadius: 0,
					tension: 0.3
				}
			]
		},
		options: {
			responsive: true,
			interaction: {
				mode: 'nearest',
				axis: 'x',
				intersect: false
			},
			scales: {
				x: {
					type: 'time',
					time: {
						unit: 'month',
						tooltipFormat: 'd MMM',
						displayFormats: {
							month: 'd MMM'
						}
					},
					title: { display: false }
				},
				y: {
					beginAtZero: true,
					title: {
						display: true,
						text: 'ET (in/day)'
					}
				}
			},
			plugins: {
				tooltip: {
					filter: function(item) {
						return item.datasetIndex === 1;
					}
				},
				legend: { display: false }
			}
		}
	});
}
