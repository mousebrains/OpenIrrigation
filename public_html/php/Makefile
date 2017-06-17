#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../../Makefile.params

SRC = DB.php
SRC+= navBar.php
SRC+= mkPage.php

DEST = $(SRC:%=$(PHPDIR)/%)

.PHONY: all install clean

all: $(SRC)

install: $(SRC)
	$(INSTALL) --mode=0644 --target-directory=$(PHPDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(PHPDIR)

clean:
	$(RM) $(PRE:%.pre=%) $(DEST)
