<?php
class InputBuilder
{
	private $qArray = false;
	public  $field;
	public  $name;
	public  $label;
	private $iPrefix;
	private $iSuffix;
	private $converter = 'text';
	private $step = 1;
	private $max = INF;
	private $min = -INF;
	private $map = [];
	private $qList = false;
	private $qTextarea = false;
	public  $qHeader = true;
	private $qMultiple = false;
	public  $listTable = NULL;
	public  $listField = NULL;
	private $listResults = [];

	function __construct(array $row, bool $qArray, $db) {
		$field = $row['field'];
		$name = $qArray ? ($field . "[]") : $field;
		$this->qArray = $qArray;
		$this->field = $field;
		$this->name = $name;
		$this->label = $row['label'];
		$this->converter = $row['converter'];
		$this->listTable = $row['listTable'];
		$this->listField = $row['idField'];
		$this->qMultiple = !is_null($this->listTable);
		$this->qRequired = $row['qRequired'];

		$itype = $row['inputType']; // Type for <input> tag
		$iPre = "<input name='$name' type='$itype'";
		if (!is_null($row['ph'])) $iPre .= " placeholder='" . $row['ph'] . "'";
		if ($this->qRequired) $iPre .= " required";
		if ($itype == 'text') {
			$iPre .= " maxlen='" . $row['maxLen'] . "'";
		} elseif ($itype == 'number') {
			$iPre .= $this->buildNumber($row);
		} elseif ($itype == 'list') { 
			$this->buildList($row, $db);
		} elseif ($itype == 'textarea') {
			$this->buildTextarea($row);
		} else {
			$toIgnore = ['date', 'time', 'password', 'email'];
			if (!in_array($itype, $toIgnore)) {
				echo "UNRECOGNIZED: iType=$itype\n";
			}
		}
		if (!is_null($row['inputArgs'])) $iPre .= " " . $row['inputArgs'];
		$this->iPrefix = $iPre . " value='";
		$this->iSuffix = "'>\n";
	}

	function qPrimary() {return is_null($this->listTable);}

	function buildNumber(array $row) {
		$msg = '';
		if ($row['step'] != 1) {
			$this->step = $row['step'];
			$msg .= " step='" . $row['step'] . "'";
		}
		if (is_numeric($row['minVal'])) {
			$this->min = floatval($row['minVal']);
			$msg .= " min='" . $row['minVal'] . "'";
		}
		if (!is_null($row['maxVal'])) {
			$this->max = floatval($row['maxVal']);
			$msg .= " max='" . $row['maxVal'] . "'";
		}
		return $msg;
	}

	function buildTextarea(array $row) {
		$this->qTextarea = true;
	}

	function buildList(array $row, $db) {
		$results = $db->query($row['sql']);
		while ($info = $results->fetchArray()) {
			array_push($this->map, [$info[0], $info[1]]);
		}
		$this->qList = true;
		$this->qHeader = count($this->map) > 1;
	}

	function populateList($db) {
		if (is_null($this->listTable) || is_null($this->listField)) return;
		$sql = "SELECT " . $this->field . "," . $this->listField
				. "  FROM " . $this->listTable . ";";
		$results = $db->query($sql);
		while ($info = $results->fetchArray()) {
			if (!array_key_exists($info[1], $this->listResults)) {
				$this->listResults[$info[1]] = [$info[0]];
			} else {
				array_push($this->listResults[$info[1]], $info[0]);
			}
		}

	}

	function savePrev($id, $value) {
		global $_SESSION;
		$field = $this->field;
		if (!array_key_exists('prev', $_SESSION)) $_SESSION['prev'] = [];
		if (!array_key_exists($field, $_SESSION['prev'])) $_SESSION['prev'][$field] = [];
		$_SESSION['prev'][$field][$id] = $value;
	}

	function qChanged($id, $value) {
		global $_SESSION;
		$field = $this->field;
		if (!array_key_exists('prev', $_SESSION) ||
			!array_key_exists($field, $_SESSION['prev']) ||
			!array_key_exists($id, $_SESSION['prev'][$field])) {
			// echo "<pre>Short changed id=$id field=$field value=$value</pre>\n";
			return $value != '';
		}
		$prev = $_SESSION['prev'][$field][$id];
		$q = $value != $prev;
		// echo "<pre>q=$q id=$id field=$field value='$value' prev='$prev'</pre>\n";
		if ($q && is_numeric($value) && is_numeric($prev)) {
			$delta = abs($value - $prev);
			$q = $delta >= $this->step;
			// echo "<pre>q=$q id=$id field=$field value='$value' prev='$prev' delta=$delta step=" . $this->step . "</pre>\n";
		}
		return $q;
	}

