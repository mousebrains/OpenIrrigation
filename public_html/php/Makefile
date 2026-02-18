#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../../Makefile.params

SRC= DB1.php
SRC+= config.php
SRC+= navBar.php
SRC+= version.php

DEST = $(SRC:%=$(PHPDIR)/%)

.PHONY: all install clean php_lint

all: $(SRC)

config.php: config.php.in ../../Makefile.params
	sed -e 's?__DBNAME__?$(DBNAME)?g' <$< >$@

install: $(SRC)
	$(INSTALL) --mode=0644 --target-directory=$(PHPDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(PHPDIR)

clean:
	$(RM) config.php $(PRE:%.pre=%) $(DEST)

php_lint:
	@fail=0; for f in $(SRC); do php -l $$f || fail=1; done; exit $$fail
