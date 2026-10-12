#
# Install the systemd units for a Debian system with a user/group
#

include ../Makefile.params

# Long-running daemons
DAEMONS = OITDI.service
DAEMONS+= OISched.service

# Oneshot units, each run by its timer
ONESHOTS = OIAgriMet.service
ONESHOTS+= OIAgriMetStats.service
ONESHOTS+= OIDailyReport.service
ONESHOTS+= OIDatabaseMaintenance.service
ONESHOTS+= OIFilterMonitor.service
ONESHOTS+= OIFlowSensorWatch.service

SERVICES = $(DAEMONS) $(ONESHOTS)

# Timers
TIMERS = OIAgriMet.timer
TIMERS+= OIAgriMetStats.timer
TIMERS+= OIDailyReport.timer
TIMERS+= OIDatabaseMaintenance.timer
TIMERS+= OIFilterMonitor.timer
TIMERS+= OIFlowSensorWatch.timer

# Templates, started by other units (OnFailure=) and never enabled themselves
TEMPLATES = OIFailure@.service

SRC = $(SERVICES) $(TIMERS)

DEST = $(SRC:%=$(SERVICEDIR)/%) $(TEMPLATES:%=$(SERVICEDIR)/%)

.PHONY: all install install-services install-logs uninstall clean start stop restart status reload enable disable

all:

install: install-logs install-services

# Enable the daemons and timers so a newly added timer survives a reboot, and
# start the timers. Starting a timer doesn't run its service until it next
# elapses (or at once, for a Persistent= timer that missed a run while
# stopped). The daemons keep running the old code until 'make restart'.
install-services: $(DEST)
	systemctl --no-pager daemon-reload
	systemctl --no-pager enable $(DAEMONS)
	systemctl --no-pager enable --now $(TIMERS)

install-logs:
	$(INSTALL) --directory $(LOGDIR)
	chown -R $(USER):$(GROUP) $(LOGDIR)

clean:

uninstall:
	-systemctl --no-pager disable --now $(TIMERS) $(DAEMONS)
	$(RM) $(DEST)
	systemctl --no-pager daemon-reload

# systemd runs units as root, so their files must be root-owned and not
# writable by the service user
$(SERVICEDIR)/%: % ../Makefile.params
	sed -e 's?__USER__?$(USER)?g' \
	    -e 's?__GROUP__?$(GROUP)?g' \
	    -e 's?__LOGDIR__?$(LOGDIR)?g' \
	    -e 's?__ARCHIVEDIR__?$(ARCHIVEDIR)?g' \
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
	chown root:root $@
	chmod 0644 $@

reload:
	systemctl --no-pager daemon-reload

# Restart the daemons, and the timers that are running (to pick up schedule
# changes). Restarting every unit would run each oneshot at once -- an extra
# daily report per deploy -- and start timers that were left stopped. The
# oneshots load their new code on their next run.
restart: reload
	systemctl --no-pager restart $(DAEMONS)
	systemctl --no-pager try-restart $(TIMERS)

enable:
	systemctl --no-pager enable $(TIMERS) $(DAEMONS)

disable:
	systemctl --no-pager disable $(TIMERS) $(DAEMONS)

start:
	systemctl --no-pager start $(TIMERS) $(DAEMONS)

stop:
	systemctl --no-pager list-unit-files $(SRC) --no-legend | awk '{print $$1}' | xargs -r systemctl --no-pager stop

status:
	-systemctl --no-pager status $(SRC)
	systemctl --no-pager list-timers $(TIMERS)
