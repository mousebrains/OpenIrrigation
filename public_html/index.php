<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Wild Iris Irrigation</title>
</head>
<body>
<?php
require_once 'php/navBar.php';

if (!empty($_POST)) {
  echo "<pre>"; var_dump($_POST); echo "</pre>";
  try {
    $db->begin();
    if (array_key_exists('Run', $_POST)) { // Update pgmStn
      $db->execute('SELECT addManual($1,$2);', [$_POST['id'], $_POST['time']]);
    } elseif (array_key_exists('Stop', $_POST)) { // Stop an existing run
      $db->execute("DELETE FROM pgmStn"
		. " WHERE qSingle=True"
		. " AND program=getManualId()"
		. " AND station=(SELECT id FROM station WHERE sensor=$1);",
		[$_POST['id']]);
      $db->execute("DELETE FROM action"
		. " WHERE sensor=$1"
		. " AND program=getManualId()"
		. " AND cmdOn IS NOT NULL"
		. " AND cmdOff IS NULL;",
		[$_POST['id']]);
      $db->execute("UPDATE action SET tOff=CURRENT_TIMESTAMP"
		. " WHERE sensor=$1 AND cmdOn IS NULL AND cmdOff IS NOT NULL;",
		[$_POST['id']]);
    } elseif (array_key_exists('mvRun', $_POST)) { // Start a master valve
      $db->execute("INSERT INTO action(sensor,cmd,tOn,tOff,program,pgmDate) VALUES"
		. "($1,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP+make_interval(mins=>$2),"
		. "getManualId(),CURRENT_DATE);",
		[$_POST['id'], $_POST['time']]);
    } else { // Stop a master valve
      $db->execute("DELETE FROM action"
		. " WHERE sensor=$1"
		. " AND program=getManualId()"
		. " AND cmdOn IS NOT NULL"
		. " AND cmdOff IS NULL;",
		[$_POST['id']]);
      $db->execute("UPDATE action SET tOff=CURRENT_TIMESTAMP"
		. " WHERE sensor=$1 AND cmdOn IS NULL AND cmdOff IS NOT NULL;",
		[$_POST['id']]);
    }
    $db->commit();
  } catch (Exception $e) {
    $db->rollback();
    echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
  }
}

function mkRow(array $row, string $prefix='') {
  $id = $row['sensor'];
  echo "<tr>\n<th id='n$id'>" . $row['name'] . "</th>\n";
  echo "<td>\n";
  echo "<span id='a$id' style='display:inline;'>\n";
  echo "<form method='post'>\n";
  echo "<input type='hidden' name='id' value='$id'>\n";
  echo "<input type='number' name='time' min='0' max='300' step='0.1'>\n";
  echo "<input type='submit' name='" . $prefix . "Run' value='Run'>\n";
  echo "</form>\n";
  echo "</span>\n";
  echo "<span id='b$id' style='display:none;'>\n";
  echo "<span id='bc$id'></span>\n";
  echo "<form method='post' style='display:inline;'>\n";
  echo "<input type='hidden' name='id' value='$id'>\n";
  echo "<input type='submit' name='" . $prefix . "Stop' value='Stop'>\n";
  echo "</form>\n";
  echo "</span>\n";
  echo "</td>\n";
  echo "</tr>\n";
}

$hdr = "<tr><th>Station</th><th>Minutes</th></tr>";
echo "<center>\n<table>\n";
echo "<thead>$hdr</thead>\n";

try {
  $results = $db->execute("SELECT sensor,name FROM station ORDER BY name;");
  while ($row = $results->fetchArray()) { mkRow($row); }
  $results = $db->execute("SELECT sensor,name FROM pocMV ORDER BY name;");
  while ($row = $results->fetchArray()) { mkRow($row, 'mv'); }
} catch (Exception $e) {
  echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
}

echo "<tfoot>$hdr</tfoot>\n";
echo "</table>\n</center>\n";
?>
<script src='js/index.js'></script>
</body>
</html> 
