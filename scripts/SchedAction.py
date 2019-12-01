#
# This class defines an action, on+off event
#
# Oct-2019, Pat Welch
#

import datetime
from SchedSensor import Sensor
from SchedProgramStation import ProgramStation

class Action:
    """ An action object which is used in the Timeline class """
    def __init__(self, tOn:datetime.datetime, tOff:datetime.datetime, pgm:int, pgmStn:int,
            pgmDate:datetime.date, sensor:Sensor, stn:ProgramStation) -> None:
        self.tOn = tOn
        self.tOff = tOff
        self.pgm = pgm
        self.pgmStn = pgmStn
        self.pgmDate = pgmDate
        self.sensor = sensor
        self.stn = stn

    def __repr__(self) -> str:
        msg = 'Action({})'.format(self.sensor.name)
        msg+= ' tOn={} tOff={}'.format(self.tOn.isoformat(), self.tOff.isoformat())
        msg+= ' pgm={} pgmDate={}'.format(self.pgm, self.pgmDate)
        msg+= ' sensor={} stn={}'.format(self.sensor.id, self.stn.id)
        return msg
