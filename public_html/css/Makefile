#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../../Makefile.params

SRC = irrigation.css table.css tooltip.css topnav.css
DEST = $(SRC:%=$(CSSDIR)/%)

.PHONY: all install clean

all:

install: $(SRC)
	$(INSTALL) --target-directory=$(CSSDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(CSSDIR)

clean:
	$(RM) $(DEST)
