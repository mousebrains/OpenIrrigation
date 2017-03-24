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

if (!empty($_POST)) {
	if (!empty($_POST['delete'])) { // Delete the entry
		$parDB->deleteFromTable($table, 'id', $_POST['id']);
	} else {
		if (!is_null($_POST['refDate'])) {
			$_POST['refDate'] = strtotime($_POST['refDate']);
		}
		if (!is_null($_POST['oldrefDate'])) {
			$_POST['oldrefDate'] = strtotime($_POST['oldrefDate']);
		}
		$_POST['oldval'] = intval($_POST['olddow']);
		if ($_POST['dailyAction'] == $_POST['action']) {
			$_POST['val'] = 0;
			foreach ($_POST['dow'] as $bit) {$_POST['val'] += 1 << intval($bit);}
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
		if ($_POST['id'] == '') {
			$parDB->insertIntoTable($table, $fields, $_POST);	
		} else {
			$parDB->maybeUpdate($table, $fields, $_POST);	
		}
	}
}

function myForm(array $row, array $sites, array $modes, array $actions,
	array $celestial, array $dow, string $submit) 
{
	if (!is_null($row['refDate'])) {
		$row['refDate'] = strftime('%Y-%m-%d', intval($row['refDate']));
	}
	$stime = intval($row['startTime']);
	$row['duration'] = gmstrftime('%H:%M:%S', $stime + intval($row['duration']));
	$row['startTime'] = gmstrftime('%H:%M:%S', $stime);
	$row['dow'] = $row['val'];
	$row['nDays'] = 0;
	$dailyAction = array_search('Day(s) of week', $actions);
	$nDaysAction = array_search('Every n days', $actions);
	echo "<hr>\n";
	echo "<center>\n";
	echo "<form method='post'>\n";
	echo "<input type='hidden' name='id' value='" . $row['id'] . "'>\n";
	echo "<input type='hidden' name='dailyAction' value='$dailyAction'>\n";
	echo "<input type='hidden' name='nDaysAction' value='$nDaysAction'>\n";
	echo "<table>\n";
	selectFromList('Site', 'site', $sites, $row['site']);
	inputRow('Name', 'name', $row['name'], 'text', 'Program B', true);
	selectFromList('Operating Mode', 'mode', $modes, $row['mode']);
	selectFromList('Event type', 'action', $actions, $row['action']);
	selectFromList('Days of Week', 'dow[]', $dow, $row['dow']);
	inputRow('Every n days', 'nDays', $row['nDays'], 'number', '1', false, 1, 0);
	inputRow('Reference date for "Every n Days"', 'refDate', $row['refDate'], 'date');
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

$results = $parDB->query('SELECT * FROM ' . $table . ' ORDER BY name;');
while ($row = $results->fetchArray()) {
	myForm($row, $sites, $modes, $actions, $celestial, $dayOfWeek, 'Update');
}

$blankRow = array_fill_keys($fields, '');
$blankRow['id'] = '';
myForm($blankRow, $sites, $modes, $actions, $celestial, $dayOfWeek, 'Create');
?>
</body>
</html>
