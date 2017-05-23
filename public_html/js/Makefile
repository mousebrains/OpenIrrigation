#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../../Makefile.params

SRC = status.js running.js
DEST = $(SRC:%=$(JSDIR)/%)

.PHONY: install clean

install: 
	$(INSTALL) --target-directory=$(JSDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(JSDIR)

clean:
	$(RM) $(DEST)