	function mkList(array $row) {
		$id = $row['id'];
		$field = $this->field;
		$name = $this->name;

		$map = $this->map;

		if ($this->qMultiple) {
			$name = $field . "[$id][]";
			$value = array_key_exists($id, $this->listResults) 
				? $this->listResults[$id] : [];
		} else {
			$value = array_key_exists($field, $row) ? $row[$field] : 
				(count($map) ? $map[0][0] : '');
		}

		$this->savePrev($id, $value);

		if (count($map) <= 1) {
			echo "<input type='hidden' name='$name' value='$value'>\n";
			return;
		}
		echo "<select name='$name'";
		if ($this->qMultiple) echo " multiple";
		echo ">\n";
		$qArray = is_array($value);
		foreach ($map as $item) {
			$key = $item[0];
			echo "<option value='$key'";
			if (($qArray && (array_search($key, $value) !== false)) ||
			    (!$qArray && ($key == $value))) {
				echo " selected";
			}
			echo ">" . $item[1] . "</option>\n";
		}
		echo "</select>\n";
	}

	function mkTextarea(array $row) {
		$field = $this->field;
		$name = $this->name;
		$value = array_key_exists($field, $row) ? $row[$field] : '';
		$this->savePrev($row['id'], $value);
		echo "<textarea name='$name' placeholder='Some text here'>$value</textarea>\n";
	}

	function mkInput(array $row) {
		if ($this->qList) return $this->mkList($row);
		if ($this->qTextarea) return $this->mkTextarea($row);
		$field = $this->field;
		$value = array_key_exists($field, $row) ? $this->unconvert($row[$field]) : '';
		$this->savePrev($row['id'], $value);
		$iPre = $this->iPrefix;
		// Drop required on empty rows
		if ($row['id'] == 0) $iPre = str_replace(" required", "", $iPre);
		echo $iPre . $value . $this->iSuffix;
	}

	function mkCell(array $row, string $ctype='td') {
		if ($this->qHeader) echo "<$ctype>\n";
		$this->mkInput($row);
		if ($this->qHeader) echo "</$ctype>\n";
	}

	function mkRow(array $row) {
		echo "<tr>\n";
		if ($this->qHeader) echo "<th>" . $this->label . "</th>\n";
		$this->mkCell($row);
		echo "</tr>\n";
	}

	function convert($value) {
		if (empty($value)) return $value;
		$cnv = $this->converter;
		$qNumeric = is_numeric($value);
		if ($qNumeric && is_numeric($cnv)) return $value * $cnv;
		if (($cnv == 'date') || ($cnv == 'datetime')) return strtotime($value);
		if ($cnv == 'time') return strtotime($value) - strtotime("00:00:00");
		if ($cnv == 'passwd') return password_hash($value, PASSWORD_DEFAULT);
		if ($qNumeric) {
			$value = floatval($value);
			return fmod($value,1) == 0 ? intval($value) : $value;
		}
		return $value;
	}

	function unconvert($value) {
		if (empty($value)) return $value;
		$cnv = $this->converter;
		$qNumeric = is_numeric($value);
		if (is_numeric($value) && is_numeric($cnv)) return $value / $cnv;
		if ($cnv == 'date') return strftime('%Y-%m-%d', $value);
		if ($cnv == 'datetime') return strftime('%Y-%m-%d %H:%M:%S', $value);
		if ($cnv == 'time') return gmstrftime('%H:%M:%S', $value);
		if ($cnv == 'passwd') return '';
		if ($qNumeric) {
			$value = floatval($value);
			if (is_numeric($this->step)) {
				$value = round($value / $this->step) * $this->step;
			}
			if (is_numeric($this->max) && ($value > $this->max)) $value = $this->max;
			if (is_numeric($this->min) && ($value < $this->min)) $value = $this->min;
			return fmod($value,1) == 0 ? intval($value) : $value;
		}
		return $value;
	}
} // Input Builder

