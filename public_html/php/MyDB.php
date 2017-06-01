<?php
require_once 'BaseDB.php';

class MyDB extends BaseDB {
	private $qForeign = false;

	function errMsg(Exception $e, string $msg) : bool {
		echo "<br><h1>Error $msg for " . $this->filename . "</h1>\n";
		echo "<pre>\n";
		echo $e->getMessage();
		echo "</pre>\n";
		return false;
	}
		
	function __construct(string $fn) {
		try {
			parent::__construct($fn);
			$this->enableExceptions(true);
		} catch (Exception $e) {
			$this->errMsg($e, "opening");
		}
        }

	function __destruct() {
		try {
                	$this->close();
		} catch (Exception $e) {
			$this->errMsg($e, "closing");
		}
	}

	function foreignKeys() : bool {
		if (!$this->qForeign) {
			$this->qForeign = true;
			try { // turn foreign key handling on
				$this->exec('PRAGMA foreign_keys=on;');
			} catch (Exception $e) {
				return $this->errMsg($e, "enabling foreign key support");
			}
		}
		return true;
	}

	function getID(string $table, string $id, string $field, $value) : int {
		try {
	        	$stmt = $this->prepare("SELECT $id FROM $table WHERE $field==:val;");
        		$stmt->bindValue(':val', $value);
        		$result = $stmt->execute();
        		$rval = NULL;
        		while ($row = $result->fetchArray()) {
                		$rval = $row[0];
                		break;
        		}
        		$stmt->close();
        		return $rval;
		} catch (Exception $e) {
			$this->errMsg($e, "getting ID");
			return -1;
		}
	}	

	function deleteFromTable(string $table, string $field, $value) : bool {
		try {
			$this->foreignKeys();
        		$sql = "DELETE FROM $table WHERE $field==:value;";
			echo "<pre>$sql, $field=$value</pre>\n";
        		$stmt = $this->prepare($sql);
        		$stmt->bindValue(':value', $value);
        		$stmt->execute();
        		$stmt->close();
			return true;
		} catch (Exception $e) {
			return $this->errMsg($e, "deleting from table($table), $field, $value");
		}

	}

	function insert(string $table, array $fields, array $post) : bool
	{
		try {
			$this->foreignKeys();
        		$sql = "INSERT INTO $table (" . implode(',', $fields) . ') VALUES (:' .
                			implode(',:', $fields) . ');';
			echo "<pre>$sql";
        		$stmt = $this->prepare($sql);
        		foreach ($fields as $field) {
				$stmt->bindValue(':' . $field, $post[$field]);
				echo " $field=" . $post[$field];
			}
 			echo "</pre>";
        		$stmt->execute();
        		$stmt->close();
			return true;
		} catch (Exception $e) {
			return $this->errMsg($e, "inserting into($table)");
		}
	}

	function updates(string $table, array $fields, array $values, string $wField, $wVal)
	{
		if (empty($fields)) return true;
		try {
			$this->foreignKeys();
			$sql = "UPDATE $table SET ";
			if (count($fields) == 1) {
				$sql .= $fields[0] . "=:" . $fields[0];
			} else {
				$sql .= "(" . implode(",", $fields) . ")=(:"
					. implode(",:", $fields) . ")";
			}
			$sql .= " WHERE $wField==:wField;";
			echo "<pre>$wField==$wVal -- $sql";
			$stmt = $this->prepare($sql);
			foreach ($fields as $field) {
				$stmt->bindValue(":$field", $values[$field]);
				echo " $field=" . $values[$field];
			}
			echo "</pre>\n";
			$stmt->bindValue(":wField", $wVal);
			$stmt->execute();
			$stmt->close();
			return true;
		} catch (Exception $e) {
			ksort($values);
			$msg = "";
			foreach ($values as $key => $val) {
				if (!empty($msg)) $msg .= ",";
				$msg .= "$key=$val";
			}
			return $this->errMsg($e, "updating $table, $field, $msg, $wField, $wVal");
		}
	}

	function loadTable(string $table, string $key, string $value, 
			string $orderBy=NULL) : array {
		try {
			$sql = "SELECT $key,$value FROM $table";
			if (!is_null($orderBy)) {$sql .= " ORDER BY $orderBy";}
                	$results = $this->query($sql . ";");
			$rows = [];
			while ($row = $results->fetchArray()) {$rows[$row[0]] = $row[1];}
			return $rows;
		} catch (Exception $e) {
			$this->errMsg($e, "loading table($table) $key, $value, $orderBy");
			return [];
		}
	}
}
?>
