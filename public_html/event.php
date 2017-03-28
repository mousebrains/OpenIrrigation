<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' type='text/css' href='css/irrigation.css'>
<script src="js/jquery.min.js"></script>
<title>Event editor</title>
</head>
<body>
<?php
require_once 'php/navBar.php';
require_once 'php/ParDB.php';
require_once 'php/webForm.php';

$table = 'event';
$fields = ['site', 'name', 'mode', 'action', 'val', 'refDate', 'startTime', 'duration',
	'startMode', 'stopMode'];
$adjust = ['refDate'=>'date'];

if (!empty($_POST)) {
	if (empty($_POST['delete'])) { // not a delete entry, so adjust values
		if ($_POST['dailyAction'] == $_POST['action']) {
			$_POST['val'] = 0;
			foreach ($_POST['dow'] as $bit) {$_POST['val'] |= 1 << intval($bit);}
		} else {
			$_POST['val'] = $_POST['nDays'];
		}
		$midnight = strtotime('00:00:00');
		$_POST['startTime'] = strtotime($_POST['startTime'])-$midnight;
		$_POST['oldstartTime'] = strtotime($_POST['oldstartTime'])-$midnight;
		$_POST['duration'] = strtotime($_POST['duration'])-$midnight;
		$_POST['oldduration'] = strtotime($_POST['oldduration'])-$midnight;
		if ($_POST['duration'] >= $_POST['startTime']) { // In same day
			$_POST['duration'] -= $_POST['startTime'];
			$_POST['oldduration'] -= $_POST['oldstartTime'];
		} else { // Span a day
			$_POST['duration'] -= $_POST['startTime'] - 86400;
			$_POST['oldduration'] -= $_POST['oldstartTime'] - 86400;
		}
	}
	$parDB->postUp($table, $fields, $_POST, $adjust);
}

function myForm(array $row, array $sites, array $modes, array $actions,
	array $celestial, array $dow, string $submit) 
{
	global $parDB;
	global $adjust;
	$stime = intval($row['startTime']);
	$row['duration'] = gmstrftime('%H:%M:%S', $stime + intval($row['duration']));
	$row['startTime'] = gmstrftime('%H:%M:%S', $stime);
	$dailyAction = array_search('Day(s) of week', $actions);
	$nDaysAction = array_search('Every n days', $actions);
	$row['dow'] = ($row['action'] == $dailyAction) ? $row['val'] : '';
	$row['nDays'] = ($row['action'] == $nDaysAction) ? $row['val'] : 0;
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	inputHidden($row['id']);
	inputHidden($dailyAction, 'dailyAction');
	inputHidden($nDaysAction, 'nDaysAction');
	inputHidden($row['val'], 'oldval');
	echo "<table>\n";
	selectFromList('Site', 'site', $sites, $row['site']);
	inputRow('Name', 'name', $row['name'], 'text', 
		['placeholder'=>'Program B', 'required'=>NULL]);
	selectFromList('Operating Mode', 'mode', $modes, $row['mode']);
	selectFromList('Event type', 'action', $actions, $row['action']);
	selectFromList('Days of Week', 'dow[]', $dow, $row['dow']);
	inputRow('Every n days', 'nDays', $row['nDays'], 'number', 
		['placeholder'=>1, 'min'=>0, 'max'=>365]);
	inputRow('Reference date for "Every n Days"', 'refDate', 
		$parDB->unadjust('refDate', $row['refDate'], $adjust), 'date');
	inputRow('Start Time', 'startTime', $row['startTime'], 'time');
	inputRow('End Time', 'duration', $row['duration'], 'time');
	selectFromList('Start Mode', 'startMode', $celestial, $row['startMode']);
	selectFromList('Stop Mode', 'stopMode', $celestial, $row['stopMode']);
	echo "</table>\n";
	submitDelete($submit, !empty($row['name']));
	echo "</form>\n";
	echo "</center>\n";
}

$sites = $parDB->loadTable('site', 'id', 'name', 'name');
$modes = $parDB->loadTable('eventMode', 'id', 'label', 'label');
$actions = $parDB->loadTable('eventAction', 'id', 'label', 'label');
$celestial = $parDB->loadTable('eventCelestial', 'id', 'label', 'label');
$dayOfWeek = $parDB->loadTable('eventDaysOfWeek', 'id', 'label', 'id');

$results = $parDB->query("SELECT * FROM $table ORDER BY name COLLATE NOCASE;");
while ($row = $results->fetchArray()) {
	myForm($row, $sites, $modes, $actions, $celestial, $dayOfWeek, 'Update');
}

myForm(mkBlankRow($fields, ['id'=>'','site'=>key($sites),'mode'=>key($modes),
			'action'=>key($actions),
			'startMode'=>key($celestial),'stopMode'=>key($celestial)]),
	$sites, $modes, $actions, $celestial, $dayOfWeek, 'Create');
?>
</body>
</html>
