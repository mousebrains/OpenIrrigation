#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../Makefile.params

.PHONY: install clean

SRC = index.php status.php
DEST = $(SRC:%=$(WEBDIR)/%)

install: 
	$(INSTALL) --target-directory=$(WEBDIR) $(SRC)
	$(MAKE) -C js $@

clean:
	$(RM) $(DEST)
	$(MAKE) -C js $@
