<?php
function inputHidden($value, $name='id', $type='hidden') 
{
	echo "<input type='$type' name='$name' value='$value'>\n";
}

function inputBlock(string $name, $value, string $type, array $opts = []) 
{
	if ($type == 'latlon') {
		$type = 'number';
		$opts['step'] = 1e-6;
		if ($name == 'latitude') {
			$opts['min'] = -90;
			$opts['max'] = 90;
		} else {
			$opts['min'] = -180;
			$opts['max'] = 180;
		}
	}
	echo "<input type='hidden' name='old$name' value='$value'>\n";
	echo "<input type='$type' name='$name' value='$value'";
	foreach ($opts as $key => $value) {
		if (is_null($value)) { // no args
			echo " $key";
		} else {
			echo " $key='$value'";
		}
	}
	echo ">\n";
}

function inputRow(string $label, string $name, $value,  string $type='text', array $opts=[])
{
	echo "<tr>\n<th>$label</th>\n<td>\n";
	inputBlock($name, $value, $type, $opts);	
	echo "</td>\n<tr>\n";
}

function selectCellList(string $name, array $items, string $active, bool $qMultiple = false)
{
	if (count($items) <= 1) {
		echo "<input type='hidden' name='old$name' value='$active'>\n";
		echo "<input type='hidden' name='$name' value='$active'>\n";
		return;
	}
	echo "<td>\n<input type='hidden' name='old$name' value='$active'>\n";
	echo "<select name='$name'";
	if ($qMultiple) {echo " multiple";}
	echo ">\n";
	foreach ($items as $key => $value) {
		echo "<option value='$key'";
		if ((!$qMultiple && ($key == $active)) || ($qMultiple && ((1 << $key) & $active))) {
			echo " selected";
		}
		echo ">$value</option>\n";
	}
	echo "</select>\n</td>\n";
}

function selectFromList(string $label, string $name, array $items, $active)
{
	$qMultiple = substr($name,-2) == '[]'; // A bit masked value collection

	if (count($items) <= 1) {
		echo "<input type='hidden' name='old$name' value='$active'>\n";
		echo "<input type='hidden' name='$name' value='$active'>\n";
		return;
	}
	echo "<tr><th>$label</th>\n";
	selectCellList($name, $items, $active, $qMultiple);
}

function submitDelete(string $submit, bool $qDelete)
{
	echo "<input type='submit' value='$submit'>\n";
	if ($qDelete) {echo "<input type='submit' value='Delete' name='delete'>\n"; }
}

function mkBlankRow(array $fields, array $others) : array 
{
	return array_merge(array_fill_keys($fields, ''), $others);
}
