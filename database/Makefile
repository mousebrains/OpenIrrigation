#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../Makefile.params

SRC = commands.db params.db
DEST = $(SRC:%=$(DBDIR)/%)

PARAMS = params.web.sql params.schema.sql params.init.sql
PARAMS+= params.soil.sql params.crop.sql params.site.sql

.PHONY: install clean

install: $(SRC)
	$(INSTALL) --target-directory=$(DBDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(DBDIR)

clean:
	$(RM) $(SRC) $(DEST)

commands.db: commands.schema.sql
	sqlite3 $@ <$<

params.db: $(PARAMS)
	for i in $^; do echo $$i; sqlite3 $@ <$$i; done
