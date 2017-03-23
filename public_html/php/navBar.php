<?php
echo "
<div id='topnav'>
 <div id='statusBlock'>Status info</div>
 <ul>
  <li id='topdropdown'>
    <a href='javascript:void(0)' id='topdropbtn'>&#9776;</a>
    <div id='top-dropdown-content'>
      <a href='index.php'>Manual Operations</a>
      <a href='monitor.php'>Monitor Operations</a>
      <a href='program.php'>Programs</a>
      <a href='event.php'>Events</a>
      <a href='programEvent.php'>Program Events</a>
      <a href='station.php'>Stations</a>
      <a href='site.php'>Site Edit</a>
      <a href='user.php'>User Edit</a>
      <a href='email.php'>EMail Edit</a>
      <a href='controller.php'>Controller Edit</a>
      <a href='sensor.php'>Decoder/Sensor Edit</a>
      <a href='poc.php'>Point-of-connect Edit</a>
      <a href='pocFlow.php'>Flow Sensor Edit</a>
      <a href='pocMV.php'>Master Valve Edit</a>
      <a href='pocPump.php'>Booster Pump Edit</a>
      <a href='report.php'>Report Name Edit</a>
    </div>
  </li>
 </ul>
</div>
<script src='js/status.js'></script>
";
?>
