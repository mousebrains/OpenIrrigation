#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../Makefile.params

LIB = DB.py Params.py TDI.py
BIN = TDIserver.py

DEST = $(LIB:%=$(BINDIR)/%) $(BIN:%=$(BINDIR)/%)

.PHONY: install clean

install: 
	$(INSTALL) --target-directory=$(BINDIR) --mode=0444 $(LIB)
	$(INSTALL) --target-directory=$(BINDIR) --mode=0555 $(BIN)

clean:
	$(RM) $(DEST)
