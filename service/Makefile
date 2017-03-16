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

install-db: $(dbDir)/commands.db

install-bin:
	$(INSTALL) --target-directory=$(binDir) --mode=0444 DB.py Params.py TDI.py
	$(INSTALL) --target-directory=$(binDir) --mode=0555 TDIserver.py

install-logs:
	$(INSTALL) --directory $(logDir)

clean:
	$(RM) $(serviceDir)/OITDI.service
	$(RM) $(dbDir)/commands.db
	$(RM) $(binDir)/DB.py $(binDir)/Params.py $(binDir)/TDI.py $(binDir)/TDIserver.py

$(dbDir)/commands.db: commands.schema
	$(INSTALL) --directory $(@D)
	sqlite3 $@ < $<
	chown -R $(user):$(group) $@

$(serviceDir)/OITDI.service: OITDI.service
	sed -e 's?__USER__?$(user)?' \
	    -e 's?__GROUP__?$(group)?' \
	    -e 's?__LOGDIR__?$(logDir)?' \
	    -e 's?__BINDIR__?$(binDir)?' \
	    -e 's?__DBDIR__?$(dbDir)?' \
	    <$< >$@
	chown -R $(user):$(group) $@

