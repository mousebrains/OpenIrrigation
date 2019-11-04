#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../../Makefile.params

SRC = DB.php
SRC+= mkPage.php
SRC+= DB1.php
SRC+= navBar.php

DEST = $(SRC:%=$(PHPDIR)/%)

.PHONY: all install clean

all: $(SRC)

install: $(SRC)
	$(INSTALL) --mode=0644 --target-directory=$(PHPDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(PHPDIR)

clean:
	$(RM) $(PRE:%.pre=%) $(DEST)
