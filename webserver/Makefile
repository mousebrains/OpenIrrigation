#
# Install webserver (nginx + php-fpm) configuration
#

include ../Makefile.params

.PHONY: all install uninstall clean

all:

install:
	./setup.sh --user=$(USER) --webroot=$(WEBDIR) --webuser=$(WEBUSER) --dbname=$(DBNAME)

clean:

uninstall:
