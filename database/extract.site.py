#! /usr/bin/env python3
#
# Extract site and log information from an existing Postgresql database
#

from collections import OrderedDict
import datetime 
import psycopg2 
import psycopg2.extras 
import argparse

class Value:
    def __init__(self, val):
        if val is None:
            self.val = "NULL"
        elif isinstance(val, str) and not val.isnumeric():
            self.val = str(psycopg2.extensions.QuotedString(val))
        elif isinstance(val, datetime.datetime) \
             or isinstance(val, datetime.date) \
             or isinstance(val, datetime.time):
            self.val = str(psycopg2.extensions.QuotedString(str(val)))
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
                self[row[0]] = Value(row[1])

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
        self.events = KeyValue(db, 'SELECT id,name FROM event;')
        self.groups = KeyValue(db, 'SELECT id,name FROM groups;')

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

    def event(self, id):
        return "(SELECT id FROM event WHERE name={})".format(self.events[id])

    def group(self, id):
        return "(SELECT id FROM groups WHERE name={})".format(self.groups[id])


def outputEntries(comment, tbl, entries):
    if entries:
        print("\n--", comment)
        print("INSERT INTO", tbl, "VALUES")
        print("{};".format(",\n".join(entries)))

def mkBase(row, fields):
    a = []
    for field in fields: a.append(str(Value(row[field])))
    return ','.join(a)

def mkSpecial(row, fields):
    a = []
    for key in fields: a.append(fields[key](row[key]))
    return ",\n  ".join(a)


def getBasic(db, fields, sql, comment, tbl):
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        entries = []
        cur.execute(sql)
        for row in cur:
            entries.append(" (" + mkBase(row, fields) + ")")
        outputEntries(comment, tbl + "(" + ",".join(fields) + ")", entries)

def getSpecial(db, fields, sFields, sql, comment, tbl):
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        entries = []
        cur.execute(sql)
        for row in cur:
            a = " (" + mkSpecial(row, sFields)
            if fields:
                a += ",\n"
                a+= "  " + mkBase(row, fields)
            a+= ")"
            entries.append(a)
        names = ",".join(sFields.keys())
        if fields:
            names += "," + ",".join(fields)
        outputEntries(comment, tbl + "(" + names + ")", entries)

def getSoil(db):
    fields = ['name', 'paw', 'infiltration', 'infiltrationslope', 'rootnorm']
    getBasic(db, fields, 'SELECT * FROM soil ORDER BY name;', 'Soil Information', 'soil')

def getCrop(db):
    fields = ['name', 'plantdate', 'lini', 'ldev', 'lmid', 'llate', 
            'kcinit', 'kcmid', 'kcend', 'height', 'depth', 'mad', 'notes']
    getBasic(db, fields, 'SELECT * FROM crop ORDER BY name;', 'Crop Information', 'crop')

def getUser(db):
    fields = ['name']
    getBasic(db, fields, 'SELECT * FROM usr ORDER BY name;', 'User Information', 'usr')

def getEMail(db, info):
    sFields = OrderedDict([('usr', info.user), ('format', info.list)])
    fields = ['email']
    getSpecial(db, fields, sFields, 'SELECT * FROM email ORDER BY email;', 
            'EMail addresses', 'email')

def getEMailReports(db, info):
    sFields = OrderedDict([('email', info.email), ('report', info.list)])
    getSpecial(db, [], sFields, 'SELECT * FROM emailReports ORDER BY email;',
            'email/report information', 'emailReports')

def getSite(db):
    fields = ['name', 'addr', 'timezone', 'latitude', 'longitude', 'elevation']
    getBasic(db, fields, 'SELECT * FROM site ORDER BY name;', 'Site Information', 'site')

def getController(db, info):
    sFields = OrderedDict([('site', info.site)])
    fields = ['name', 'latitude', 'longitude', 'driver', 'maxstations', 'maxcurrent',
            'delay', 'make', 'model', 'installed', 'notes']
    getSpecial(db, fields, sFields, 'SELECT * FROM controller ORDER BY name;',
            'controller information', 'controller')

