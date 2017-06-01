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

commands.db: commands.schema.sql
	sqlite3 $@ <$<
	echo Extra Commands
	./extractCmd.py $(DBDIR)/commands.db | sqlite3 $@

params.db: $(PARAMS)
	for i in $^; do echo $$i; sqlite3 $@ <$$i; done
	echo Extra Params
	./extractPar.py $(DBDIR)/commands.db | sqlite3 $@

ET.db: $(ET)
	for i in $^; do echo $$i; sqlite3 $@ <$$i; done
