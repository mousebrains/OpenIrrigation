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

	// Next local midnight strictly after epoch milliseconds t
	function nextMidnight(t) {
		const d = new Date(t);
		d.setHours(24, 0, 0, 0);
		return d.getTime();
	}

	function renderChart(flow, hours) {
		if (chart) {
			chart.destroy();
			chart = null;
		}

		const points = [];
		const volPoints = [];
		let prev = null;
		flow.forEach(function(row) {
			const t = Number(row[0]) * 1000;
			const f = Number(row[1]);
			const v = Number(row[2]);
			if (prev) {
				// The server resets cumulative volume at each local
				// midnight; insert the day-end value and a zero at every
				// midnight crossed so the reset draws as a vertical drop
				// instead of a slow ramp to the next day's first reading
				let vol = prev.vol;
				let from = prev.t;
				for (let m = nextMidnight(prev.t); m <= t; m = nextMidnight(m)) {
					vol += prev.flow * (m - from) / 60000;
					volPoints.push({x: m, y: vol});
					volPoints.push({x: m, y: 0});
					vol = 0;
					from = m;
				}
			}
			points.push({x: t, y: f});
			volPoints.push({x: t, y: v});
			prev = {t: t, flow: f, vol: v};
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
					// 'before' holds each value flat until the next point
					// (sample-and-hold); 'after' extends the next value backward
					stepped: 'before',
					yAxisID: 'y'
				}, {
					label: 'Volume (gal)',
					data: volPoints,
					borderColor: 'rgba(255, 159, 64, 1)',
					backgroundColor: 'rgba(255, 159, 64, 0.2)',
					fill: false,
					pointRadius: 0,
					yAxisID: 'y1'
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
							text: 'Flow (GPM)',
							color: 'rgba(54, 162, 235, 1)'
						},
						ticks: { color: 'rgba(54, 162, 235, 1)' }
					},
					y1: {
						beginAtZero: true,
						position: 'right',
						title: {
							display: true,
							text: 'Volume (gal)',
							color: 'rgba(255, 159, 64, 1)'
						},
						ticks: { color: 'rgba(255, 159, 64, 1)' },
						grid: { drawOnChartArea: false }
					}
				},
				plugins: {
					tooltip: {
						callbacks: {
							afterBody: function(context) {
								if (!context.length) {return '';}
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
								if (!active.length) {return '';}
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
