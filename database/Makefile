#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../Makefile.params

SRC = commands.db params.db ET.db
DEST = $(SRC:%=$(DBDIR)/%)

PARAMS = params.web.sql params.schema.sql params.init.sql
PARAMS+= params.soil.sql params.crop.sql params.site.sql

ET = params.web.sql ET.schema.sql ET.codes.sql

.PHONY: all extract install clean

all: $(SRC)

install: $(SRC)
	$(INSTALL) --target-directory=$(DBDIR) $(SRC)
	chown -R $(USER):$(GROUP) $(DBDIR)

clean:
	$(RM) $(SRC) $(DEST)

commands.db: commands.schema.sql $(DBDIR)/commands.db extractCmd.py FetchTable.py
	sqlite3 $@ <$<
	echo Extra Commands
	./extractCmd.py $(DBDIR)/commands.db | sqlite3 $@

params.db: $(PARAMS) $(DBDIR)/params.db extractPar.py FetchTable.py
	for i in $(PARAMS); do echo $$i; sqlite3 $@ <$$i; done
	echo Extra Params
	./extractPar.py $(DBDIR)/params.db | sqlite3 $@

ET.db: $(ET)
	for i in $^; do echo $$i; sqlite3 $@ <$$i; done
