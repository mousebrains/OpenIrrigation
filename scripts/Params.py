#
# Load parameters from a database table, params.
# The table is expected to have at least three columns,
#   grp is a group name that is selected on
#   name is the key for val in the internal dictionary
#   val is the value associated with key
#
# If value has a comma an array is created.
#
# Each value is converted to
#            an integer,
#            a float, or
#            leading/trailing blanks are stripped off

from DB import DB

def __toNum(val: str):
    try: # Try and convert to an integer
        return int(val)
    except (ValueError, TypeError): # Failed, so now try a float
        try:
            return float(val)
        except (ValueError, TypeError): # Failed, so return the string
            return val.strip()

def __decode(val: str):
    """ Try and split str by commas and convert elements to numbers
        if all the elements are numeric """

    if ',' not in val: return __toNum(val.strip())
    a = []
    nNumeric =  0
    for item in val.split(','):
        a.append(__toNum(item))
        nNumeric += isinstance(a[-1], int) or isinstance(a[-1], float)
    return a if nNumeric == len(a) else val.strip()

def load(dbName:str, grp:str, logger) -> dict:
    """ Load parameters for group grp from database dbName """
    db = DB(dbName, logger)
    info = {}
    with db.cursor() as cur:
        cur.execute('SELECT name,val FROM params WHERE grp=%s;', (grp,))
        for row in cur:
            info[row[0]] = __decode(row[1])
    return info if info else None