class PageBuilder
{
	private $key;
	private $db;
	private $qTable = false;
	private $table = NULL;
	private $sql = NULL;
	private $items = [];
	private $fields = [];
	private $secondary = [];
	private $idField;
	private $keyField;

	function __construct(string $key, $db) {
		$this->key = $key;
		$this->db = $db;
		$results = $db->query("SELECT * FROM webFetch WHERE key=='$key';");
		while ($row = $results->fetchArray()) {
			$this->table = $row['tbl'];
			$this->sql = $row['sql'];
			$this->qTable = $row['qTable'];
			$this->idField = $row['idField'];
			$this->keyField = $row['keyField'];
		}
		if (is_null($this->table) || is_null($this->sql)) {
			echo "<h1>Error unrecognized key($key)</h1>\n";
			return;
		}
		if (is_null($this->idField)) $this->idField = 'id';
		if (is_null($this->keyField)) $this->keyField = $this->table;

		$results = $db->query("SELECT * FROM webItem WHERE key=='$key' "
				. "ORDER BY sortOrder;");
		while ($row = $results->fetchArray()) {
			$item = new InputBuilder($row, $this->qTable, $this->db);
			array_push($this->items, $item);
			if ($item->qPrimary()) {
				array_push($this->fields, $row['field']);
			} else {
				array_push($this->secondary, $item);
			}
		}
		if (empty($this->items)) {
			echo "<h1>Error: no webView columns found for $key</h1>\n";
			return;
		}
	}

	function postUp(array $post) {
		/*	
		global $_SESSION;
		echo "<pre>\n";
		myDump('_SESSION', $_SESSION['prev']);
		myDump('_POST', $post);
		echo "</pre>\n";
		*/
		return $this->qTable ? $this->postUpArray($post) : $this->postUpSingle($post);
	}

	function postUpSingle(array $post) {
		$id = $post['id'];
		if (array_key_exists('delete', $post)) { // Delete an entry by its id
			$this->db->deleteFromTable($this->table, 'id', $id);
			return;
		}
		if ($id == 0) { // Insert a new record
			$qSecondary = false;
			$qInsert = false;
			$saveItems = [];
			foreach ($this->items as $item) {
				$qSecondary |= !$item->qPrimary();
				if ($item->qPrimary()) {
					$field = $item->field;
					if ($item->qRequired && ($post[$field] == '')) {
						return; // skip not all filled out
					}
					$q = $item->qChanged($id, $post[$field]);
					$qInsert |= $q;
					if ($q || ($post[$field] != '')) {
						array_push($saveItems, $item);
					}
				}
			}
			if ($qInsert) {
				$values = [];
				$fields = [];
				foreach ($saveItems as $item) {
					$field = $item->field;
					array_push($fields, $field);
					$values[$field] = $item->convert($post[$field]);
				}
				$this->db->insert($this->table, $fields, $values);
				if ($qSecondary) {
					$id = $this->db->getID($this->table, $this->idField,
						$this->keyField, $post[$this->keyField]);
					$this->postUpSecondary($post, $id);
				}
			}
			return;
		}
		$aValues = [];
		$qSecondary = false;
		foreach ($this->items as $item) {
			$qSecondary |= !$item->qPrimary();
			$field = $item->field;
			if ($item->qPrimary() && $item->qChanged($id, $post[$field])) {
				$aValues[$field] = $item->convert($post[$field]);
			}
		}
		if (!empty($aValues)) {
			$fields = array_keys($aValues);
			$aValues['id'] = $id;
			$this->db->updates($this->table, $fields, $aValues, 'id', $id);
		}
		if ($qSecondary) $this->postUpSecondary($post);
	}

	function postUpSecondary(array $post, $newID = NULL) {
		$id = $post['id'];
		if (is_null($newID)) $newID = $id;
		foreach ($this->items as $item) { // Look for secondary
			$field = $item->field;
			if ($item->qPrimary()) continue;
			if (empty(array_diff($post[$field], 
				  $_SESSION['prev'][$field][$id]))) continue;
			$this->db->deleteFromTable($item->listTable, $item->listField, $newID);
			$sql = "INSERT INTO " . $item->listTable . "(" . $item->listField
				. "," . $item->field . ") VALUES(:key,:value);";
			$stmt = $this->db->prepare($sql);
			foreach ($post[$field] as $a) {
				echo "<pre>$sql, $newID, $id, $a</pre>\n";
				$stmt->bindValue(":key", $newID);
				$stmt->bindValue(":value", $a);
				$stmt->execute();
				$stmt->reset();
			}
			$stmt->close();
		}

	}