def getSensor(db, info):
    sFields = OrderedDict([('controller', info.ctl), ('devtype', info.list)])
    fields = ['name', 'latitude', 'longitude', 'passivecurrent', 'activecurrent',
            'driver', 'addr', 'wirepath', 'make', 'model', 'installed', 'notes']
    getSpecial(db, fields, sFields, 'SELECT * FROM sensor ORDER BY addr;',
            'sensor information', 'sensor')
            
def getPOC(db, info):
    sFields = OrderedDict([('site', info.site)])
    fields = ['name', 'targetflow', 'maxflow', 'delayon', 'delayoff']
    getSpecial(db, fields, sFields, 'SELECT * FROM poc ORDER BY name;',
            'point-of-connect information', 'poc')

def getPOCFlow(db, info):
    sFields = OrderedDict([('poc', info.poc), ('sensor', info.sensor)])
    fields = ['name', 'make', 'model', 'tohertz', 'k', 'flowoffset']
    getSpecial(db, fields, sFields, 'SELECT * FROM pocFlow ORDER BY name;',
            'point-of-connect flow information', 'pocFlow')

def getPOCMV(db, info):
    sFields = OrderedDict([('poc', info.poc), ('sensor', info.sensor)])
    fields = ['name', 'make', 'model', 'qnormallyopen']
    getSpecial(db, fields, sFields, 'SELECT * FROM pocMV ORDER BY name;',
            'point-of-connect master valve information', 'pocMV')

def getPOCPump(db, info):
    sFields = OrderedDict([('poc', info.poc), ('sensor', info.sensor)])
    fields = ['name', 'make', 'model', 'minflow', 'maxflow', 'delayon', 'delayoff', 'priority']
    getSpecial(db, fields, sFields, 'SELECT * FROM pocPump ORDER BY name;',
            'point-of-connect booster pump information', 'pocPump')

def getStation(db, info):
    sFields = OrderedDict([('poc', info.poc), ('sensor', info.sensor)])
    fields = ['name', 'make', 'model', 'sortorder', 'mincycletime', 'maxcycletime', 
            'soaktime', 'maxcostations', 'measuredflow', 'userflow',
            'lowflowfrac', 'highflowfrac',
            'flowdelayon', 'flowdelayoff']
    getSpecial(db, fields, sFields, 'SELECT * FROM station ORDER BY name;',
            'station information', 'station')

def getProgram(db, info):
    sFields = OrderedDict([('site', info.site), ('onoff', info.list),
        ('action', info.list), ('startmode', info.list), ('stopmode', info.list)])
    fields = ['name', 'priority', 'qhide', 'ndays', 'refdate', 
            'starttime', 'endtime', 'attractorfrac', 'maxstations',
            'etthreshold']
    getSpecial(db, fields, sFields, 'SELECT * FROM program ORDER BY name;',
            'program information', 'program')

def getProgramDOW(db, info):
    sFields = OrderedDict([('program', info.program), ('dow', info.list)])
    getSpecial(db, [], sFields, 'SELECT * FROM pgmDOW ORDER BY program,dow;',
            'program/day-of-week information', 'pgmDOW')

def getProgramStation(db, info):
    sFields = OrderedDict([('program', info.program), ('station', info.station), 
        ('mode', info.list)])
    fields = ['runtime', 'priority', 'qsingle']
    getSpecial(db, fields, sFields, 'SELECT * FROM pgmStn ORDER BY program,station;',
            'program/station information', 'pgmStn')

def getEvent(db, info):
    sFields = OrderedDict([('site', info.site), ('onoff', info.list),
        ('action', info.list), ('startmode', info.list), ('stopmode', info.list)])
    fields = ['name', 'ndays', 'refdate', 'starttime', 'endtime', 'nrepeat', 'notes']
    getSpecial(db, fields, sFields, 'SELECT * FROM event ORDER BY name;',
            'event information', 'event')

