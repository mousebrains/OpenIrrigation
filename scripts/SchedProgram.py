#
# List of priority ordered active program objects
#
# Oct-2019, Pat Welch, pat@mousebrains

import psycopg
import logging
import datetime
from zoneinfo import ZoneInfo
from astral import Observer
from astral.sun import sun as astral_sun
from SchedProgramStation import ProgramStations

class Programs(list):
    """ Collection of active program objects in priority order """
    def __init__(self, cur:psycopg.Cursor, stations: ProgramStations,
            logger:logging.Logger) -> None:
        """ Grab all the active programs from the database  """

        # First grab the day-of-week to program association
        sql = "SELECT program,key FROM pgmDOW INNER JOIN webList ON dow=id;"
        cur.execute(sql)
        pgm2dow = {}
        for row in cur:
            (pgm, dow) = row
            if pgm not in pgm2dow: pgm2dow[pgm] = []
            pgm2dow[pgm].append(dow)

        sql = "SELECT"
        sql+= " program.id,program.name"
        sql+= ",(SELECT key FROM webList WHERE id=program.action)"
        sql+= ",program.nDays,program.refDate,program.startTime,program.endTime"
        sql+= ",(SELECT key FROM webList WHERE id=program.startMode)"
        sql+= ",(SELECT key FROM webList WHERE id=program.stopMode)"
        sql+= ",program.qBackward,program.maxStations,program.maxFlow"
        sql+= ",site.timezone,site.elevation,site.latitude,site.longitude"
        sql+= " FROM program"
        sql+= " INNER JOIN site ON site.id=program.site"
        sql+= " WHERE (SELECT key FROM webList where id=onOff)='on'"
        sql+= " ORDER BY PRIORITY"
        sql+= ";"

        cur.execute(sql)
        for row in cur:
            ident = row[0]
            if ident not in stations.pgm2stn: continue # No need to keep
            self.append(Program(row,
                pgm2dow[ident] if ident in pgm2dow else None,
                stations.pgm2stn[ident]))

    def __repr__(self) -> str:
        msg = "Programs"
        for item in self:
            msg += '\nProgram: ' + str(item)
        return msg

class Program:
    """ Information about a Program """
    def __init__(self, row:list, dows:list, stations:list) -> None:
        site = {}
        (self.id, self.name
                , action
                , nDays, refDate, startTime, stopTime
                , startMode, stopMode
                , self.qBackward, self.maxStations, self.maxFlow
                , site['tz'], site['elev'], site['lat'], site['lon']
                ) = row
        self.start = PgmDateTime(action, nDays, refDate, dows, startTime, startMode, site)
        self.stop  = PgmDateTime(action, nDays, refDate, dows, stopTime,  stopMode,site)
        self.stations = stations

    def __repr__(self) -> str:
        msg = 'id={} name={}'.format(self.id, self.name)
        msg+= ' qBackward={}'.format(self.qBackward)
        msg+= ' maxStn={} maxFlow={}'.format(self.maxStations, self.maxFlow)
        msg+= ' start={} stop={}'.format(self.start, self.stop)
        msg+= '\nProgram Stations:'
        for item in self.stations:
            msg += '\nStation: ' + str(item)
        return msg

    def mkTime(self, pgmDate:datetime.date) -> tuple:
        """ Return a start/stop time tuple or None if there is none for this pgmDate """
        stime = self.start.mkTime(pgmDate)
        if stime is None: return (None, None)
        etime = self.stop.mkTime(pgmDate)
        if etime is None: return (None, None)
        if etime <= stime: # etime before stime, so backup stime up by a day
            stime -= datetime.timedelta(days=1)
        return (stime, etime)

