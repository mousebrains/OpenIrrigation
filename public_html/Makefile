#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../Makefile.params

.PHONY: install clean

SRC = index.php status.php site.php user.php email.php
SRC += monitor.php smonitor.php running.php
SRC+= controller.php sensor.php
SRC+= poc.php pocFlow.php pocMV.php pocPump.php
SRC+= soil.php crop.php
SRC+= station.php program.php event.php programStation.php
SRC+= params.php
SRC+= ET.php ETannual.php ETStn.php

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
