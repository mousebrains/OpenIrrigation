#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#
user = irrigation
group = $(user)
userDir = /home/$(user)
dbDir = $(userDir)/database

INSTALL = install --compare --group=$(group) --owner=$(user) --backup -D

.PHONY: install 

install: $(dbDir)/commands.db $(dbDir)/params.db

clean:
	$(RM) $(dbDir)/commands.db
	$(RM) $(dbDir)/params.db

$(dbDir)/commands.db: commands.schema
	$(INSTALL) --directory $(@D)
	sqlite3 $@ < $<
	chown -R $(user):$(group) $@

$(dbDir)/params.db: params.schema
	$(INSTALL) --directory $(@D)
	sqlite3 $@ < $<
	chown -R $(user):$(group) $@
