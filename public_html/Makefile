#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../Makefile.params

SRC = favicon.png
SRC+= index.php indexProcess.php indexStatus.php
SRC+= status.php 
SRC+= reportDaily.php reportDailyStatus.php
SRC+= monitor.php monitorStatus.php
SRC+= monitorActiveOff.php monitorPendingRemove.php monitorProcAction.php
SRC+= site.php user.php email.php
SRC+= controller.php sensor.php
SRC+= poc.php pocFlow.php pocMV.php pocPump.php
SRC+= soil.php crop.php
SRC+= station.php program.php event.php programStation.php
SRC+= params.php webList.php
SRC+= ET.php ETannual.php ETStn.php

DEST = $(SRC:%=$(WEBDIR)/%)

.PHONY: all install clean

all:

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
