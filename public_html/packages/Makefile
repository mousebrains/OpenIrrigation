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
	$(INSTALL) --mode=0444 chart.umd.min.js $(JSDIR)/chart.umd.min.js
	$(INSTALL) --mode=0444 chartjs-adapter-date-fns.bundle.min.js $(JSDIR)/chartjs-adapter-date-fns.bundle.min.js
	chown -R $(USER):$(GROUP) $(JSDIR)

clean:
	$(RM) $(JSDIR)/jquery.min.*
	$(RM) $(JSDIR)/chart.umd.min.js $(JSDIR)/chartjs-adapter-date-fns.bundle.min.js
	$(RM) $(JSDIR)/Chart.min.js $(JSDIR)/moment.min.js $(JSDIR)/jquery.tablesorter.min.js
