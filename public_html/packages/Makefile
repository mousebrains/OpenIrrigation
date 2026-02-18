#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../../Makefile.params

JQVERSION = 4.0.0

.PHONY: all install clean

all:

install:
	$(INSTALL) --mode=0444 jquery-$(JQVERSION).min.js $(JSDIR)/jquery.min.js
	$(INSTALL) --mode=0444 jquery-$(JQVERSION).min.map $(JSDIR)/jquery.min.map
	chown -R $(USER):$(GROUP) $(JSDIR)

clean:
	$(RM) $(JSDIR)/jquery.min.*
	$(RM) $(JSDIR)/Chart.min.js $(JSDIR)/moment.min.js $(JSDIR)/jquery.tablesorter.min.js
