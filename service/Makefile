#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#

include ../Makefile.params

# Where to install the .service files
SERVICEDIR = /etc/systemd/system
SRC = OITDI.service
DEST = $(SRC:%=$(SERVICEDIR)/%)

.PHONY: install install-services install-logs clean retart status

install: install-services install-logs

install-services: $(DEST)

install-logs:
	$(INSTALL) --directory $(LOGDIR)
	chown -R $(USER):$(GROUP) $(LOGDIR)

clean:
	$(RM) $(DEST)

$(SERVICEDIR)/%: %
	sed -e 's?__USER__?$(USER)?g' \
	    -e 's?__GROUP__?$(GROUP)?g' \
	    -e 's?__LOGDIR__?$(LOGDIR)?g' \
	    -e 's?__BINDIR__?$(BINDIR)?g' \
	    -e 's?__DBDIR__?$(DBDIR)?g' \
	    <$< >$@
	chown -R $(USER):$(GROUP) $(@D)

restart:
	systemctl daemon-reload
	for i in $(SRC); do systemctl restart $$i; done

status:
	for i in $(SRC); do systemctl status $$i; done
