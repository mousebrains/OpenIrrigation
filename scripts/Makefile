#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#
# Where to install the .service files
serviceDir = /etc/systemd/system

user = irrigation
group = $(user)
userDir = /home/$(user)
dbDir = $(userDir)/database
binDir = $(userDir)/bin
logDir = $(userDir)/logs

INSTALL = install --compare --group=$(group) --owner=$(user) --backup -D

.PHONY: install install-services install-db install-bin

install: install-services install-db install-bin install-logs

install-services: $(serviceDir)/OITDI.service

install-db: $(dbDir)/commands.db $(dbDir)/params.db

install-bin:
	$(INSTALL) --target-directory=$(binDir) --mode=0444 DB.py Params.py TDI.py
	$(INSTALL) --target-directory=$(binDir) --mode=0555 TDIserver.py

install-logs:
	$(INSTALL) --directory $(logDir)

clean:
	$(RM) $(serviceDir)/OITDI.service
	$(RM) $(dbDir)/commands.db
	$(RM) $(dbDir)/params.db
	$(RM) $(binDir)/DB.py $(binDir)/Params.py $(binDir)/TDI.py $(binDir)/TDIserver.py

$(dbDir)/commands.db: commands.schema
	$(INSTALL) --directory $(@D)
	sqlite3 $@ < $<
	chown -R $(user):$(group) $@

$(dbDir)/params.db: params.schema
	$(INSTALL) --directory $(@D)
	sqlite3 $@ < $<
	chown -R $(user):$(group) $@

$(serviceDir)/OITDI.service: OITDI.service
	sed -e 's?__USER__?$(user)?g' \
	    -e 's?__GROUP__?$(group)?g' \
	    -e 's?__LOGDIR__?$(logDir)?g' \
	    -e 's?__BINDIR__?$(binDir)?g' \
	    -e 's?__DBDIR__?$(dbDir)?g' \
	    <$< >$@
	chown -R $(user):$(group) $@

