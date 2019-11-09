#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../../Makefile.params

SRC = irrigation.js # Utility functions
SRC+= status.js
SRC+= index.js
SRC+= reportDaily.js 
SRC+= monitor.js
SRC+= tableEditor.js
SRC+= processState.js

DEST = $(SRC:%=$(JSDIR)/%)

.PHONY: all install clean

all:

install: 
	$(INSTALL) --target-directory=$(JSDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(JSDIR)

clean:
	$(RM) $(DEST)
