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

class Params(dict): # Parameters loaded from a database
    def __init__(self, db, grp):
        dict.__init__(self)
        for row in db.read('SELECT name,val FROM params WHERE grp=?;', (grp,)):
            val = row[1]
            if ',' in val:
                a = []
                for item in val.split(','):
                    a.append(self.__toNum(item))
                val = a
            else:
                val = self.__toNum(val)

            self[row[0]] = val

    def __toNum(self, val):
        try:
            return int(val)
        except:
            try:
                return float(val)
            except:
                return val.strip()
