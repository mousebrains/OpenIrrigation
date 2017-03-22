.phony: all install clean start stop restart status

all: install

install clean:
	$(MAKE) -C database $@
	$(MAKE) -C scripts $@
	$(MAKE) -C public_html $@
	$(MAKE) -C service $@

start stop restart status:
	$(MAKE) -C service $@
