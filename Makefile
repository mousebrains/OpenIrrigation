.phony: all install clean start stop restart status enable disable reload cleanlogs

all: Makefile.params install

Makefile.params: config
	./$<

install clean: Makefile.params
	$(MAKE) -C database $@
	$(MAKE) -C scripts $@
	$(MAKE) -C public_html $@
	$(MAKE) -C service $@

enable disable start stop restart status reload: Makefile.params
	$(MAKE) -C service $@

cleanlogs: Makefile.params
	$(MAKE) stop
	$(RM) $(LOGDIR)/*.log
	$(MAKE) start
