#
# Cumulative runtime tracking per program-station and program date
#
# Extracted from SchedTimeline.py
#
# Oct-2019, Pat Welch
#

import datetime


class CumTime:
    """ Cumulative runtime per programstation and program date """
    def __init__(self) -> None:
        self.cumTime = {}

    def __repr__(self) -> str:
        msg = ['Cumulative Time']
        for stn in sorted(self.cumTime):
            for d in sorted(self.cumTime[stn]):
                msg.append("{}:{}={}".format(stn, d, self.cumTime[stn][d]))
        return "\n".join(msg)

    def get(self, pgmstn:int, pgmDate:datetime.date) -> datetime.timedelta:
        if pgmstn is None: return datetime.timedelta(seconds = 0)
        if pgmstn not in self.cumTime: return datetime.timedelta(seconds = 0)
        if pgmDate not in self.cumTime[pgmstn]: return datetime.timedelta(seconds = 0)
        return self.cumTime[pgmstn][pgmDate]

    def add(self, pgmstn:int, pgmDate:datetime.date, dt:datetime.timedelta) -> None:
        if pgmstn is None: return
        if pgmstn not in self.cumTime: self.cumTime[pgmstn] = {}
        dt = max(datetime.timedelta(seconds=0), dt)
        if pgmDate not in self.cumTime[pgmstn]:
            self.cumTime[pgmstn][pgmDate] = dt
        else:
            self.cumTime[pgmstn][pgmDate] += dt
