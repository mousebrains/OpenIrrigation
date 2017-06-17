<?php
class ColumnInput {
  // <input ... >
  function __construct(array $row, $db) {
    $this->key = $row['col'];
    $this->label = $row['label'];
    $this->type = $row['inputtype'];
    $this->qRequired = $row['qrequired'] == 't';
    $this->placeholder = $row['placeholder'];
    $this->converter = $row['converter'];
    $this->valMin = $row['valmin'];
    $this->valMax = $row['valmax'];
    $this->valStep = $row['valstep'];
    $this->prefix = $this->mkPrefix();
    $this->middle = $this->mkMiddle();
    $this->suffixNotRequired = "'>";
    $this->suffixRequired = $this->qRequired ? "' required>" : $this->suffixNotRequired;
  }

  function mkPrefix() {
    $a = "<input type='" . $this->type . "'";
    if (!is_null($this->placeholder)) $a .= " placeholder='" . $this->placeholder . "'";
    if ($this->type == "number") {
      if (!is_null($this->valMin)) $a .= " min='" . $this->valMin . "'";
      if (!is_null($this->valMax)) $a .= " max='" . $this->valMax . "'";
      if (!is_null($this->valStep)) $a .= " step='" . $this->valStep . "'";
    }
    $a.= " name='" . $this->key . "[";
    return $a;
  }

  function mkMiddle() {return "]' value='";}

  function qLoadData() {return True;}
  function qDisplay() {return True;}
  function qMultiple() {return False;}

  function qChanged(array $post, array $prev) {
    $key = $this->key;
    if (array_key_exists($key, $post)) {
      if (array_key_exists($key, $prev)) {
        $a = $post[$key]; // From web, so a string
        $b = $prev[$key]; // From database, so may be a float
        if (is_numeric($a) and is_numeric($b)) {
          return abs($a - $b) > 1e-10; // Really small difference
        }
        return $a != $b;
      }
      return True;
    }
    return array_key_exists($key, $prev);
  }

  function convert2web(array $row=NULL) {
    $val = (!is_null($row) and array_key_exists($this->key, $row)) ? $row[$this->key] : "";
    if (!empty($val) and ($this->type == "number")) {
      if (!is_null($this->valMin)) $val = max($val, $this->valMin);
      if (!is_null($this->valMax)) $val = min($val, $this->valMax);
      if (!is_null($this->valStep)) $val = round($val / $this->valStep) * $this->valStep;
    }
    if ($this->type == "password") return "";
    return $val;
  }

  function convert2db(string $val) {
    if (($this->type == "password") and ($val != "")) return password_hash($val, PASSWORD_DEFAULT);
    return $val;
  }

  function mkInput(array &$previous, int $cnt, array $row=NULL) {
    return $this->prefix
	. $cnt 
	. $this->middle 
	. $this->mkNoDisplay($row, $previous)
	. (is_null($row) ? $this->suffixNotRequired : $this->suffixRequired);
  }

  function mkNoDisplay(array $row=NULL, array &$previous) {
    $key = $this->key;
    $val = $this->convert2web($row);
    $previous[$key] = $val;
    return $val;
  }
} // ColumnInput

class ColumnTextArea extends ColumnInput {
  // <textarea ... >...</textarea>
  function __construct(array $row, $db) {
    parent::__construct($row, $db);
    $this->suffixNotRequired = "</textarea>";
    $this->suffixRequired = $this->suffixNotRequired;
  }

  function mkPrefix() {
    $a = "<textarea";
    if (!is_null($this->placeholder)) $a .= " placeholder='" . $this->placeholder . "'";
    $a .= " name='" . $this->key . "[";
    return $a;
  }

  function mkMiddle() {return "]'>";}

  function convert2db(string $val) {return $val;}
} // ColumnTextArea

class ColumnCheckbox extends ColumnInput {
  // <input type='checkbox'...>
  function __construct(array $row, $db) {
    parent::__construct($row, $db);
  }

  function mkPrefix() {
    return "<input type='checkbox' value='t' name='" . $this->key . "[";
  }

  function convert2db(string $val) {return ($val == "t") ? "True" : "False";}

  function mkInput(array &$previous, int $cnt, array $row=NULL) {
    $id = (is_null($row) or !array_key_exists("id", $row)) ? 0 : $row["id"];
    $val = $this->mkNoDisplay($row, $previous);
    $a = $this->prefix . $cnt . "]'";
    if ($val) $a .= " checked";
    return $a . ">";
  }

