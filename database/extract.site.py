#! /usr/bin/env python3
#
# Extract site and log information from an existing Postgresql database
#
# The output is SQL INSERTs that recreate the configuration in a freshly
# installed database (make freshdb FORCE=1).  Every column of each table is
# exported except its id and, for usr, the password hash; foreign keys are
# written as lookups by name, since ids differ between databases.  Rows a
# fresh install already has -- soils, crops, and the "Manual <site>" program
# the site insert trigger creates -- are updated in place (ON CONFLICT).
#

from collections import OrderedDict
import datetime
import psycopg
from psycopg import sql as sql_module
from psycopg.rows import dict_row
import argparse

class Value:
    def __init__(self, val, conn=None):
        if val is None:
            self.val = "NULL"
        elif isinstance(val, str) and not val.isnumeric():
            self.val = sql_module.Literal(val).as_string(conn)
        elif isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
            self.val = sql_module.Literal(str(val)).as_string(conn)
        else:
            self.val = str(val)

    def __str__(self): return self.val
    def id(self): return int(self.val)

class KeyValue(dict):
    def __init__(self, db, sql):
        dict.__init__(self)
        with db.cursor() as cur:
            cur.execute(sql)
            for row in cur:
                self[row[0]] = Value(row[1], db)

class Info:
    def __init__(self, db):
        self.listGroup = KeyValue(db, 'SELECT id,grp FROM webList;')
        self.listKey = KeyValue(db, 'SELECT id,key FROM webList;')
        self.soils = KeyValue(db, 'SELECT id,name FROM soil;')
        self.crops = KeyValue(db, 'SELECT id,name FROM crop;')
        self.users = KeyValue(db, 'SELECT id,name FROM usr;')
        self.emails = KeyValue(db, 'SELECT id,email FROM email;')
        self.sites = KeyValue(db, 'SELECT id,name FROM site;')
        self.ctls = KeyValue(db, 'SELECT id,name FROM controller;')
        self.ctl2site = KeyValue(db, 'SELECT id,site FROM controller;')
        self.mapFeatures = KeyValue(db, 'SELECT id,name FROM mapFeature;')
        self.map2site = KeyValue(db, 'SELECT id,site FROM mapFeature;')
        self.sensors = KeyValue(db, 'SELECT id,name FROM sensor;')
        self.sens2ctl = KeyValue(db, 'SELECT id,controller FROM sensor;')
        self.pocs = KeyValue(db, 'SELECT id,name FROM poc;')
        self.poc2site = KeyValue(db, 'SELECT id,site FROM poc;')
        self.pocFlows = KeyValue(db, 'SELECT id,name FROM pocFlow;')
        self.pocFlow2poc = KeyValue(db, 'SELECT id,poc FROM pocFlow;')
        self.programs = KeyValue(db, 'SELECT id,name FROM program;')
        self.pgmStn2program = KeyValue(db, 'SELECT id,program FROM pgmStn;')
        self.pgmStn2station = KeyValue(db, 'SELECT id,station FROM pgmStn;')
        self.stations = KeyValue(db, 'SELECT id,sensor FROM station;')

    def list(self, id):
        return "(SELECT id FROM webList WHERE grp={} AND key={})".format(
                self.listGroup[id], self.listKey[id])

    def soil(self, id):
        return "(SELECT id FROM soil WHERE name={})".format(self.soils[id])

    def crop(self, id):
        return "(SELECT id FROM crop WHERE name={})".format(self.crops[id])

    def user(self, id):
        return "(SELECT id FROM usr WHERE name={})".format(self.users[id])

    def email(self, id):
        return "(SELECT id FROM email WHERE email={})".format(self.emails[id])

    def site(self, id):
        return "(SELECT id FROM site WHERE name={})".format(self.sites[id])

    def ctl(self, id):
        return "(SELECT id FROM controller WHERE name={} AND site={})".format(
                self.ctls[id], self.site(self.ctl2site[id].id()))

    def mapFeature(self, id):
        return "(SELECT id FROM mapFeature WHERE name={} AND site={})".format(
                self.mapFeatures[id], self.site(self.map2site[id].id()))

    def sensor(self, id):
        return "(SELECT id FROM sensor WHERE name={} AND controller={})".format(
                self.sensors[id], self.ctl(self.sens2ctl[id].id()))

    def poc(self, id):
        return "(SELECT id FROM poc WHERE name={} AND site={})".format(
                self.pocs[id], self.site(self.poc2site[id].id()))

    def pocFlow(self, id):
        return "(SELECT id FROM pocFlow WHERE name={} AND poc={})".format(
                self.pocFlows[id], self.poc(self.pocFlow2poc[id].id()))

    def program(self, id):
        return "(SELECT id FROM program WHERE name={})".format(self.programs[id])

    def pgmStn(self, id):
        if id is None: return "NULL"
        return "(SELECT id FROM pgmStn WHERE program={} AND station={})".format(
                self.program(self.pgmStn2program[id].id()),
                self.station(self.pgmStn2station[id].id()))

    def station(self, id):
        return "(SELECT id FROM station WHERE sensor={})".format(
                self.sensor(self.stations[id].id()))

