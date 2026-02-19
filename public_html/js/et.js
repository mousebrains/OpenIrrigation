$(function() {
	var etChart = null;

	$(document).on('change', '.et-daily', function() {
		// TODO: implement daily ET chart
	});

	$(document).on('change', '.et-annual', function() {
		var cb = this;
		var id = $(cb).data('codigo');

		if (!cb.checked) {
			if (etChart) {
				etChart.destroy();
				etChart = null;
			}
			return;
		}

		// Uncheck other Annual checkboxes so only one is active
		$('.et-annual').not(cb).prop('checked', false);

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
	});

	// 7-day centered moving average for an array of {x, y} points
	function movingAvg(pts, halfWin) {
		var out = [];
		var n = pts.length;
		for (var i = 0; i < n; i++) {
			var lo = Math.max(0, i - halfWin);
			var hi = Math.min(n - 1, i + halfWin);
			var sum = 0;
			for (var j = lo; j <= hi; j++) {
				sum += pts[j].y;
			}
			out.push({ x: pts[i].x, y: sum / (hi - lo + 1) });
		}
		return out;
	}

	function renderAnnualChart(rows) {
		if (etChart) {
			etChart.destroy();
			etChart = null;
		}

		// rows: [doy, mn, q10, value, q90, mx]  (FETCH_NUM indices 0-5)
		var mxPts = [];
		var q90Pts = [];
		var medPts = [];
		var q10Pts = [];
		var mnPts = [];

		for (var i = 0; i < rows.length; i++) {
			var doy = Number(rows[i][0]);
			var d = new Date(2024, 0, doy);
			var t = d.getTime();

			mnPts.push({ x: t, y: Number(rows[i][1]) });
			q10Pts.push({ x: t, y: Number(rows[i][2]) });
			medPts.push({ x: t, y: Number(rows[i][3]) });
			q90Pts.push({ x: t, y: Number(rows[i][4]) });
			mxPts.push({ x: t, y: Number(rows[i][5]) });
		}

		// Apply 7-day centered moving average (halfWin=3 → 7-point window)
		mxPts = movingAvg(mxPts, 3);
		q90Pts = movingAvg(q90Pts, 3);
		medPts = movingAvg(medPts, 3);
		q10Pts = movingAvg(q10Pts, 3);
		mnPts = movingAvg(mnPts, 3);

		var peach = 'rgba(255, 180, 120, 0.3)';

		var ctx = document.getElementById('etChart').getContext('2d');
		etChart = new Chart(ctx, {
			type: 'line',
			data: {
				datasets: [
					{ // 0: mx – fill down to q90 (peach)
						label: 'Max',
						data: mxPts,
						borderColor: 'transparent',
						backgroundColor: peach,
						fill: '+1',
						pointRadius: 0,
						tension: 0.3
					},
					{ // 1: q90 – fill down to q10 (green)
						label: '90th pctl',
						data: q90Pts,
						borderColor: 'transparent',
						backgroundColor: 'rgba(100, 190, 100, 0.25)',
						fill: '+2',
						pointRadius: 0,
						tension: 0.3
					},
					{ // 2: median – solid blue line
						label: 'Median ET',
						data: medPts,
						borderColor: 'rgba(54, 120, 220, 1)',
						backgroundColor: 'rgba(54, 120, 220, 1)',
						fill: false,
						pointRadius: 0,
						borderWidth: 2,
						tension: 0.3
					},
					{ // 3: q10 – fill down to mn (peach)
						label: '10th pctl',
						data: q10Pts,
						borderColor: 'transparent',
						backgroundColor: peach,
						fill: '+1',
						pointRadius: 0,
						tension: 0.3
					},
					{ // 4: mn – no fill (bottom boundary)
						label: 'Min',
						data: mnPts,
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
							return item.datasetIndex === 2;
						}
					},
					legend: { display: false }
				}
			}
		});
	}
});