  function mkNoDisplay(array $row=NULL, array &$previous) {
    $key = $this->key;
    $val = (is_null($row) or !array_key_exists($this->key, $row)) ? False : 
		($row[$this->key] == "t");
    $previous[$key] = $val;
    return $val;
  }
} // ColumnCheckbox

class ColumnSelect extends ColumnInput {
  // <select ...>...</select>
  function __construct(array $row, $db) {
    $this->refTable = $row['reftable'];
    $this->refKey = $row['refkey'];
    $this->refLabel = $row['reflabel'];
    $this->refCriteria = $row['refcriteria'];
    $this->refOrderBy = $row['reforderby'];
    $this->references = $this->loadReferences($db);
    parent::__construct($row, $db);
  }

  function mkPrefix() {
    return "<select name='" . $this->key . "[";
  }

  function mkMiddle() {return "]'>\n";}

  function qDisplay() {return count($this->references) > 1;}

  function loadReferences($db) {
    $sql = "SELECT " . $this->refKey . "," . $this->refLabel 
	. " FROM " . $this->refTable;
    if (!is_null($this->refCriteria)) $sql .= " WHERE " . $this->refCriteria;
    if (!is_null($this->refOrderBy)) $sql .= " ORDER BY " . $this->refOrderBy;
    return $db->loadKeyValue($sql . ";");
  }

  function convert2web(array $row=NULL) {
    if (!is_null($row) and array_key_exists($this->key, $row)) {return $row[$this->key];}
    if (empty($this->references)) return "";
    return array_keys($this->references)[0];
  }

  function convert2db(string $val) {return $val;}

  function mkInput(array &$previous, int $cnt, array $row=NULL) {
    $val = $this->mkNoDisplay($row, $previous);
    $a = $this->prefix . $cnt . $this->middle;
    foreach ($this->references as $k => $v) {
      $a .= "<option value='$k'";
      if ($k == $val) $a .= " selected";
      $a .= ">$v</option>\n";
    }
    return $a . "</select>";
  }
} // Column Select

class ColumnMultiple extends ColumnSelect {
  // <select ... multiple>...</select>
  function __construct(array $row, $db) {
    parent::__construct($row, $db);
    $this->secondaryKey = $row['secondarykey'];
    $this->secondaryValue = $row['secondaryvalue'];
    $this->secondary = $this->loadSecondary($db);
  }

  function mkPrefix() {return "<select multiple name='" . $this->key . "[";}

  function qLoadData() {return False;}
  function qDisplay() {return True;}
  function qChanged(array $post, array $prev) {return False;}
  function qMultiple() {return True;}

  function loadSecondary($db) {
    $sql = "SELECT " . $this->secondaryKey . "," . $this->secondaryValue
	. " FROM " . $this->key . ";";
    $results = $db->execute($sql);
    $a = [];
    while ($row = $results->fetchRow()) {
      $key = $row[0];
      if (!array_key_exists($key, $a)) $a[$key] = [];
      array_push($a[$key], $row[1]);
    }
    return $a;
  } 

  function mkInput(array &$previous, int $cnt, array $row=NULL) {
    $id = is_null($row) ? 0 : $row['id'];
    $a = $this->prefix . $cnt . "][]>\n";
    $key = $this->key;
    if (!array_key_exists($key, $previous)) $previous[$key] = [];
    $keys = array_key_exists($id, $this->secondary) ? $this->secondary[$id] : [];
    $val = $this->convert2web($row);
    foreach ($this->references as $k => $v) {
      $a .= "<option value='$k'";
      if (in_array($k, $keys)) {
        $a .= " selected";
        array_push($previous[$key], $k);
      }
      $a .= ">$v</option>\n";
    }
    return $a . "</select>";
  }
} // Column Multiple

function mkColumnInfo(array $row, $db) {
  $type = $row['inputtype'];
  if ($type == 'multiple') return new ColumnMultiple($row, $db);
  if ($type == 'textarea') return new ColumnTextArea($row, $db);
  if ($type == 'checkbox') return new ColumnCheckbox($row, $db);
  if (!is_null($row['reftable'])) return new ColumnSelect($row, $db);
  return new ColumnInput($row, $db);
}

