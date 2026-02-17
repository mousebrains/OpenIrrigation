#
# Shared scheduler utilities
#
# Extracted from SchedMain to break the circular import:
#   SchedAction -> SchedMain -> SchedTimeline -> SchedAction
#

import datetime

def prettyTimes(tOn:datetime.datetime, tOff:datetime.datetime) -> tuple:
    dateStr = "%Y-%m-%d "
    timeStr = "%H:%M:%S"
    sOn = tOn.strftime(dateStr + timeStr + ("" if tOn.microsecond == 0 else ".%f"))
    sOff= tOff.strftime(
            ("" if tOn.date() == tOff.date() else dateStr) +
            timeStr +
            ("" if tOff.microsecond == 0 else ".%f"))
    return (sOn, sOff)
