#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../Makefile.params

LIB = DB.py Params.py TDI.py TDISimulate.py Programs.py Events.py
BIN = TDIserver.py AgriMet.py scheduler.py notifier.py dumpDatabase.py

DEST = $(LIB:%=$(BINDIR)/%) $(BIN:%=$(BINDIR)/%)

.PHONY: all install clean

all:

install: 
	$(INSTALL) --target-directory=$(BINDIR) --mode=0444 $(LIB)
	$(INSTALL) --target-directory=$(BINDIR) --mode=0555 $(BIN)
	chown -R $(USER):$(GROUP) $(BINDIR)

clean:
	$(RM) $(DEST)