class PageBuilder {
  function __construct(string $key, $db, array $info=[]) {
    session_start();
    try {
      $this->key = $key;
      $this->db = $db;
      $this->table = $this->ifExists($info, 'table', $key);
      $this->qTable = $this->ifExists($info, 'qTable', True);
      $this->qDelete = $this->ifExists($info, 'qDelete', True);
      $this->qScheduler = $this->ifExists($info, 'qScheduler', False);
      $this->columns = $this->ifExists($info, 'columns', NULL);
      $this->keyCol = $this->ifExists($info, 'keyCol', 'id');
      $this->criteria = $this->ifExists($info, 'criteria', NULL);
      $this->orderBy = $this->ifExists($info, 'orderBy', NULL);
      $this->qBlank = $this->ifExists($info, 'qBlank', True);
      $this->getInfo(); // Get column information
    } catch (Exception $e) {
      echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
    }
  }

  function ifExists(array $a, string $key, $val) {
    return array_key_exists($key, $a) ? $a[$key] : $val;
  }

  function postUp(array $post) {
    try {
      $this->db->begin(); // Start a transaction block
      $this->postUpArray($post);
      $this->db->commit(); // Commit what was done
    } catch (Exception $e) {
      $this->db->rollback(); // Discard transaction block on an error
      echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
    }
  }

  function postUpArray(array $post) {
    // echo "<pre>postUpArray\n"; var_dump($post); echo "</pre>";
    // global $_SESSION;
    // echo "<pre>SESSION\n"; var_dump($_SESSION); echo "</pre>";
    $deleted = array_key_exists('delete', $post) ? $post['delete'] : [];
    if ($deleted) $deleted = $this->postDelete($deleted, $post); // Delete entries

    $n = count($post['id']);
    for ($i = 0; $i < $n; ++$i) {
      $id = $post['id'][$i];
      if (in_array($id, $deleted)) continue; // Deleted this entry, so skip it
      $row = ['id'=>$id];
      foreach ($this->colInfo as $a) {
        $key = $a->key;
        if (array_key_exists($key, $post) and array_key_exists($i, $post[$key])) {
          $row[$key] = $post[$key][$i];
        } else {
          $row[$key] = "";
        }
      }
      $post['id'][$i] = $this->postUpSingle($row);  // Reset id for inserted record for multiple
    }

    if (!empty($this->multipleInfo)) $this->postMultiple($post);
  }

  function postUpSingle(array $row) {
    // echo "<pre>postUpSingle\n"; var_dump($row); echo "</pre>";
    global $_SESSION;
    $id = $row['id'];

    $sessID = $this->mkSessionID($id);
    $columns = [];
    if (array_key_exists($sessID, $_SESSION)) {
      $prev = $_SESSION[$sessID];
      foreach ($this->colInfo as $a) {
        if ($a->qChanged($row, $prev)) array_push($columns, $a);
      }
    } else {
      foreach ($this->colInfo as $a) {
        if (!$a->qMultiple()) array_push($columns, $a);
      }
    }
    if (count($columns)) { // Something to be updated/inserted
      $toUpdate = [];
      foreach ($columns as $a) {
        $key = $a->key;
        $toUpdate[$key] = $a->convert2db($row[$key]); 
      }
      if ($id > 0) { // An update
        $criteria = [$this->keyCol => $id];
        echo "<pre>UPDATE " . $this->table . " SET ("
		. implode(array_keys($toUpdate), ",")
		. ")=("
		. implode(array_values($toUpdate), ",")
		. ") WHERE ("
		. implode(array_keys($criteria), ",")
		. ")=("
		. implode(array_values($criteria), ",")
		. ");\n</pre>";
        $this->db->update($this->table, $toUpdate, $criteria);
      } else { // An insert
        $toUpdate = [];
        foreach ($this->colInfo as $a) { // We want all columns
          if (!$a->qMultiple()) {
            $key = $a->key;
            $val = $a->convert2db($row[$key]);
            if ($val != '') $toUpdate[$key] = $val;
          }
        }
        echo "<pre>INSERT INTO " . $this->table . "("
		. implode(array_keys($toUpdate), ",")
		. ") VALUES("
		. implode(array_values($toUpdate), ",")
		. ");\n</pre>";
        $this->db->insert($this->table, $toUpdate);
        if (count($this->multipleInfo)) { // find the id of inserted row for postMultiple
          $oid = $this->db->querySingle("SELECT lastval();"); // session dependent
          $id = is_null($oid) ? $id : $oid;
          echo "<pre>New ID=$id</pre>";
        }
      }
    }
    return $id; // $id of inserted record
  }

