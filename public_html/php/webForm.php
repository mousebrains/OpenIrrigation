<?php
function inputRow(string $label, string $name, $value, 
		  string $type = 'text', 
		  string $placeholder = NULL, 
		  bool $qRequired = false,
		  float $step = NULL,
		  float $min = NULL,
		  float $max = NULL,
		  bool $qChecked = NULL
		) {
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

	echo "<tr><th>" . $label . "</th><td>\n";
	echo "<input type='hidden' name='old" . $name . "' value='" . $value . "'>\n";
	echo "<input type='" . $type . "' name='" . $name . "' value='" . $value . "'";
	if (!is_null($placeholder)) {echo " placeholder='" . $placeholder . "'";}
	if (!is_null($step)) {echo " step='" . $step . "'";}
	if (!is_null($min)) {echo " min='" . $min . "'";}
	if (!is_null($max)) {echo " max='" . $max . "'";}
	if ($qRequired) {echo " required";}
	if ($qChecked) {echo " checked";}
	echo ">\n</td><tr>\n";
}

function selectFromList(string $label, string $name, array $items, $active) {
	if (count($items)) {
		echo "<input type='hidden' name='old" . $name . "' value='" . $active . "'>\n";
		echo "<input type='hidden' name='" . $name . "' value='" . $active . "'>\n";
		return;
	}
	echo "<tr><th>" . $label . "</th><td>\n";
	echo "<input type='hidden' name='old" . $name . "' value='" . $active . "'>\n";
	echo "<select name='" . $name . "'>\n";
        foreach ($items as $key => $value) {
		echo "<option value='" . $key . "'";
                if ($key == $active) {echo " selected";}
                echo ">" . $value . "</option>\n";
        }
        echo "</select>\n";
}

function submitDelete(string $submit, $qDelete) {
	echo "<input type='submit' value='" . $submit . "'>\n";
	if ($qDelete) {echo "<input type='submit' value='Delete' name='delete'>\n"; }
}
?>
