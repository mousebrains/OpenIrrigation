// Site map: cached aerial imagery with the map features (valve boxes, shutoffs,
// hose bibs, ...) on top.  A valve box's popup lists its valves with their
// stations' programs and last/next runs; a box with a valve on now pulses.

const MAP_REFRESH_MS = 60000; // re-read mapData.php this often
const MAP_BASE_KEY = 'oiMapBase'; // localStorage: the last base layer chosen
const MAP_MAX_ZOOM = 23; // Leaflet scales the finest cached tiles past their zoom

const mapKinds = [ // [key, legend label], in legend order; webList grp='mapKind'
	['valveBox', 'Valve box'],
	['equipment', 'Controller equipment'],
	['shutoff', 'Shutoff'],
	['backflow', 'Backflow preventer'],
	['drain', 'Drain'],
	['hoseBib', 'Hose bib'],
	['other', 'Other'],
];

let oiMap = null;
const mapMarkers = new Map(); // feature id -> marker
const mapGroups = {}; // kind -> L.layerGroup

function mapStorage(key, val) { // localStorage can be missing or throw
	try {
		if (val === undefined) {return window.localStorage.getItem(key);}
		window.localStorage.setItem(key, val);
	} catch {
		// a private window or blocked storage: just don't remember
	}
	return null;
}