class PgmDateTime:
    """ Class to construct a date/time from a program date """
    def __init__(self, action:str, nDays:int, refDate:datetime.date, dows:list,
            t:datetime.time, mode:str, siteInfo:dict) -> None:
        self.time = self.__mkTime(mode, t, siteInfo)
        self.date = self.__mkDate(action, nDays, refDate, dows)

    def __repr__(self): return "date=" + str(self.date) + " time=" + str(self.time)

    def mkTime(self, pgmDate:datetime.date) -> datetime.datetime:
        d = self.date.mkDate(pgmDate)
        return None if d is None else self.time.mkTime(d)

    def __mkTime(self, mode:str, t:str, siteInfo:dict):
        """ Choose which time class to use """
        try:
            tzinfo = ZoneInfo(siteInfo['tz'])
        except KeyError:
            raise RuntimeError(
                    f"Timezone {siteInfo['tz']!r} not found."
                    " Install timezone data: pip install tzdata")
        if mode == 'clock': return TimeClock(t, tzinfo)
        return TimeAstral(mode, t, siteInfo, tzinfo)

    def __mkDate(self, action:str, nDays:int, refDate:datetime.date, dows:list):
        """ Choose which date close to use """
        if action == 'dow': return DateDOW(dows)
        if action == 'nDays': return DateDays(nDays, refDate)
        raise Exception('Unsupported date action={}'.format(action))

class DateDOW:
    """ Return a date if it is in the set of day-of-weeks """
    def __init__(self, dows):
        self.dows = set()
        if dows is None: return
        dow2num = {'mon': 0, 'tue': 1, 'wed': 2, 'thur': 3, 'fri': 4, 'sat': 5, 'sun': 6}
        for dow in dows:
            if dow in dow2num:
                self.dows.add(dow2num[dow])
            else:
                raise Exception('Unrecognized day of week {}'.format(dow))

    def __repr__(self):
        return 'dows=' + str(self.dows)

    def mkDate(self, d:datetime.date) -> datetime.date:
        return d if d.weekday() in self.dows else None

    def mkRefDate(self, d:datetime.date) -> datetime.date:
        return None

class DateDays:
    """ Return a date if it is n days from the ref date else None """
    def __init__(self, nDays:int, refDate:datetime.date):
        self.nDays = nDays
        self.ref = refDate

    def __repr__(self):
        return 'nDays={} ref={}'.format(self.nDays, self.ref.isoformat())

    def mkDate(self, d:datetime.date) -> datetime.date:
        dt = (d - self.ref).days # Days between d and ref
        return None if (dt % self.nDays) else d # If zero remainder then good

    def mkRefDate(self, d:datetime.date) -> datetime.date:
        dd = (d - self.ref).days # Days between
        return d + datetime.timedelta(days=dd + self.nDays - (dd % self.nDays))

class TimeClock:
    """ the time field is an actuall walk clock time """
    def __init__(self, t:datetime.time, tz:datetime.timezone) -> None:
        self.t = t.replace(tzinfo=tz)

    def __repr__(self):
        return "t=" + self.t.isoformat()

    def mkTime(self, pgmDate:datetime.date) -> datetime.datetime:
        return datetime.datetime.combine(pgmDate, self.t)

class TimeAstral:
    """ the time field is relative to the earth/sun position """
    def __init__(self, mode:str, t:datetime.time, site:dict, tz:datetime.timezone):
        self.mode = mode
        self.tz = tz
        self.dt = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        if t > datetime.time(12,0,0): # Times past noon encode a negative offset from the
            self.dt -= datetime.timedelta(days=1) # astral event, e.g. 23:30 → −30 minutes
        self.observer = Observer(latitude=site['lat'], longitude=site['lon'], elevation=site['elev'])

    def __repr__(self):
        return "mode={} dt={} observer={}".format(self.mode, self.dt, self.observer)

    def mkTime(self, pgmDate:datetime.date) -> datetime.datetime:
        sun = astral_sun(self.observer, date=pgmDate, tzinfo=self.tz)
        if self.mode not in sun:
            raise Exception('Mode, {}, is not an astral sun position'.format(self.mode))
        t = sun[self.mode] + self.dt
        return t.replace(tzinfo=self.tz)