	function postUpArray(array $post) {
		$deleted = [];
		if (array_key_exists('delete', $post)) { // Delete entries by id
			foreach ($post['delete'] as $id) {
				if ($id != 0) {
					$deleted[$id] = 1;
					$this->db->deleteFromTable($this->table, 'id', $id);
				}
			}
		}
		$n = count($post['id']);
		for ($i = 0; $i < $n; ++$i) {
			$id = $post['id'][$i];
			if (array_key_exists($id, $deleted)) continue;
			$data = ['id'=>$id];
			foreach ($this->items as $item) {
				$field = $item->field;
				if ($item->qPrimary()) {
					$data[$field] = $post[$field][$i];
				} else { // Secondary
					$data[$field] = 
						array_key_exists($field, $post) &&
						array_key_exists($id, $post[$field]) &&
						!is_null($post[$field][$id])
						? $post[$field][$id] : [];
				}
			}
			$this->postUpSingle($data);
		}
	}

	function mkPage() {
		global $_SESSION;
		$_SESSION['prev'] = [];
		foreach ($this->items as $item) { 
			if (!$item->qPrimary()) $item->populateList($this->db); 
		}
		return $this->qTable ? $this->mkByRows() : $this->mkByTables();
	}

	function mkByRows() { // Build a single table with many rows
		echo "<center>\n";
		echo "<form method='post'>\n";
		echo "<table>\n";
		$this->mkTableHeader("thead");
		$results = $this->db->query($this->sql);
		while ($row = $results->fetchArray()) {$this->mkRow($row);}
		$this->mkRow([]);
		$this->mkTableHeader("tfoot");
		echo "</table>\n";
		echo "<input type='submit' value='Update'>\n";
		echo "</form>\n";
		echo "</center>\n";
	}

	function mkRow(array $row) {
		$qEmpty = empty($row);
		$id = $qEmpty ? 0 : $row['id'];
		$row['id'] = $id;
		echo "<tr>\n";
		echo "<td>\n";
		echo "<input type='hidden' name='id[]' value='$id'>\n";
		if (!$qEmpty) {
			echo "<input type='checkbox' name='delete[]' value='$id'>\n";
		}
		echo "</td>\n";
		foreach ($this->items as $item) {$item->mkCell($row);}
		echo "</tr>\n";
	}

	function mkTableHeader(string $ctype=NULL) {
		if (!is_null($ctype)) echo "<$ctype>\n";
		echo "<tr>";
		if ($this->qTable) echo "<th>Delete</th>";
		foreach ($this->items as $item) {
			if ($item->qHeader) echo "<th>" . $item->label . "</th>"; 
		}
		echo "</tr>\n";
		if (!is_null($ctype)) echo "</$ctype>\n";
	}

	function mkByTables() {
		$results = $this->db->query($this->sql);
		$qFirst = true;
		while ($row = $results->fetchArray()) {
			if (!$qFirst) echo "<hr>\n"; 
			$qFirst = false;
			$this->mkTable($row);
		}
		if (!$qFirst) echo "<hr>\n"; 
		$this->mkTable([]);
	}

	function mkTable(array $row) {
		$qEmpty = empty($row);
		$id = $qEmpty ? 0 : $row['id'];
		$row['id'] = $id;
		echo "<center>\n";
		echo "<form method='post'>\n";
		echo "<input type='hidden' name='id' value='$id'>\n";
		echo "<table>\n";
		foreach ($this->items as $item) { $item->mkRow($row); }
		echo "</table>\n";
		if ($qEmpty) {
			echo "<input type='submit' name='insert' value='Create'>\n";
		} else {
			echo "<input type='submit' name='update' value='Update'>\n";
			echo "<input type='submit' name='delete' value='Delete'>\n";
		}
		echo "</form>\n";
		echo "</center>\n";
	}
} // PageBuilder
?>
