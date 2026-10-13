"""Minimal site rows for the SQL tests: one POC (id 1, the filter scripts
assume it) with a flow sensor (pocFlow id 1), a lawn station with a clean
baseline and a garden drip station, and a program to run them."""

import datetime

UTC = datetime.timezone.utc


def mkSite(cur) -> dict:
    """Insert the rows; returns their ids. `cur` may be dict- or tuple-row."""
    def one(sql, args=()):
        cur.execute(sql, args)
        row = cur.fetchone()
        return row["id"] if isinstance(row, dict) else row[0]

    site = one("INSERT INTO site(name) VALUES('Test') RETURNING id;")
    ctl = one("INSERT INTO controller(site,name) VALUES(%s,'TDI') RETURNING id;", (site,))
    poc = one("INSERT INTO poc(id,site,name) VALUES(1,%s,'Outside') RETURNING id;", (site,))
    flowSensor = one("INSERT INTO sensor(controller,name,addr) VALUES(%s,'Flow',0) RETURNING id;", (ctl,))
    pocFlow = one("INSERT INTO pocFlow(id,poc,sensor,name) VALUES(1,%s,%s,'Outside') RETURNING id;",
                  (poc, flowSensor))
    lawnSensor = one("INSERT INTO sensor(controller,name,addr) VALUES(%s,'Lawn',1) RETURNING id;", (ctl,))
    dripSensor = one("INSERT INTO sensor(controller,name,addr) VALUES(%s,'Drip',2) RETURNING id;", (ctl,))
    lawn = one("INSERT INTO station(poc,sensor,name,maxCoStations,cleanFlow,qFilterSensor)"
               " VALUES(%s,%s,'Cesped A',1,12.62,TRUE) RETURNING id;", (poc, lawnSensor))
    drip = one("INSERT INTO station(poc,sensor,name,userFlow)"
               " VALUES(%s,%s,'Huerto',1.2) RETURNING id;", (poc, dripSensor))
    program = one("INSERT INTO program(site,name,label) VALUES(%s,'Nightly','Night') RETURNING id;",
                  (site,))
    return dict(site=site, controller=ctl, poc=poc, pocFlow=pocFlow, lawnSensor=lawnSensor,
                dripSensor=dripSensor, lawn=lawn, drip=drip, program=program)


def historical(cur, ids, sensor, tOn, minutes):
    cur.execute("INSERT INTO historical(sensor,tOn,tOff,program,pgmDate,onCode,offCode)"
                " VALUES(%s,%s,%s,%s,%s,0,0);",
                (sensor, tOn, tOn + datetime.timedelta(minutes=minutes), ids["program"], tOn.date()))


def action(cur, ids, sensor, tOn, minutes, on):
    """A scheduled run; `on` means its valve has opened (onCode set)."""
    cur.execute("INSERT INTO action(sensor,addr,controller,cmd,tOn,tOff,program,pgmDate,onCode)"
                " VALUES(%s,0,%s,0,%s,%s,%s,%s,%s);",
                (sensor, ids["controller"], tOn, tOn + datetime.timedelta(minutes=minutes),
                 ids["program"], tOn.date(), 0 if on else None))


def reading(cur, ids, t, flow):
    cur.execute("INSERT INTO sensorLog(pocFlow,timestamp,value,flow) VALUES(%s,%s,%s,%s);",
                (ids["pocFlow"], t, round(flow * 10), flow))
