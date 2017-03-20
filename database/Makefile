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

$(DBDIR)/%.db: %.schema %.init
	$(INSTALL) --directory $(@D)
	cat $^ | sqlite3 $@ < /dev/null
	chown -R $(user):$(group) $(@D)
