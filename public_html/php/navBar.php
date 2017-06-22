<?php
require_once 'php/DB.php';

echo "<div id='topnav'><div>\n";

if ($db->querySingle("SELECT qSimulate FROM simulate LIMIT 1;")) {
  echo "  <span>Simulating</span>";
}

echo "
 <span id='statusCurrent'></span>
 <span id='statusFlow'></span>
 <span id='statusActive'></span>
 <span id='statusPending'></span>
 <ul>
  <li id='topdropdown'>
    <a href='javascript:void(0)' id='topdropbtn'>&#9776;</a>
    <div id='top-dropdown-content'>
      <a href='index.php'>Manual Operations</a>
      <a href='reportDaily.php'>Daily Summary</a>
      <a href='smonitor.php'>Summary</a>
      <a href='monitor.php'>Monitor Operations</a>
      <a href='program.php'>Programs</a>
      <a href='programStation.php'>Program Station</a>
      <a href='event.php'>Events</a>
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
      <a href='webList.php'>Web Parameter Edit</a>
      <a href='ET.php'>ET Daily</a>
      <a href='ETannual.php'>ET Annual</a>
    </div>
  </li>
 </ul>
</div>
</div>

<script src='js/status.js'></script>
";
?>
