<?php
require_once 'php/ParDB.php';

echo "<script>
var sensorMap = new Object();\n";
$results = $parDB->query('SELECT addr,pocFlow.name,toHertz*K as K,offset FROM pocFlow INNER JOIN sensor ON pocFlow.sensor==sensor.id;');
while ($row = $results->fetchArray()) {
	echo "sensorMap['" . $row['addr'] . "']={name:'" . $row['name']
		. "', offset:" . $row['offset'] . ", K:" . $row['K'] . "};\n";
}
echo "</script>
<div id='topnav'>
 <div id='statusBlock'>Status info</div>
 <ul>
  <li id='topdropdown'>
    <a href='javascript:void(0)' id='topdropbtn'>&#9776;</a>
    <div id='top-dropdown-content'>
      <a href='index.php'>Manual Operations</a>
      <a href='monitor.php'>Monitor Operations</a>
      <a href='program.php'>Programs</a>
      <a href='programStation.php'>Program Station</a>
      <a href='event.php'>Events</a>
      <a href='programEvent.php'>Program Events</a>
      <a href='station.php'>Stations</a>
      <a href='ETStn.php'>ET Stations</a>
      <a href='site.php'>Site Edit</a>
      <a href='user.php'>User Edit</a>
      <a href='email.php'>EMail Edit</a>
      <a href='controller.php'>Controller Edit</a>
      <a href='sensor.php'>Decoder/Sensor Edit</a>
      <a href='poc.php'>Point-of-connect Edit</a>
      <a href='pocFlow.php'>Flow Sensor Edit</a>
      <a href='pocMV.php'>Master Valve Edit</a>
      <a href='pocPump.php'>Booster Pump Edit</a>
      <a href='soil.php'>Soil Edit</a>
      <a href='crop.php'>Crop Edit</a>
      <a href='params.php'>Parameter Edit</a>
      <a href='ET.php'>ET Daily</a>
      <a href='ETannual.php'>ET Annual</a>
    </div>
  </li>
 </ul>
</div>

<script src='js/status.js'></script>
";
?>
