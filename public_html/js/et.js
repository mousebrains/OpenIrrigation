$(function() {
	var etChart = null;

	$('#et-select').on('change', function() {
		var sel = $(this);
		var id = sel.val();
		var desc = sel.find('option:selected').text();

		$('#et-title').text(desc);

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
			renderAnnualChart(rows, desc);
		}).fail(function(jqXHR, textStatus) {
			OI_toast('Request failed: ' + textStatus, true);
		});
	}).trigger('change');

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

	function renderAnnualChart(rows, desc) {
		if (etChart) {
			etChart.destroy();
			etChart = null;
		}

		var annual = (rows && rows.annual) || [];
		var ytd = (rows && rows.ytd) || [];
		var prev = (rows && rows.prev) || [];

		// annual: [doy, q10, value, q90]  (FETCH_NUM indices 0-3)
		var q90Pts = [];
		var medPts = [];
		var q10Pts = [];

		for (var i = 0; i < annual.length; i++) {
			var doy = Number(annual[i][0]);
			var d = new Date(2024, 0, doy);
			var t = d.getTime();

			q10Pts.push({ x: t, y: Number(annual[i][1]) });
			medPts.push({ x: t, y: Number(annual[i][2]) });
			q90Pts.push({ x: t, y: Number(annual[i][3]) });
		}

		// ytd: [doy, value]
		var ytdPts = [];
		for (var j = 0; j < ytd.length; j++) {
			var ytdDoy = Number(ytd[j][0]);
			var ytdD = new Date(2024, 0, ytdDoy);
			ytdPts.push({ x: ytdD.getTime(), y: Number(ytd[j][1]) });
		}

		// prev: [doy, value] — previous year from today's DOY onward
		var prevPts = [];
		for (var k = 0; k < prev.length; k++) {
			var prevDoy = Number(prev[k][0]);
			var prevD = new Date(2024, 0, prevDoy);
			prevPts.push({ x: prevD.getTime(), y: Number(prev[k][1]) });
		}

		// Apply 7-day centered moving average (halfWin=3 -> 7-point window)
		q90Pts = movingAvg(q90Pts, 3);
		medPts = movingAvg(medPts, 3);
		q10Pts = movingAvg(q10Pts, 3);

		var ctx = document.getElementById('etChart').getContext('2d');
		etChart = new Chart(ctx, {
			type: 'line',
			data: {
				datasets: [
					{ // 0: q90 - fill down to q10 (green band)
						label: '90th pctl',
						data: q90Pts,
						borderColor: 'transparent',
						backgroundColor: 'rgba(100, 190, 100, 0.25)',
						fill: '+2',
						pointRadius: 0,
						tension: 0.3
					},
					{ // 1: median - solid blue line
						label: 'Median',
						data: medPts,
						borderColor: 'rgba(54, 120, 220, 1)',
						backgroundColor: 'rgba(54, 120, 220, 1)',
						fill: false,
						pointRadius: 0,
						borderWidth: 2,
						tension: 0.3
					},
					{ // 2: q10 - invisible bottom boundary
						label: '10th pctl',
						data: q10Pts,
						borderColor: 'transparent',
						backgroundColor: 'transparent',
						fill: false,
						pointRadius: 0,
						tension: 0.3
					},
					{ // 3: YTD - red/orange line
						label: new Date().getFullYear() + ' Actual',
						data: ytdPts,
						borderColor: 'rgba(220, 80, 40, 1)',
						backgroundColor: 'rgba(220, 80, 40, 1)',
						fill: false,
						pointRadius: 0,
						borderWidth: 2,
						tension: 0.3
					},
					{ // 4: Previous year - purple line
						label: (new Date().getFullYear() - 1) + ' Actual',
						data: prevPts,
						borderColor: 'rgba(140, 70, 200, 1)',
						backgroundColor: 'rgba(140, 70, 200, 1)',
						fill: false,
						pointRadius: 0,
						borderWidth: 2,
						tension: 0.3
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: true,
				aspectRatio: 2,
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
							text: desc || ''
						}
					}
				},
				plugins: {
					tooltip: {
						filter: function(item) {
							return item.datasetIndex === 1 || item.datasetIndex === 3 || item.datasetIndex === 4;
						}
					},
					legend: { display: false }
				}
			}
		});
	}
});
