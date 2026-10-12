#
# List of priority ordered active program objects
#
# Oct-2019, Pat Welch, pat@mousebrains

import psycopg
import logging
import datetime
from zoneinfo import ZoneInfo
from SchedProgramStation import ProgramStations
from SchedUtils import Problems, asInstant

# Start/stop modes which are relative to a sun position
ASTRAL_MODES = ('dawn', 'sunrise', 'noon', 'sunset', 'dusk')

class Programs(list):
    """ Collection of active program objects in priority order """
    def __init__(self, cur:psycopg.Cursor, stations: ProgramStations,
            logger:logging.Logger, problems:Problems | None = None) -> None:
        """ Grab all the active programs from the database  """
        if problems is None: problems = Problems(logger)

        # First grab the day-of-week to program association
        sql = "SELECT program,key FROM pgmDOW INNER JOIN webList ON dow=id;"
        cur.execute(sql)
        pgm2dow: dict[int, list[str]] = {}
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
        sql+= ",program.qBackward,program.qManual,program.maxStations,program.maxFlow"
        sql+= ",site.timezone,site.elevation,site.latitude,site.longitude"
        sql+= ",(SELECT key FROM webList WHERE id=program.onOff)"
        sql+= " FROM program"
        sql+= " INNER JOIN site ON site.id=program.site"
        sql+= " WHERE (SELECT key FROM webList where id=onOff) IN ('on','highET')"
        sql+= " ORDER BY program.priority,program.id" # id: a stable order for equal priorities
        sql+= ";"

        cur.execute(sql)
        for row in cur.fetchall():
            ident = row[0]
            name = row[1]
            onOff = row[-1]
            if onOff != 'on': # highET is accepted by the program editor but never implemented
                problems.warning(
                        "Program {} is in mode '{}', which the scheduler does not"
                        " implement; it is not scheduled".format(name, onOff))
                continue
            for stn in stations.etStations.get(ident, []):
                problems.warning(
                        "Station {} in program {} is in mode 'ET', which the scheduler"
                        " does not implement; it is not scheduled".format(stn, name))
            if ident not in stations.pgm2stn: continue # No need to keep
            try:
                self.append(Program(row[:-1],
                    pgm2dow[ident] if ident in pgm2dow else None,
                    stations.pgm2stn[ident]))
            except Exception as e: # One bad program must not stop the whole schedule
                problems.error('Program {} is not scheduled: {}'.format(name, e))

    def __repr__(self) -> str:
        msg = "Programs"
        for item in self:
            msg += '\nProgram: ' + str(item)
        return msg

class Program:
    """ Information about a Program """
    def __init__(self, row:list | tuple, dows:list | None, stations:list) -> None:
        site = {}
        (self.id, self.name
                , action
                , nDays, refDate, startTime, stopTime
                , startMode, stopMode
                , self.qBackward, self.qManual, self.maxStations, self.maxFlow
                , site['tz'], site['elev'], site['lat'], site['lon']
                ) = row
        self.start = PgmDateTime(action, nDays, refDate, dows, startTime, startMode, site, 'start')
        self.stop  = PgmDateTime(action, nDays, refDate, dows, stopTime,  stopMode, site, 'end')
        self.stations = stations

    def __repr__(self) -> str:
        msg = 'id={} name={}'.format(self.id, self.name)
        msg+= ' qBackward={} qManual={}'.format(self.qBackward, self.qManual)
        msg+= ' maxStn={} maxFlow={}'.format(self.maxStations, self.maxFlow)
        msg+= ' start={} stop={}'.format(self.start, self.stop)
        msg+= '\nProgram Stations:'
        for item in self.stations:
            msg += '\nStation: ' + str(item)
        return msg

    def mkTime(self, pgmDate:datetime.date) -> tuple:
        """ Return the (start, stop) window as UTC instants, or (None, None)
        if the program does not run on pgmDate

        Start and stop are wall-clock times in the site's zone.  When the stop
        is not after the start on the clock face, the window began the day
        before.  A wall time that does not exist (the spring-forward gap) or
        occurs twice (the fall-back fold) takes the UTC offset in force before
        the transition (PEP 495 fold=0): 02:30 on a spring-forward night is
        03:30 PDT and 01:30 on a fall-back night is the first, PDT, 01:30.
        """
        stime = self.start.mkTime(pgmDate)
        if stime is None: return (None, None)
        etime = self.stop.mkTime(pgmDate)
        if etime is None: return (None, None)
        if etime.replace(tzinfo=None) <= stime.replace(tzinfo=None):
            # etime before stime on the clock, so the window started the day before
            stime = self.start.time.mkTime(pgmDate - datetime.timedelta(days=1))
        return (asInstant(stime), asInstant(etime))

