#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../../Makefile.params

SRC = Chart.min.js moment.min.js

.PHONY: install clean

install:
	$(INSTALL) --mode=0444 --target-directory $(JSDIR) $(SRC)
	$(INSTALL) --mode=0444 jquery-3.2.0.min.js $(JSDIR)/jquery.min.js
	$(INSTALL) --mode=0444 jquery-3.2.0.min.map $(JSDIR)/jquery.min.map
	chown -R $(USER):$(GROUP) $(JSDIR)

clean:
	$(RM) $(JSDIR)/jquery.min.*
