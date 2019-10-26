#
# Install scripts into appropriate directories for a Raspbian Buster system
# with a user/group
#

include ../Makefile.params

# Where to install the .service files
SRC = OITDI.service
SRC+= OIAgriMet.service
SRC+= OISched.service

OSRC= OINotify@.service

DEST = $(SRC:%=$(SERVICEDIR)/%) $(OSRC:%=$(SERVICEDIR)/%)

.PHONY: all install install-services install-logs clean start stop retart status reload enable disable

all:

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
	    -e 's?__DBNAME__?$(DBNAME)?g' \
	    -e 's?__SITENAME__?$(SITENAME)?g' \
	    -e 's?__CONTROLLERNAME__?$(CONTROLLERNAME)?g' \
	    -e 's?__SIMULATE__?$(SIMULATE)?g' \
	    <$< >$@
	chown -R $(USER):$(GROUP) $(@D)

reload:
	systemctl --no-pager daemon-reload

restart: reload
	systemctl --no-pager restart $(SRC)

enable disable start stop status:
	systemctl --no-pager $@ $(SRC)