def getEventDOW(db, info):
    sFields = OrderedDict([('event', info.event), ('dow', info.list)])
    getSpecial(db, [], sFields, 'SELECT * FROM eventDOW ORDER BY event,dow;',
            'event/day-of-week information', 'eventDOW')

def getETStation(db, info):
    sFields = OrderedDict([('station', info.station), ('crop', info.crop), ('soil', info.soil)])
    fields = ['sdate', 'edate', 'userrootnorm', 'userinfiltrationrate', 'usermad',
              'preciprate', 'uniformity', 'fracrain', 'fracsun', 'slope', 'slopelocation',
              'depletion', 'cycletime', 'soaktime', 'fracadjust']
    getSpecial(db, fields, sFields, 'SELECT * FROM ETStation ORDER BY station;',
            'ET/station information', 'ETStation')

def getGroup(db, info):
    sFields = OrderedDict([('site', info.site)])
    fields = ['name']
    getSpecial(db, fields, sFields, 'SELECT * FROM groups ORDER BY name;',
            'group information', 'groups')

def getGroupStation(db, info):
    sFields = OrderedDict([('groups', info.group), ('station', info.station)])
    fields = ['sortorder']
    getSpecial(db, fields, sFields, 'SELECT * FROM groupStation ORDER BY groups,station;',
            'group/station information', 'groupStation')

def getAction(db, info):
    sFields = OrderedDict([('sensor', info.sensor), ('program', info.program),
        ('pgmstn', info.pgmStn)])
    fields = ['cmd', 'ton', 'toff', 'pgmdate']
    getSpecial(db, fields, sFields, 'SELECT * FROM action ORDER BY tOn,sensor;',
            'Action information', 'acction')

def logBasic(db, info, tbl, fields=['timestamp', 'value'], sFields = None):
    if sFields is None:
        sFields = [('controller', info.ctl)]
    sFields = OrderedDict(sFields)
    getSpecial(db, fields, sFields, 'SELECT * FROM ' + tbl + ' ORDER BY timestamp;',
            tbl + " message log", tbl)

parser = argparse.ArgumentParser()
parser.add_argument('--db', help='database name', required=True)
args = parser.parse_args()

with psycopg2.connect(dbname=args.db) as db:
    info = Info(db)
    print('-- Generated', datetime.datetime.now())
    getSoil(db)
    getCrop(db)
    getUser(db)
    getEMail(db, info)
    getEMailReports(db, info)
    getSite(db)
    getController(db, info)
    getSensor(db, info)
    getPOC(db, info)
    getPOCFlow(db, info)
    getPOCMV(db, info)
    getPOCPump(db, info)
    getStation(db, info)
    getProgram(db, info)
    getProgramDOW(db, info)
    getProgramStation(db, info)
    getEvent(db, info)
    getEventDOW(db, info)
    getETStation(db, info)
    getGroup(db, info)
    getGroupStation(db, info)

    getAction(db, info)
    logBasic(db, info, 'onLog', ['timestamp', 'code', 'pre', 'peak', 'post'],
             [('sensor', info.sensor)])
    logBasic(db, info, 'offLog', ['timestamp', 'code'], [('sensor', info.sensor)])

    # logBasic(db, info, 'zeeLog')
    # logBasic(db, info, 'numberLog')
    # logBasic(db, info, 'versionLog')
    # logBasic(db, info, 'errorLog')
    # logBasic(db, info, 'twoLog', ['timestamp', 'addr', 'value'])
    # logBasic(db, info, 'peeLog', ['timestamp', 'addr', 'value'])
    # logBasic(db, info, 'teeLog', ['timestamp', 'code', 'pre', 'peak', 'post'],
            # [('sensor', info.sensor)])
    # logBasic(db, info, 'sensorLog', ['timestamp', 'value'],
            # [('pocflow', info.pocFlow)])
    # logBasic(db, info, 'currentLog', ['timestamp', 'volts', 'mAmps'])
