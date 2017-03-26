<?php
function inputRow(string $label, string $name, $value, 
		  string $type = 'text', 
		  string $placeholder = NULL, 
		  bool $qRequired = false,
		  float $step = NULL,
		  float $min = NULL,
		  float $max = NULL,
		  bool $qChecked = NULL
		)
{
	if ($type == 'latlon') {
		$type = 'number';
		$step = 1e-7; // ~1/100 of an arc second
		if ($name == 'latitude') {
			$min = -90;	
			$max = 90;	
		} else {
			$min = -180;	
			$max = 180;	
		}
	}

	echo "<tr><th>$label</th><td>\n";
	echo "<input type='hidden' name='old$name' value='$value'>\n";
	echo "<input type='$type' name='$name' value='$value'";
	if (!is_null($placeholder)) {echo " placeholder='$placeholder'";}
	if (!is_null($step)) {echo " step='$step'";}
	if (!is_null($min)) {echo " min='$min'";}
	if (!is_null($max)) {echo " max='$max'";}
	if ($qRequired) {echo " required";}
	if ($qChecked) {echo " checked";}
	echo ">\n</td><tr>\n";
}

function selectCellList(string $name, array $items, string $active, bool $qMultiple = false)
{
	echo "<td><input type='hidden' name='old$name' value='$active'>\n";
	echo "<select name='$name'";
	if ($qMultiple) {echo " multiple";}
	echo ">\n";
	foreach ($items as $key => $value) {
		echo "<option value='$key'";
		if ((!$qMultiple && ($key == $active)) || ($qMultiple & ((1 << $key) & $active))) {
			echo " selected";
		}
		echo ">$value</option>\n";
	}
	echo "</select></td>\n";
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

function postUp(array $post, string $table, array $fields, $db) 
{
	if (!empty($post['delete'])) { // Delete the entry
		$db->deleteFromTable($table, 'id', $post['id']);
	} else {
		if ($post['id'] == '') {
			$db->insertIntoTable($table, $fields, $post);	
		} else {
			$db->maybeUpdate($table, $fields, $post);	
		}
	}
}
?>
