#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../Makefile.params

LIB = DB.py MyBaseThread.py MyLogger.py Params.py 
LIB+= SchedMain.py SchedProgram.py SchedProgramStation.py SchedSensor.py
LIB+= SchedAction.py SchedEvent.py SchedUtils.py
LIB+= SchedTimeline.py
LIB+= TDI.py TDIbase.py TDIserial.py TDISimulate.py TDIvalve.py
LIB+= Notify.py
BIN = AgriMet.py dumpDatabase.py scheduler.py TDIserver.py 
BIN+= dailyReport.py

DEST = $(LIB:%=$(BINDIR)/%) $(BIN:%=$(BINDIR)/%)

.PHONY: all install clean

all:

install: 
	$(INSTALL) --target-directory=$(BINDIR) --mode=0444 $(LIB)
	$(INSTALL) --target-directory=$(BINDIR) --mode=0555 $(BIN)
	chown -R $(USER):$(GROUP) $(BINDIR)

clean:
	$(RM) $(DEST)
