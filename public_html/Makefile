#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../Makefile.params

.PHONY: install clean

SRC = index.php status.php site.php user.php email.php report.php
SRC+= controller.php sensor.php
SRC+= poc.php pocFlow.php pocMV.php pocPump.php
SRC+= soil.php crop.php
SRC+= station.php program.php event.php

DEST = $(SRC:%=$(WEBDIR)/%)

install:: 
	$(INSTALL) --target-directory=$(WEBDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(WEBDIR)

clean::
	$(RM) $(DEST)

install clean::
	$(MAKE) -C packages $@
	$(MAKE) -C js $@
	$(MAKE) -C css $@
	$(MAKE) -C php $@
