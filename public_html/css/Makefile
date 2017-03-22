#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../../Makefile.params

SRC = irrigation.css
DEST = $(SRC:%=$(CSSDIR)/%)

.PHONY: install clean

install: $(SRC)
	$(INSTALL) --target-directory=$(CSSDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(CSSDIR)

clean:
	$(RM) $(DEST)
