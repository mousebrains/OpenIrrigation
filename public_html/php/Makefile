#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../../Makefile.params

PRE = CmdDB.php.pre ParDB.php.pre

SRC = $(PRE:%.pre=%) 
SRC+= MyDB.php statusBlock.php navBar.php
SRC+= webForm.php

DEST = $(SRC:%=$(PHPDIR)/%)

.PHONY: install clean

install: $(SRC)
	$(INSTALL) --mode=0644 --target-directory=$(PHPDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(PHPDIR)

clean:
	$(RM) $(PRE:%.pre=%) $(DEST)

%.php: %.php.pre
	sed -e 's?__DBDIR__?$(DBDIR)?g' <$< >$@