def outputEntries(comment, tbl, names, entries, conflict=None):
    if entries:
        print("\n-- BEGIN ", comment)
        print("INSERT INTO ", tbl + "(" + ",".join(names) + ")", "VALUES")
        print(" {}".format(",\n ".join(entries)))
        if conflict: # Overwrite a row the fresh install already has
            print(" ON CONFLICT ({}) DO UPDATE SET {}".format(conflict, ",".join(
                "{0}=EXCLUDED.{0}".format(name) for name in names if name != conflict)))
        print(";")
        print("-- END ", comment)

def mkBase(row, fields):
    a = []
    for field in fields: a.append(str(Value(row[field])))
    return ",".join(a)

def mkSpecial(row, fields):
    a = []
    for key in fields: a.append("NULL" if row[key] is None else fields[key](row[key]))
    return ",".join(a)

def dataFields(db, tbl, sFields, exclude=()):
    """Every column of tbl except id, the lookup columns in sFields, and exclude.

    Exits if a foreign-key column is not in sFields: exporting it as a raw id
    would point at the wrong row in another database.
    """
    with db.cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns"
                    " WHERE table_schema='public' AND table_name=lower(%s)"
                    " ORDER BY ordinal_position;", (tbl,))
        columns = [row[0] for row in cur]
        cur.execute("SELECT a.attname FROM pg_constraint c"
                    " JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=ANY(c.conkey)"
                    " WHERE c.contype='f' AND c.conrelid=to_regclass(lower(%s));", (tbl,))
        fkeys = {row[0] for row in cur}
    unmapped = fkeys.difference(sFields)
    if unmapped:
        raise SystemExit("{} has foreign key column(s) {} with no lookup".format(tbl, sorted(unmapped)))
    return [c for c in columns if c != 'id' and c not in sFields and c not in exclude]

def getBasic(db, sql, comment, tbl, conflict=None, exclude=()):
    getSpecial(db, OrderedDict(), sql, comment, tbl, conflict, exclude)

def getSpecial(db, sFields, sql, comment, tbl, conflict=None, exclude=()):
    fields = dataFields(db, tbl, sFields, exclude)
    with db.cursor(row_factory=dict_row) as cur:
        entries = []
        cur.execute(sql)
        for row in cur:
            a = [mkSpecial(row, sFields)] if sFields else []
            if fields:
                a.append(mkBase(row, fields))
            entries.append("(" + ",".join(a) + ")")
        outputEntries(comment, tbl, list(sFields.keys()) + fields, entries, conflict)

def getSoil(db):
    getBasic(db, 'SELECT * FROM soil ORDER BY name;', 'Soil Information', 'soil', conflict='name')

def getCrop(db):
    getBasic(db, 'SELECT * FROM crop ORDER BY name;', 'Crop Information', 'crop', conflict='name')

def getUser(db):
    # Password hashes stay behind; set passwords again after restoring
    getBasic(db, 'SELECT * FROM usr ORDER BY name;', 'User Information', 'usr',
             exclude=('passwd',))

def getEMail(db, info):
    sFields = OrderedDict([('usr', info.user), ('format', info.list)])
    getSpecial(db, sFields, 'SELECT * FROM email ORDER BY email;',
            'EMail addresses', 'email')

def getEMailReports(db, info):
    sFields = OrderedDict([('email', info.email), ('report', info.list)])
    getSpecial(db, sFields, 'SELECT * FROM emailReports ORDER BY email;',
            'email/report information', 'emailReports')

def getSite(db):
    getBasic(db, 'SELECT * FROM site ORDER BY name;', 'Site Information', 'site')

def getController(db, info):
    sFields = OrderedDict([('site', info.site)])
    getSpecial(db, sFields, 'SELECT * FROM controller ORDER BY name;',
            'controller information', 'controller')

def getMapFeature(db, info):
    sFields = OrderedDict([('site', info.site), ('kind', info.list)])
    getSpecial(db, sFields, 'SELECT * FROM mapFeature ORDER BY site,name;',
            'site map features', 'mapFeature')

