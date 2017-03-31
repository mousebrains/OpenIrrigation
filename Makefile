.phony: all install clean start stop restart status

all: Makefile.params install

Makefile.params: config
	./$<

install clean: Makefile.params
	$(MAKE) -C database $@
	$(MAKE) -C scripts $@
	$(MAKE) -C public_html $@
	$(MAKE) -C service $@

start stop restart status reload: Makefile.params
	$(MAKE) -C service $@
