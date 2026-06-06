#
# Install scripts into appropriate directories for a Raspbian Buster system
# with a user/group
#

include ../Makefile.params

# Services (oneshot units triggered by timers, plus long-running daemons)
SERVICES = OITDI.service
SERVICES+= OIAgriMet.service
SERVICES+= OIAgriMetStats.service
SERVICES+= OISched.service
SERVICES+= OIDailyReport.service
SERVICES+= OIDatabaseMaintenance.service

# Timers
TIMERS = OIAgriMet.timer
TIMERS+= OIAgriMetStats.timer
TIMERS+= OIDailyReport.timer
TIMERS+= OIDatabaseMaintenance.timer

SRC = $(SERVICES) $(TIMERS)

DEST = $(SRC:%=$(SERVICEDIR)/%)

.PHONY: all install install-services install-logs uninstall clean start stop restart status reload enable disable

all:

install: install-services install-logs

install-services: $(DEST)
	systemctl --no-pager daemon-reload

install-logs:
	$(INSTALL) --directory $(LOGDIR)
	chown -R $(USER):$(GROUP) $(LOGDIR)

clean:

uninstall:
	-systemctl --no-pager disable --now $(TIMERS) OITDI.service OISched.service
	$(RM) $(DEST)
	systemctl --no-pager daemon-reload

$(SERVICEDIR)/%: % ../Makefile.params
	sed -e 's?__USER__?$(USER)?g' \
	    -e 's?__GROUP__?$(GROUP)?g' \
	    -e 's?__LOGDIR__?$(LOGDIR)?g' \
	    -e 's?__BINDIR__?$(BINDIR)?g' \
	    -e 's?__DBDIR__?$(DBDIR)?g' \
	    -e 's?__DBNAME__?$(DBNAME)?g' \
	    -e 's?__SITENAME__?$(SITENAME)?g' \
	    -e 's?__CONTROLLERNAME__?$(CONTROLLERNAME)?g' \
	    -e 's?__TELEMETRYRETENTIONDAYS__?$(TELEMETRYRETENTIONDAYS)?g' \
	    -e 's?__HISTORYRETENTIONDAYS__?$(HISTORYRETENTIONDAYS)?g' \
	    -e 's?__AUDITRETENTIONDAYS__?$(AUDITRETENTIONDAYS)?g' \
	    -e 's?__SIMULATE__?$(SIMULATE)?g' \
	    <$< >$@
	chown -R $(USER):$(GROUP) $(@D)

reload:
	systemctl --no-pager daemon-reload

restart: reload
	systemctl --no-pager restart $(SRC)

enable:
	systemctl --no-pager enable $(TIMERS) OITDI.service OISched.service

disable:
	systemctl --no-pager disable $(TIMERS) OITDI.service OISched.service

start:
	systemctl --no-pager start $(TIMERS) OITDI.service OISched.service

stop:
	systemctl --no-pager stop $(TIMERS) $(SERVICES)

status:
	-systemctl --no-pager status $(SRC)
	systemctl --no-pager list-timers $(TIMERS)
