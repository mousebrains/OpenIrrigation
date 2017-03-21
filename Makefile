.phony: all install clean start stop restart status

all: install

install clean:
	$(MAKE) -C packages $@
	$(MAKE) -C database $@
	$(MAKE) -C scripts $@
	$(MAKE) -C public_html $@
	$(MAKE) -C service $@

start stop restart status:
	$(MAKE) -C service $@
