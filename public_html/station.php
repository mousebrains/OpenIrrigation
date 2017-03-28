<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset="UTF-8">
<meta http-equiv='Content-Language' content='en'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Station editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'station';
$fields = ['poc', 'sensor', 'name', 'station', 'make', 'model', 
	'sortOrder', 'cycleTime', 'soakTime', 
	'measuredFlow', 'userFlow', 'lowFlowFrac', 'highFlowFrac', 
	'onDelay', 'offDelay'];
$adjust = ['cycleTime'=>60, 'soakTime'=>60];

if (!empty($_POST)) {$parDB->postUp($table, $fields, $_POST, $adjust);}

function myForm(array $row, array $poc, array $sensors, string $submit) {
	global $parDB;
	global $adjust;
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	inputHidden($row['id']);
	echo "<table>\n";
	selectFromList('POC', 'poc', $poc, $row['poc']);
	selectFromList('Sensor', 'sensor', $sensors, $row['sensor']);
	inputRow('Name', 'name', $row['name'], 'text', 
		['placeholder'=>'Sensor Name', 'required'=>NULL]);
	inputRow('Station', 'station', $row['station'], 'number', 
		['placeholder'=>1, 'required'=>true, 'min'=>1, 'max'=>200]);
	inputRow('Make', 'make', $row['make'], 'text', ['placeholder'=>'Tucor']);
	inputRow('Model', 'model', $row['model'], 'text', ['placeholder'=>'TDI']);
	inputRow('Sort Order', 'sortOrder', $row['sortOrder'], 'number', 
		['placeholder'=>1, 'min'=>1, 'max'=>200]);
	inputRow('Maximum Cycle Time (min)', 'cycleTime', 
		$parDB->unadjust('cycleTime', $row['cycleTime'], $adjust), 'number', 
		['placeholder'=>1, 'min'=>1, 'max'=>600]);
	inputRow('Minimum Soak Time (min)', 'soakTime', 
		$parDB->unadjust('soakTime', $row['soakTime'], $adjust), 'number', 
		['placeholder'=>1, 'min'=>1, 'max'=>600]);
	inputRow('On Delay (s)', 'onDelay', $row['onDelay'], 'number', 
		['placeholder'=>1, 'min'=>1, 'max'=>900]);
	inputRow('Off Delay (s)', 'offDelay', $row['offDelay'], 'number', 
		['placeholder'=>1, 'min'=>1, 'max'=>900]);
	inputRow('Measured Flow (GPM)', 'measuredFlow', $row['measuredFlow'], 'number', 
		['placeholder'=>5.1, 'step'=>0.1, 'min'=>0, 'max'=>100]);
	inputRow('User Flow (GPM)', 'userFlow', $row['userFlow'], 'number', 
		['placeholder'=>5.1, 'step'=>0.1, 'min'=>0, 'max'=>100]);
	inputRow('Low flow fraction', 'lowFlowFrac', $row['lowFlowFrac'], 'number', 
		['placeholder'=>0.1, 'step'=>0.1, 'min'=>0, 'max'=>10]);
	inputRow('High flow fraction', 'highFlowFrac', $row['highFlowFrac'], 'number',
		['placeholder'=>0.1, 'step'=>0.1, 'min'=>0, 'max'=>10]);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$poc = $parDB->loadTable('poc', 'id', 'name', 'name');
$sensors = $parDB->loadTable('sensor', 'id', 'name', 'addr');

$results = $parDB->query("SELECT * FROM $table ORDER BY sortOrder;");
while ($row = $results->fetchArray()) {
	myForm($row, $poc, $sensors, 'Update');
}

myForm(mkBlankRow($fields, ['id'=>'','poc'=>key($poc),'sensor'=>key($sensors)]), 
       $poc, $sensors, 'Create');
?>
</body>
</html>