def getSensor(db, info):
    sFields = OrderedDict([('controller', info.ctl), ('devtype', info.list),
        ('mapfeature', info.mapFeature)])
    getSpecial(db, sFields, 'SELECT * FROM sensor ORDER BY addr;',
            'sensor information', 'sensor')

def getPOC(db, info):
    sFields = OrderedDict([('site', info.site)])
    getSpecial(db, sFields, 'SELECT * FROM poc ORDER BY name;',
            'point-of-connect information', 'poc')

def getPOCFlow(db, info):
    sFields = OrderedDict([('poc', info.poc), ('sensor', info.sensor)])
    getSpecial(db, sFields, 'SELECT * FROM pocFlow ORDER BY name;',
            'point-of-connect flow information', 'pocFlow')

def getPOCMV(db, info):
    sFields = OrderedDict([('poc', info.poc), ('sensor', info.sensor)])
    getSpecial(db, sFields, 'SELECT * FROM pocMV ORDER BY name;',
            'point-of-connect master valve information', 'pocMV')

def getPOCPump(db, info):
    sFields = OrderedDict([('poc', info.poc), ('sensor', info.sensor)])
    getSpecial(db, sFields, 'SELECT * FROM pocPump ORDER BY name;',
            'point-of-connect booster pump information', 'pocPump')

def getStation(db, info):
    sFields = OrderedDict([('poc', info.poc), ('sensor', info.sensor)])
    getSpecial(db, sFields, 'SELECT * FROM station ORDER BY name;',
            'station information', 'station')

def getProgram(db, info):
    sFields = OrderedDict([('site', info.site), ('onoff', info.list),
        ('action', info.list), ('startmode', info.list), ('stopmode', info.list)])
    # The site insert trigger has already made each "Manual <site>" program
    getSpecial(db, sFields, 'SELECT * FROM program ORDER BY priority,name;',
            'program information', 'program', conflict='name')

def getProgramDOW(db, info):
    sFields = OrderedDict([('program', info.program), ('dow', info.list)])
    getSpecial(db, sFields, 'SELECT * FROM pgmDOW ORDER BY program,dow;',
            'program/day-of-week information', 'pgmDOW')

def getProgramStation(db, info):
    sFields = OrderedDict([('program', info.program), ('station', info.station),
        ('mode', info.list)])
    getSpecial(db, sFields, 'SELECT * FROM pgmStn ORDER BY program,station;',
            'program/station information', 'pgmStn')

def getETStation(db, info):
    sFields = OrderedDict([('station', info.station), ('crop', info.crop), ('soil', info.soil)])
    getSpecial(db, sFields, 'SELECT * FROM ETStation ORDER BY station;',
            'ET/station information', 'ETStation')

def getHistorical(db, info):
    sFields = OrderedDict([('sensor', info.sensor), ('program', info.program),
        ('pgmstn', info.pgmStn)])
    sql = "SELECT * FROM historical ORDER BY tOn,sensor;"
    getSpecial(db, sFields, sql, "Historical information", "historical")

def logBasic(db, info, tbl, sFields=None):
    if sFields is None:
        sFields = [('controller', info.ctl)]
    getSpecial(db, OrderedDict(sFields), 'SELECT * FROM ' + tbl + ' ORDER BY timestamp;',
            tbl + " message log", tbl)

parser = argparse.ArgumentParser()
parser.add_argument('--db', help='database name', required=True)
args = parser.parse_args()

with psycopg.connect(dbname=args.db) as db:
    info = Info(db)
    print('-- Generated', datetime.datetime.now())
    getSoil(db)
    getCrop(db)
    getUser(db)
    getEMail(db, info)
    getEMailReports(db, info)
    getSite(db)
    getController(db, info)
    getMapFeature(db, info)
    getSensor(db, info)
    getPOC(db, info)
    getPOCFlow(db, info)
    getPOCMV(db, info)
    getPOCPump(db, info)
    getStation(db, info)
    getProgram(db, info)
    getProgramDOW(db, info)
    getProgramStation(db, info)
    getETStation(db, info)

    getHistorical(db, info)
    # logBasic(db, info, 'zeeLog')
    # logBasic(db, info, 'numberLog')
    # logBasic(db, info, 'versionLog')
    # logBasic(db, info, 'errorLog')
    # logBasic(db, info, 'twoLog')
    # logBasic(db, info, 'peeLog')
    # logBasic(db, info, 'teeLog', [('sensor', info.sensor)])
    # logBasic(db, info, 'sensorLog', [('pocflow', info.pocFlow)])
    # logBasic(db, info, 'currentLog')
