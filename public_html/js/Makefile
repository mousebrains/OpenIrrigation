#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../../Makefile.params

SRC = status.js
DEST = $(SRC:%=$(JSDIR)/%)

.PHONY: install clean

install: 
	$(INSTALL) --target-directory=$(JSDIR) $(SRC)

clean:
	$(RM) $(DEST)
