.phony: all install clean restart status

all: install

install clean:
	$(MAKE) -C packages $@
	$(MAKE) -C database $@
	$(MAKE) -C scripts $@
	$(MAKE) -C public_html $@
	$(MAKE) -C service $@

restart status:
	$(MAKE) -C service $@
