$(function() {
	let chart = null;
	let stationData = [];

	function fetchAndRender(hours) {
		$.ajax({
			type: 'POST',
			url: 'flowGraphData.php',
			data: { hours: hours },
			dataType: 'json'
		}).done(function(data) {
			if (data.success === false) {
				OI_toast(data.message, true);
				return;
			}
			stationData = data.stations || [];
			renderChart(data.flow || [], hours);
		}).fail(function(jqXHR, textStatus) {
			OI_toast('Request failed: ' + textStatus, true);
		});
	}

	function renderChart(flow, hours) {
		if (chart) {
			chart.destroy();
			chart = null;
		}

		const points = flow.map(function(row) {
			return { x: Number(row[0]) * 1000, y: Number(row[1]) };
		});

		const timeFormat = hours <= 12 ? 'HH:mm' : 'MMM d HH:mm';

		const ctx = document.getElementById('flowChart').getContext('2d');
		chart = new Chart(ctx, {
			type: 'line',
			data: {
				datasets: [{
					label: 'Flow (GPM)',
					data: points,
					borderColor: 'rgba(54, 162, 235, 1)',
					backgroundColor: 'rgba(54, 162, 235, 0.2)',
					fill: true,
					pointRadius: 0,
					tension: 0.2
				}]
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
							tooltipFormat: 'MMM d, yyyy HH:mm',
							displayFormats: {
								minute: timeFormat,
								hour: timeFormat
							}
						},
						title: { display: false }
					},
					y: {
						beginAtZero: true,
						title: {
							display: true,
							text: 'Flow (GPM)'
						}
					}
				},
				plugins: {
					tooltip: {
						callbacks: {
							afterBody: function(context) {
								if (!context.length) return '';
								const t = context[0].parsed.x / 1000;
								const active = [];
								for (let i = 0; i < stationData.length; i++) {
									const s = stationData[i];
									const tOn = Number(s[1]);
									const tOff = Number(s[2]);
									if (tOn <= t && t <= tOff) {
										active.push(s[0]);
									}
								}
								if (!active.length) return '';
								return '\nStations: ' + active.map(escapeHTML).join(', ');
							}
						}
					},
					legend: { display: false }
				}
			}
		});
	}

	$('.hour-buttons button').on('click', function() {
		$('.hour-buttons button').removeClass('active');
		$(this).addClass('active');
		fetchAndRender($(this).data('hours'));
	});

	fetchAndRender(24);
});
