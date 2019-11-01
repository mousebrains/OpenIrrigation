#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../../Makefile.params

SRC = status.js index.js reportDaily.js 
SRC+= smonitor.js
DEST = $(SRC:%=$(JSDIR)/%)

.PHONY: all install clean

all:

install: 
	$(INSTALL) --target-directory=$(JSDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(JSDIR)

clean:
	$(RM) $(DEST)
