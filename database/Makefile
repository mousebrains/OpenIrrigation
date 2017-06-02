#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../Makefile.params

CMDDB = commands.db

PARAMS = params.web.sql params.schema.sql params.init.sql
PARAMS+= params.soil.sql params.crop.sql params.site.sql
PARAMSDB = params.db

ETDB = ET.db

SRC = $(CMDDB) $(PARAMSDB) $(ETDB)
DEST = $(SRC:%=$(DBDIR)/%)

.PHONY: all extract install clean

all: $(SRC)

install: $(DEST)
	chown -R $(USER):$(GROUP) $(DBDIR)

clean:
	$(RM) $(SRC) $(DEST)

$(DBDIR)/$(CMDDB): $(CMDDB) extractCmd.py FetchTable.py
	./extractCmd.py $@ $<
	$(INSTALL) --target-directory=$(DBDIR) $<

$(CMDDB): commands.schema.sql
	sqlite3 $@ <$<

$(DBDIR)/$(PARAMSDB): $(PARAMSDB) extractPar.py FetchTable.py
	./extractPar.py $@ $<
	$(INSTALL) --target-directory=$(DBDIR) $<

$(PARAMSDB): $(PARAMS)
	for i in $(PARAMS); do echo $$i; sqlite3 $@ <$$i; done

$(DBDIR)/$(ETDB): $(ETDB)
	$(INSTALL) --target-directory=$(DBDIR) $<

$(ETDB): params.web.sql ET.schema.sql ET.codes.sql
	for i in $^; do echo $$i; sqlite3 $@ <$$i; done