function mapTime(epoch) {
	if (epoch === null || epoch === undefined) {return '&mdash;';}
	const when = new Date(epoch * 1000);
	const opts = {month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'};
	if (when.getFullYear() !== new Date().getFullYear()) {
		opts.year = 'numeric'; // a run last December is not next December
	}
	return escapeHTML(when.toLocaleString([], opts));
}

// The label on the decoder: TDI station addresses are numbered from 1 on the
// decoders, master valves 240-243 are MV1-MV4
function decoderLabel(v) {
	if (v.addr === null) {return '';}
	if (v.devType === 'flow') {return 'flow ' + v.addr;}
	return v.addr >= 240 ? 'MV' + (v.addr - 239) : String(v.addr + 1);
}

function mapIcon(f, on) {
	const cls = 'oi-map-icon ' + escapeHTML(f.kind) + (on ? ' on' : '');
	const size = f.kind === 'valveBox' ? 20 : 14;
	return L.divIcon({className: '', html: "<div class='" + cls + "'></div>",
		iconSize: [size, size], iconAnchor: [size / 2, size / 2], popupAnchor: [0, -size / 2]});
}

function popupHTML(f, valves) {
	let html = "<div class='oi-map-popup'><h3>" + escapeHTML(f.name) + "</h3>"
		+ "<span class='kind'>" + escapeHTML(f.kindLabel) + "</span>";
	if (f.notes) {html += "<div class='notes'>" + escapeHTML(f.notes) + "</div>";}
	if (valves.length) {
		html += "<table><tr><th>Position</th><th>Label</th><th>Station</th>"
			+ "<th>Programs</th><th>Last ran</th><th>Next</th></tr>";
		for (const v of valves) {
			html += "<tr" + (v.onNow ? " class='on' title='On now'" : "") + ">"
				+ "<td>" + escapeHTML(v.position) + "</td>"
				+ "<td class='label'>" + escapeHTML(decoderLabel(v)) + "</td>"
				+ "<td>" + escapeHTML(v.station || v.sensor) + (v.onNow ? " (on)" : "") + "</td>"
				+ "<td>" + escapeHTML(v.programs) + "</td>"
				+ "<td>" + mapTime(v.lastRun) + "</td>"
				+ "<td>" + mapTime(v.nextRun) + "</td></tr>";
		}
		html += "</table>";
	}
	return html + "</div>";
}

function baseLayers(layers) {
	const bases = {};
	for (const t of layers) {
		const opts = {minZoom: 0, maxZoom: MAP_MAX_ZOOM, maxNativeZoom: t.maxNativeZoom,
			attribution: escapeHTML(t.attribution) + (t.fetched ? ', fetched ' + escapeHTML(t.fetched) : '')};
		if (Array.isArray(t.bounds)) {opts.bounds = t.bounds;}
		bases[escapeHTML(t.label)] = L.tileLayer('mapTile.php?layer=' + encodeURIComponent(t.id)
			+ '&z={z}&x={x}&y={y}', opts);
	}
	// Needs the internet; fine for the area the imagery does not cover
	bases['Street map (OpenStreetMap)'] = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
		maxZoom: MAP_MAX_ZOOM, maxNativeZoom: 19,
		attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'});
	return bases;
}

function addLegend(map) {
	const legend = L.control({position: 'bottomleft'});
	legend.onAdd = function () {
		const div = L.DomUtil.create('div', 'oi-map-legend');
		div.innerHTML = mapKinds.filter(k => mapGroups[k[0]]).map(k =>
			"<div><span class='oi-map-icon " + k[0] + "'></span>" + escapeHTML(k[1]) + "</div>").join('')
			+ "<div><span class='oi-map-icon valveBox on'></span>Valve on now</div>";
		return div;
	};
	legend.addTo(map);
}

function showMessage(map, text) {
	const msg = L.control({position: 'topright'});
	msg.onAdd = function () {
		const div = L.DomUtil.create('div', 'oi-map-message');
		div.innerHTML = escapeHTML(text);
		return div;
	};
	msg.addTo(map);
}

// Add or update a marker per feature; a refresh keeps open popups open
function updateFeatures(data) {
	const byFeature = new Map();
	for (const v of data.valves) {
		if (!byFeature.has(v.feature)) {byFeature.set(v.feature, []);}
		byFeature.get(v.feature).push(v);
	}
	const seen = new Set();
	for (const f of data.features) {
		if (f.latitude === null || f.longitude === null) {continue;}
		seen.add(f.id);
		const valves = byFeature.get(f.id) || [];
		const on = valves.some(v => v.onNow);
		const html = popupHTML(f, valves);
		let m = mapMarkers.get(f.id);
		if (m) {
			m.setLatLng([f.latitude, f.longitude]);
			if (m.oiOn !== on) {m.setIcon(mapIcon(f, on));}
			m.setPopupContent(html);
		} else {
			m = L.marker([f.latitude, f.longitude], {icon: mapIcon(f, on), title: f.name, riseOnHover: true})
				.bindPopup(html, {maxWidth: 600})
				.bindTooltip(escapeHTML(f.name), {direction: 'right', offset: [10, 0]});
			if (!mapGroups[f.kind]) {mapGroups[f.kind] = L.layerGroup().addTo(oiMap);}
			mapGroups[f.kind].addLayer(m);
			mapMarkers.set(f.id, m);
		}
		m.oiOn = on;
	}
	for (const [id, m] of mapMarkers) {
		if (!seen.has(id)) {
			m.remove();
			mapMarkers.delete(id);
		}
	}
}

function loadMap(first) {
	window.fetch('mapData.php', {method: 'POST'})
		.then(r => r.json())
		.then(data => {
			if (!data.success) {throw new Error(data.message);}
			if (first) {buildMap(data);} else {updateFeatures(data);}
		})
		.catch(e => {
			if (first) {
				document.getElementById('map').textContent = 'Unable to load the map: ' + e.message;
			} else {
				console.log('Map refresh failed', e); // keep showing the last data
			}
		});
}

function buildMap(data) {
	const center = data.site ? [data.site.latitude, data.site.longitude] : [0, 0];
	// Whole zooms (no zoomSnap): fractional zooms show seams between tiles
	oiMap = L.map('map', {maxZoom: MAP_MAX_ZOOM}).setView(center, data.site ? 18 : 2);
	const bases = baseLayers(data.layers);
	const names = Object.keys(bases);
	const saved = mapStorage(MAP_BASE_KEY);
	bases[names.includes(saved) ? saved : names[0]].addTo(oiMap);
	oiMap.on('baselayerchange', e => mapStorage(MAP_BASE_KEY, e.name));

	updateFeatures(data);
	const overlays = {};
	for (const [key, label] of mapKinds) {
		if (mapGroups[key]) {overlays[escapeHTML(label)] = mapGroups[key];}
	}
	L.control.layers(bases, overlays).addTo(oiMap);
	L.control.scale({imperial: true, metric: true}).addTo(oiMap);
	addLegend(oiMap);

	if (mapMarkers.size) {
		oiMap.fitBounds(L.featureGroup([...mapMarkers.values()]).getBounds(), {padding: [30, 30], maxZoom: 21});
	} else {
		showMessage(oiMap, 'No map features yet: add them under Map Features.');
	}
	if (!data.layers.length) {
		showMessage(oiMap, 'No cached aerial imagery: run fetchMapTiles.py (see README.md).');
	}
	window.setInterval(() => loadMap(false), MAP_REFRESH_MS);
}

loadMap(true);