  function postDelete($deleted, array $post) { // Delete entries
    if (count($post['id']) == 1) $deleted = $post['id']; // Single entry
    $vars = [];
    for ($i = 0; $i < count($deleted); ++$i) {
      array_push($vars, "$" . ($i + 1));
    }
    $sql = "DELETE FROM " . $this->table . " WHERE " . $this->keyCol . " IN ("
    	. implode($vars, ",") . ");";
    echo "<pre>$sql (" . implode($deleted, ",") . ")</pre>\n";
    $this->db->execute($sql, $deleted);
    return $deleted;
  } // postDelete

  function postMultiple(array $post) {
    global $_SESSION;
    $n = count($post['id']);
    foreach ($this->multipleInfo as $item) {
      $key = $item->key;
      $toDel = [];
      $toAdd = [];
      for ($i = 0; $i < $n; ++$i) {
        $id = $post['id'][$i];
        if ($id == 0) continue;
        $sessID = $this->mkSessionID($id);
        $prev = array_key_exists($sessID, $_SESSION) ? $_SESSION[$sessID] : [];
        $a = (array_key_exists($key, $post) and array_key_exists($i, $post[$key]))
		? $post[$key][$i] : [];
        $b = array_key_exists($key, $prev) ? $prev[$key] : [];
        foreach (array_diff($b, $a) as $oid) array_push($toDel, [intval($id), intval($oid)]);
        foreach (array_diff($a, $b) as $oid) array_push($toAdd, [intval($id), intval($oid)]);
      }
      $qChanged = False;
      if (count($toDel)) { // Something to delete
        $qChanged = True;
        $sql = "DELETE FROM $key WHERE (" . $item->secondaryKey . ","
		. $item->secondaryValue . ")=($1,$2);";
        $stmt = $this->db->prepare($sql);
        foreach ($toDel as $a) {
          echo "<pre>$sql (" . implode($a, ",") . ")\n</pre>";
          $stmt->execute($a);
        }
      }
      if (count($toAdd)) { // Something to add
        $qChanged = True;
        $sql = "INSERT INTO $key(" . $item->secondaryKey 
		. "," . $item->secondaryValue . ") VALUES($1,$2);";
        $stmt = $this->db->prepare($sql);
        foreach ($toAdd as $a) {
          echo "<pre>$sql (" . implode($a, ",") . ")\n</pre>";
          $stmt->execute($a);
        }
      }
      if ($qChanged) $item->secondary = $item->loadSecondary($this->db); // Reload after we changed
    } // Loop over multipleInfo
  } // postMultiple

  function mkPage() {
    try {
      if ($this->qTable) {
        $this->mkSingleTable();
      } else {
        $this->mkManyTables();
      }
    } catch (Exception $e) {
      echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
    }
  } // mkPage

  function mkSingleTable() { // Build as a single table/form
    $hdr = $this->qDelete ? ['Delete'] : [];
    foreach ($this->colInfo as $a) {
      if ($a->qDisplay()) array_push($hdr, $a->label);
    }
    $hdr = "<tr><th>" . implode($hdr, "</th><th>") . "</th></tr>\n";
    echo "<center>\n";
    echo "<form method='post'>\n";
    echo "<table>\n";
    echo "<thead>$hdr</thead>\n"; 
    $cnt = 0;
    $hidden = [];
    $results = $this->db->execute($this->mkDataSQL());
    while ($row = $results->fetchAssoc()) {
      $this->mkSingleRow($hidden, $cnt, $row); 
      ++$cnt;
    }
    if ($this->qBlank) $this->mkSingleRow($hidden, $cnt, NULL);
    echo "<tfoot>$hdr</tfoot>\n"; 
    echo "</table>\n";
    foreach ($hidden as $item) {echo $item . "\n";}
    echo "<input type='submit' name='update' value='Update'>\n";
    if ($this->qScheduler) echo "<input type='submit' name='scheduler' value='Run Scheduler'>\n";
    echo "</form>\n";
    echo "</center>\n";
  }

