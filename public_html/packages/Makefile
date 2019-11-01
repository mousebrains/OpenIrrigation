#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../../Makefile.params

SRC = Chart.min.js moment.min.js jquery.tablesorter.min.js

JQVERSION = 3.4.1

.PHONY: all install clean

all:

install:
	$(INSTALL) --mode=0444 --target-directory $(JSDIR) $(SRC)
	$(INSTALL) --mode=0444 jquery-$(JQVERSION).min.js $(JSDIR)/jquery.min.js
	$(INSTALL) --mode=0444 jquery-$(JQVERSION).min.map $(JSDIR)/jquery.min.map
	chown -R $(USER):$(GROUP) $(JSDIR)

clean:
	$(RM) $(JSDIR)/jquery.min.*
