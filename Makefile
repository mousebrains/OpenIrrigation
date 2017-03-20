.phony: all install clean

all: install

install clean:
	$(MAKE) -C packages $@
	$(MAKE) -C database $@
	$(MAKE) -C scripts $@
	$(MAKE) -C public_html $@
	$(MAKE) -C service $@
