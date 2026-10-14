#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../../Makefile.params

JQVERSION = 4.0.0
LEAFLET = leaflet-1.9.4

.PHONY: all install uninstall clean

all:

install:
	$(INSTALL) --mode=0444 jquery-$(JQVERSION).min.js $(JSDIR)/jquery.min.js
	$(INSTALL) --mode=0444 jquery-$(JQVERSION).min.map $(JSDIR)/jquery.min.map
	$(INSTALL) --mode=0444 chart.umd.min.js $(JSDIR)/chart.umd.min.js
	$(INSTALL) --mode=0444 chartjs-adapter-date-fns.bundle.min.js $(JSDIR)/chartjs-adapter-date-fns.bundle.min.js
	$(INSTALL) --mode=0444 $(LEAFLET)/leaflet.js $(JSDIR)/leaflet.js
	chown -R $(USER):$(GROUP) $(JSDIR)
	@# leaflet.css finds its images in images/ beside it
	$(INSTALL) --mode=0444 $(LEAFLET)/leaflet.css $(CSSDIR)/leaflet.css
	$(INSTALL) --mode=0444 --target-directory=$(CSSDIR)/images $(LEAFLET)/images/*.png
	chown -R $(USER):$(GROUP) $(CSSDIR)

clean:

uninstall:
	$(RM) $(JSDIR)/jquery.min.*
	$(RM) $(JSDIR)/chart.umd.min.js $(JSDIR)/chartjs-adapter-date-fns.bundle.min.js
	$(RM) $(JSDIR)/Chart.min.js $(JSDIR)/moment.min.js $(JSDIR)/jquery.tablesorter.min.js
	$(RM) $(JSDIR)/leaflet.js $(CSSDIR)/leaflet.css
	$(RM) $(addprefix $(CSSDIR)/images/,$(notdir $(wildcard $(LEAFLET)/images/*.png)))
