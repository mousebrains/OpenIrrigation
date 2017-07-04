import threading
import queue
import random
import serial
import psycopg2

# Make either a real or simulated serial style connection
def mkSerial(args, params, logger):
  with psycopg2.connect(dbname=args.db) as db, \
	db.cursor() as cur:
    cur.execute("INSERT INTO simulate(qSimulate) VALUES(%s);", [args.simul])
    db.commit()

  if not args.simul:
    return serial.Serial(port=params['port'], baudrate=params['baudrate'])
  s0 = Simulate(logger)
  s0.start()
  return s0

class Simulate(threading.Thread):
	def __init__(self, logger):
		threading.Thread.__init__(self, daemon=True)
		self.name='Simulate'
		self.logger = logger
		self.qIn = queue.Queue()
		self.qOut = queue.Queue()
		self.qOn = {}
		self.cmds = {'0E':self.cmdE, '0U':self.cmdU, '0S':self.cmdS, '02':self.cmd2,
			'0P': self.cmdP, '0A':self.cmdA, '0D': self.cmdD, '0T':self.cmdT,
			'0V': self.cmdV, '0#': self.cmdPound}

	def write(self, a): # serial interface
		self.qIn.put(a)

	def read(self, n=None): # serial interface
		a = self.qOut.get()
		self.qOut.task_done()
		return a

	def close(self): # serial interface
		pass

	def putter(self, msg): # Spit out single bytes
		sentence = '{:02X}{}'.format(len(msg), msg)
		chkSum = 0
		self.qOut.put(b'\x16') # Send sync
		for c in sentence:
			chkSum += ord(c)
			self.qOut.put(bytes(c, 'UTF-8'))
		chk = "{:02X}\r".format(chkSum & 255)
		self.qOut.put(bytes(chk[0], 'UTF-8'))
		self.qOut.put(bytes(chk[1], 'UTF-8'))
		self.qOut.put(b'\r')

	def run(self): # Called on thread start
		logger = self.logger
		qIn = self.qIn
		qOut = self.qOut
		put = self.putter
		cmds = self.cmds
		logger.info('Starting')
		while True:
			a = qIn.get()
			if a != b'\x06': # ACK
				msg = str(a[3:-2], 'UTF-8')
				cmd = msg[0:2]
				if cmd in cmds:
					cmds[cmd](msg)
					qOut.put(b'\x06') # Send ACK
				else:
					logger.error('Unrecognized sentence {}'.format(a))
					qOut.put(b'\x15') # Send NAK
					put("1Z0102")
			qIn.task_done()

	def cmdA(self, msg):
		addr = msg[2:4]
		self.qOn[addr] = 1
		pre = 28 + random.uniform(-1,1)
		peak = 650 + random.uniform(-10,10)
		post = 50 + random.uniform(-2,2)
		self.putter("1A{}00{:04X}{:04X}{:04X}".format(addr,
			int(pre), int(peak), int(post)))

	def cmdD(self, msg):
		addr = msg[2:4]
		code = 0 if addr in self.qOn else 2
		if addr == 'FF':
			code = 0 if len(self.qOn) else 2
			self.qOn = {}
		elif code == 0: # In the dictionary
			del self.qOn[addr]
		self.putter("1D{}{:02X}".format(addr, code))

	def cmdE(self, msg):
		self.putter('1E00')

	def cmdPound(self, msg):
		self.putter('1#{}'.format(msg[2:]))

	def cmdU(self, msg):
		n = len(self.qOn)
		volts = 34 - n * 0.05 + random.uniform(-0.07,0.07)
		mAmps = 25 + n * 25 + random.uniform(-1,1)
		self.putter("1U{:04X}{:04X}".format(int(volts * 10), int(mAmps)))

	def cmdS(self, msg):
		n = len(self.qOn)
		flow = n * (100 + random.uniform(-2,2)) # In Hertz*10
		self.putter("1S{}04{:04X}".format(msg[2:4], int(flow)))

	def cmd2(self, msg):
		self.putter('12{}'.format(msg[2:]))

	def cmdP(self, msg):
		self.putter('1P000A')

	def cmdV(self, msg):
		self.putter('1VSimul')

	def cmdT(self, msg):
		pre = 28 + random.uniform(-1,1)
		peak = 650 + random.uniform(-10,10)
		post = 50 + random.uniform(-2,2)
		self.putter("1T{}00{:04X}{:04X}{:04X}".format(msg[2:4],
			int(pre), int(peak), int(post)))
