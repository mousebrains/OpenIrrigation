#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user irrigation
#
# Where to install the .service files
serviceDir = /etc/systemd/system

user = irrigation
group = $(user)
userDir = /home/$(user)
webDir = $(userDir)/public_html

INSTALL = install --compare --group=$(group) --owner=$(user) --backup -D

.PHONY: install

install: 
	$(INSTALL) --target-directory=$(webDir) index.php status.php
	$(MAKE) -C js $@

clean:
	$(RM) $(webDir)/index.php $(webDir)/status.php
	$(MAKE) -C js $@
