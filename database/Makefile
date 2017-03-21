#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../Makefile.params

SRC = commands.db params.db
DEST = $(SRC:%=$(DBDIR)/%)

.PHONY: install clean

install: $(SRC)
	$(INSTALL) --target-directory=$(DBDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(DBDIR)

clean:
	$(RM) $(SRC) $(DEST)

commands.db: commands.schema
	sqlite3 $@ <$<

params.db: params.schema params.init params.soil params.crop params.site
	for i in $^; do sqlite3 $@ <$$i; done
