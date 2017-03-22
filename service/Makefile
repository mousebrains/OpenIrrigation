#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../Makefile.params

# Where to install the .service files
SERVICEDIR = /etc/systemd/system
SRC = OITDI.service
DEST = $(SRC:%=$(SERVICEDIR)/%)

.PHONY: install install-services install-logs clean start stop retart status

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
	systemctl --no-pager daemon-reload
	for i in $(SRC); do systemctl --no-pager restart $$i; done

start stop status:
	for i in $(SRC); do systemctl --no-pager $@ $$i; done