  function mkDelete(string $id) {
    return "<input type='checkbox', name='delete[]', value='$id'>";
  }

  function mkHidden(string $key, string $cnt, string $val) {
    return "<input type='hidden' name='$key" . "[$cnt]' value='$val'>";
  }

  function mkSingleRow(array &$hidden, int $cnt, array $row=NULL) {
    global $_SESSION;
    $id = is_null($row) ? 0 : $row[$this->keyCol];
    $prev = [];
    array_push($hidden, $this->mkHidden('id', $cnt, $id)); 
    echo "<tr>\n";
    if ($this->qDelete) {
      echo "<th>";
      if ($id > 0) echo $this->mkDelete($id);
      echo "</th>\n";
    }
    foreach ($this->colInfo as $a) {
      if ($a->qDisplay()) {
        echo "<td>" .  $a->mkInput($prev, $cnt, $row) . "</td>\n";
      } else {
        array_push($hidden, $this->mkHidden($a->key, $cnt, $a->mkNoDisplay($row, $prev)));
      }
    }
    echo "</tr>\n";
    $_SESSION[$this->mkSessionID($id)] = $prev;
  }

  function mkManyTables() { // Build as many tables/forms
    $results = $this->db->execute($this->mkDataSQL());
    $qRule = False;
    while ($row = $results->fetchAssoc()) {
      if ($qRule) echo "<hr>\n";
      $qRule = True;
      $this->mkOneTable($row);
    }
    if ($qRule) echo "<hr>\n";
    $this->mkOneTable(NULL);
  }

  function mkOneTable(array $row=NULL) {
    global $_SESSION;
    $id = is_null($row) ? 0 : $row[$this->keyCol];
    $hidden = [$this->mkHidden('id', 0, $id)];
    $prev = [];
    echo "<center>\n";
    echo "<form method='post'>\n";
    echo "<table>\n";
    echo "<tbody>\n";
    foreach ($this->colInfo as $a) {
      if ($a->qDisplay()) {
        echo "<tr><th>" . $a->label . "</th><td>" . $a->mkInput($prev, 0, $row) . "</td></tr>\n";
      } else { // ColumnMultiple will always display
	$a->mkNodisplay($row, $prev);
        array_push($hidden, $this->mkHidden($a->key, 0, $a->convert2web($row)));
      }
    }
    echo "</tbody>\n";
    echo "</table>\n";
    if (is_null($row)) { // An empty table
      echo "<input type='submit' name='update' value='Create'>\n";
    } else { // Not an empty table
      echo "<input type='submit' name='update' value='Update'>\n";
      echo "<input type='submit' name='delete' value='Delete'>\n";
    }
    foreach ($hidden as $item) echo $item . "\n";
    echo "</form>\n";
    echo "</center>\n";
    $_SESSION[$this->mkSessionID($id)] = $prev;
  }

  function mkDataSQL() { // Return SQL to fetch data rows
    $names = [$this->keyCol];
    foreach ($this->colInfo as $a) {
      if ($a->qLoadData()) array_push($names, $a->key);
    }
    $sql = "SELECT " . implode($names, ",") . " FROM " . $this->table;
    if (!is_null($this->criteria)) $sql .= " WHERE " . $this->criteria;
    if (!is_null($this->orderBy)) $sql .= " ORDER BY " . $this->orderBy;
    return $sql . ";";
  }

  function mkSessionID(string $id=NULL) {return "ID$id";} // Key for use in $_SESSION

  function getInfo() { // Extract information on how to build the page from db
    $sql = "SELECT * FROM tableInfo WHERE tbl=$1";
    $args = [$this->table];
    if (!empty($this->columns)) {
      $sql .= ' AND col IN(';
      $vars = [];
      for ($i=0; $i < count($this->columns); ++$i) {
        array_push($vars, '$' . ($i+2));
        array_push($args, $this->columns[$i]);
      } 
      $sql .= implode($vars, ',') . ');';
    }
    $this->colInfo = [];
    $this->multipleInfo = [];
    $results = $this->db->execute($sql . ' ORDER BY displayOrder;', $args);
    while ($row = $results->fetchAssoc()) {
      $a = mkColumnInfo($row, $this->db);
      array_push($this->colInfo, $a);
      if ($a->qMultiple()) array_push($this->multipleInfo, $a);
    }
  }
} // PageBuilder
