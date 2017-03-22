#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../Makefile.params

.PHONY: install clean

SRC = index.php status.php site.php user.php userEMail.php
DEST = $(SRC:%=$(WEBDIR)/%)

install:: 
	$(INSTALL) --target-directory=$(WEBDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(WEBDIR)

clean::
	$(RM) $(DEST)

install clean::
	$(MAKE) -C js $@
	$(MAKE) -C css $@
	$(MAKE) -C php $@