class PgmDateTime:
    """ Class to construct a date/time from a program date """
    def __init__(self, action:str, nDays:int, refDate:datetime.date, dows:list | None,
            t:datetime.time, mode:str, siteInfo:dict, which:str = 'start') -> None:
        if t is None: raise ValueError('no {} time'.format(which))
        self.time = self.__mkTime(mode, t, siteInfo, which)
        self.date = self.__mkDate(action, nDays, refDate, dows)

    def __repr__(self): return "date=" + str(self.date) + " time=" + str(self.time)

    def mkTime(self, pgmDate:datetime.date) -> datetime.datetime | None:
        d = self.date.mkDate(pgmDate)
        return None if d is None else self.time.mkTime(d)

    def __mkTime(self, mode:str, t:datetime.time, siteInfo:dict,
            which:str) -> 'TimeClock | TimeAstral':
        """ Choose which time class to use """
        if siteInfo['tz'] is None: raise ValueError('the site has no timezone')
        try:
            tzinfo = ZoneInfo(siteInfo['tz'])
        except KeyError as e:
            raise RuntimeError(
                    f"Timezone {siteInfo['tz']!r} not found."
                    " Install timezone data: pip install tzdata") from e
        if mode == 'clock': return TimeClock(t, tzinfo)
        if mode in ASTRAL_MODES: return TimeAstral(mode, t, siteInfo, tzinfo)
        raise ValueError('unsupported {} mode {!r}'.format(which, mode))

    def __mkDate(self, action:str, nDays:int, refDate:datetime.date,
            dows:list | None) -> 'DateDOW | DateDays':
        """ Choose which date close to use """
        if action == 'dow': return DateDOW(dows)
        if action == 'nDays': return DateDays(nDays, refDate)
        raise ValueError('unsupported date action={!r}'.format(action))

class DateDOW:
    """ Return a date if it is in the set of day-of-weeks """
    def __init__(self, dows: list | None):
        self.dows: set[int] = set()
        if dows is None: return
        dow2num = {'mon': 0, 'tue': 1, 'wed': 2, 'thur': 3, 'fri': 4, 'sat': 5, 'sun': 6}
        for dow in dows:
            if dow in dow2num:
                self.dows.add(dow2num[dow])
            else:
                raise Exception('Unrecognized day of week {}'.format(dow))

    def __repr__(self) -> str:
        return 'dows=' + str(self.dows)

    def mkDate(self, d:datetime.date) -> datetime.date | None:
        return d if d.weekday() in self.dows else None

class DateDays:
    """ Return a date if it is n days from the ref date else None """
    def __init__(self, nDays:int, refDate:datetime.date):
        if nDays is None:
            raise ValueError('nDays is not set')
        if nDays <= 0:
            raise ValueError('nDays must be positive, got {}'.format(nDays))
        if refDate is None:
            raise ValueError('refDate is not set')
        self.nDays = nDays
        self.ref = refDate

    def __repr__(self):
        return 'nDays={} ref={}'.format(self.nDays, self.ref.isoformat())

    def mkDate(self, d:datetime.date) -> datetime.date | None:
        dt = (d - self.ref).days # Days between d and ref
        return None if (dt % self.nDays) else d # If zero remainder then good

class TimeClock:
    """ the time field is an actuall walk clock time """
    def __init__(self, t:datetime.time, tz:datetime.tzinfo) -> None:
        self.t = t.replace(tzinfo=tz)

    def __repr__(self):
        return "t=" + self.t.isoformat()

    def mkTime(self, pgmDate:datetime.date) -> datetime.datetime:
        """ The wall-clock time on pgmDate in the site's zone (fold=0) """
        return datetime.datetime.combine(pgmDate, self.t)

class TimeAstral:
    """ the time field is relative to the earth/sun position """
    def __init__(self, mode:str, t:datetime.time, site:dict, tz:ZoneInfo):
        self.mode = mode
        self.tz = tz
        self.dt = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        if t > datetime.time(12,0,0): # Times past noon encode a negative offset from the
            self.dt -= datetime.timedelta(days=1) # astral event, e.g. 23:30 → −30 minutes
        if site['lat'] is None or site['lon'] is None:
            raise ValueError('{} mode needs the site latitude and longitude'.format(mode))
        from astral import Observer
        self.observer = Observer(latitude=site['lat'], longitude=site['lon'],
                elevation=site['elev'] or 0)

    def __repr__(self):
        return "mode={} dt={} observer={}".format(self.mode, self.dt, self.observer)

    def mkTime(self, pgmDate:datetime.date) -> datetime.datetime:
        """ The sun event on pgmDate plus the offset, in the site's zone

        The offset is real elapsed time, so it is added to the UTC instant;
        adding it to the local time would be off by an hour across a DST change.
        """
        from astral.sun import sun as astral_sun
        sun = astral_sun(self.observer, date=pgmDate, tzinfo=self.tz)
        if self.mode not in sun:
            raise Exception('Mode, {}, is not an astral sun position'.format(self.mode))
        return (asInstant(sun[self.mode]) + self.dt).astimezone(self.tz)
