#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../Makefile.params

SCHEMA = commands.schema params.schema
SRC = $(SCHEMA:%.schema=%.db)
DEST = $(SRC:%=$(DBDIR)/%)

.PHONY: install clean

install: $(DEST)

clean:
	$(RM) $(DEST)

$(DBDIR)/commands.db: commands.schema
	$(INSTALL) --directory $(@D)
	sqlite3 $@ <$<
	chown -R $(user):$(group) $(@D)

$(DBDIR)/params.db: params.schema params.init params.soil params.crop params.site
	$(INSTALL) --directory $(@D)
	for i in $^; do sqlite3 $@ <$$i; done
	chown -R $(user):$(group) $(@D)
