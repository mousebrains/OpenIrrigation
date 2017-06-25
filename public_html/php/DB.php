<?php
class DBResults {
  function __construct($db, $sql, $results) {
    $this->results = $results;
    if (!$results) {
      throw(new Exception("Error executing '$sql', " . pg_last_error($db)));
    }
  }
  function fetchAll() {return pg_fetch_all($this->results);}
  function fetchArray() {return pg_fetch_array($this->results);}
  function fetchAssoc() {return pg_fetch_assoc($this->results);}
  function fetchRow() {return pg_fetch_row($this->results);}
  function querySingle() {
    $row = $this->fetchRow();
    return count($row) ? $row[0] : NULL;
  }

  function loadKeyValue() {
    $a = [];
    while ($row = $this->fetchRow()) { $a[$row[0]] = $row[1]; }
    return $a;
  }

  function loadColumn() {
    $a = [];
    while ($row = $this->fetchRow()) {array_push($a, $row[0]);}
    return $a;
  }
} // DBResults

class DBStatement {
  private static $cnt = 0;

  function __construct($db, string $sql) {
    $this->db = $db;
    $this->sql = $sql;
    ++self::$cnt;
    $this->name = "s" . self::$cnt;
    $results = pg_prepare($db, $this->name, $sql);
    if (!$results) {
      throw(new Exception("Error preparing '$sql', " . pg_last_error($db)));
    }
  }

  function execute(array $args=[]) {
    return new DBResults($this->db, $this->sql, pg_execute($this->db, $this->name, $args));
  }

  function querySingle(array $args=[]) {
    return $this->execute($args)->querySingle();
  }
} // DBStatement

class DB {
  private $cnt = 0;
  
  function __construct(string $dbname) {
    if (!($this->db = pg_connect("dbname=$dbname"))) {
      throw(new Exception("Error opening connection to $dbname"));
    }
  } // __construct
  
  function __destruct() {
    if (!pg_close($this->db)) {
      throw(new Exception("Error closing connection to $dbname, " . pg_last_error()));
    }
  } // __destruct
 
  function query(string $sql) {
    if (!pg_query($this->db, $sql)) {
      throw(new Exception("Error for '$sql', " . pg_last_error()));
    }
  }
 
  function begin() {$this->query('BEGIN;');}
  function commit() {$this->query('COMMIT;');}
  function rollback() {$this->query('ROLLBACK;');}
  
  function prepare(string $sql) {return new DBStatement($this->db, $sql);}
  function execute(string $sql, array $args=[]) {return $this->prepare($sql)->execute($args);}

  function insert(string $tbl, array $data) {
    $n = count($data);
    if ($n == 0) {return;}
    $keys = array_keys($data);
    $args = array_values($data);
    $vars = [];
    for ($i = 0; $i < $n; ++$i) array_push($vars, '$' . ($i+1));

    $sql = "INSERT INTO $tbl(" . implode($keys, ",") . ") VALUES (" . implode($vars, ",") . ");";
    $this->prepare($sql)->execute($args);
  }

  function update(string $tbl, array $data, array $criteria) {
    $n = count($data);
    if ($n == 0) {return;}
    $keys = array_keys($data);
    $args = array_values($data);
    $vars = [];
    for ($i = 0; $i < $n; ++$i) array_push($vars, '$' . ($i+1));

    $sql = "UPDATE $tbl SET (" . implode($keys, ",") . ")=(" . implode($vars, ",") . ")";

    $m = count($criteria);
    if ($m != 0) {
      $keys = array_keys($criteria);
      $vars = [];
      for ($i = 0; $i < $m; ++$i) {
        $key = $keys[$i];
        array_push($args, $criteria[$key]);
        array_push($vars, $key . '=$' . ($i + $n + 1));
      }
      $sql .= " WHERE " . implode($vars, " AND ");
    }
    $this->prepare($sql . ";")->execute($args);
  }


  function delete(string $tbl, array $criteria) {
    $sql = "DELETE FROM $tbl";
    $args = [];
    if (count($criteria) != 0) {
      $vars = [];
      $keys = array_keys($criteria);
      $args = array_values($criteria);
      for ($i = 0; $i < count($keys); ++$i) array_push($vars, $keys[$i] . '=$' . ($i+1));
      $sql .= " WHERE " . implode($vars, ' AND ');
    }
    $this->prepare($sql . ";")->execute($args);
  }

  function querySingle(string $sql, array $args=[]) {
    return $this->execute($sql, $args)->querySingle();
  }

  function loadKeyValue(string $sql, array $args=[]) {
    return $this->prepare($sql)->execute($args)->loadKeyValue();
  }

  function loadColumn(string $sql, array $args=[]) {
    return $this->prepare($sql)->execute($args)->loadColumn();
  }
} // DB

try {
  $db = new DB('irrigation');
} catch (Exception $e) {
  echo "<div><pre>" . $e->getMessage() . "</pre></div>\n";
  throw($e);
}
?>
