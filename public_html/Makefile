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
SRC+= monitorActiveOff.php monitorPendingRemove.php 
SRC+= monitorClearAll.php monitorAllOff.php monitorPocOff.php
SRC+= tableEditor.php tableStatus.php
SRC+= tableRowInsert.php tableRowDelete.php tableRowUpdate.php
SRC+= ET.php etDaily.php etAnnual.php
SRC+= systemctl.php

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
