# Message classes for talking to Tucor TDI 2-wire controller

from TDIbase import Base
import logging
import queue
import serial

def mkList(items:list) -> list: 
    """ Convert a single item into a list """
    return items if isinstance(items, list) else [items]

class Error(Base): 
    """ Get errors 0E -> 1EXX """
    def __init__(self, params:dict, logger:logging.Logger, qExcept:queue.Queue, 
            serial:serial.Serial, qReply:queue.Queue):
        Base.__init__(self, logger, qExcept, serial, qReply, 'ERR', params['errorPeriod'],
                '0E', None, (1,), params['errorSQL'], params['zeeSQL'])

class Current(Base):
    """ Get current 0U -> 1UXXXXYYYY """
    def __init__(self, params:dict, logger:logging.Logger, qExcept:queue.Queue, 
            serial:serial.Serial, qReply:queue.Queue):
        Base.__init__(self, logger, qExcept, serial, qReply, 'Current', params['currentPeriod'],
                '0U', None, (2,2), params['currentSQL'], params['zeeSQL'])


class Pee(Base):
    """ 0PXXYY -> 12XXZZZZ (Path?) 
        I don't know how this is different than 02 
    """
    def __init__(self, params:dict, logger:logging.Logger, qExcept:queue.Queue, 
            serial:serial.Serial, qReply:queue.Queue):
        Base.__init__(self, logger, qExcept, serial, qReply, 'Pee', params['peePeriod'],
                '0P', (1,1), (1,2), params['peeSQL'], params['zeeSQL'])
        self.previous = {}
        for channel in mkList(params['peeChannels']):
            self.addArgs((channel, 0xff))
            self.previous[channel] = None

    def procReply(self, t:float, reply:str, args:list) -> None:
        (channel, val) = args
        if (channel not in self.previous) or (self.previous[channel] != val): # different reading
            self.previous[channel] = val
            self.logger.debug('Fresh reading t=%s %s %s', t, reply, args)
            self.dbOut.put(self.msgHandler.sql, t, [channel, val])
        else:
            self.logger.debug('Dropped reading t=%s %s %s', t, reply, args)

class Pound(Base): 
    """ 0#XX -> 1#XX 
        Number of stations in controller
    """
    def __init__(self, params:dict, logger:logging.Logger, qExcept:queue.Queue, 
            serial:serial.Serial, qReply:queue.Queue):
        Base.__init__(self, logger, qExcept, serial, qReply, 'Pound', params['numberPeriod'],
                '0#', (1,), (1,), params['numberSQL'], params['zeeSQL'])
        self.addArgs((params['numberStations'], ))

class Sensor(Base):
    """ 0SXX -> 1SXXYYZZZZ """
    def __init__(self, params:dict, logger:logging.Logger, qExcept:queue.Queue, 
            serial:serial.Serial, qReply:queue.Queue):
        Base.__init__(self, logger, qExcept, serial, qReply, 'Sensor', params['sensorPeriod'],
                '0S', (1,), (1,1,2), params['sensorSQL'], params['zeeSQL'])
        self.previous = {}
        for channel in mkList(params['sensorChannels']):
            self.addArgs((channel,))
            self.previous[channel] = None

    def procReply(self, t:float, reply:str, args:list) -> None:
        (channel, flag, val) = args
        if (flag == 4) and ((channel not in self.previous) or (self.previous[channel] != val)):
            # fresh and different reading
            self.previous[channel] = val
            self.logger.debug('Fresh reading t=%s %s %s', t, reply, args)
            self.dbOut.put(self.msgHandler.sql, t, [channel, val])
        else:
            self.logger.debug('Dropped reading t=%s %s %s', t, reply, args)

class Two(Base): # 02XXYY -> 12XXZZ
    def __init__(self, params:dict, logger:logging.Logger, qExcept:queue.Queue, 
            serial:serial.Serial, qReply:queue.Queue):
        Base.__init__(self, logger, qExcept, serial, qReply, 'Two', params['twoPeriod'],
                '02', (1,1), (1,1), params['twoSQL'], params['zeeSQL'])
        self.previous = {}
        for channel in mkList(params['twoChannels']):
            self.addArgs((channel, 0xff))
            self.previous[channel] = None

    def procReply(self, t:float, reply:str, args:list) -> None:
        (channel, val) = args
        if (channel not in self.previous) or (self.previous[channel] != val): # different reading
            self.previous[channel] = val
            self.logger.debug('Fresh reading t=%s %s %s', t, reply, args)
            self.dbOut.put(self.msgHandler.sql, t, [channel, val])
        else:
            self.logger.debug('Dropped reading t=%s %s %s', t, reply, args)

class Version(Base): # 0V -> 1EZ...Z
    def __init__(self, params:dict, logger:logging.Logger, qExcept:queue.Queue, 
            serial:serial.Serial, qReply:queue.Queue):
        Base.__init__(self, logger, qExcept, serial, qReply, 'Version', params['versionPeriod'],
                '0V', None, None, params['versionSQL'], params['zeeSQL'])
        self.msgHandler.qString = True # A string argument
