.PHONY: all freshdb install uninstall clean start stop restart status enable disable reload cleanlogs php_lint

all:

Makefile.params: config
	@echo You should rerun $< since it is newer than $@

all install clean: Makefile.params
	$(MAKE) -C database $@
	$(MAKE) -C scripts $@
	$(MAKE) -C public_html $@
	$(MAKE) -C service $@
	$(MAKE) -C webserver $@

uninstall: Makefile.params
	$(MAKE) -C service uninstall
	$(MAKE) -C public_html uninstall
	$(MAKE) -C scripts uninstall
	$(MAKE) -C webserver uninstall
	$(MAKE) -C database uninstall

freshdb: Makefile.params
	$(MAKE) -C database freshdb

enable disable start stop restart status reload: Makefile.params
	$(MAKE) -C service $@

cleanlogs: Makefile.params
	$(MAKE) stop
	$(RM) $(LOGDIR)/*.log
	$(MAKE) start

php_lint:
	$(MAKE) -C public_html $@
