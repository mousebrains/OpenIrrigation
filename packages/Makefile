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
jsDir = $(webDir)/js

INSTALL = install --compare --group=$(group) --owner=$(user) --backup -D

.PHONY: install install-javascript

install: install-javascript

install-javascript:
	$(INSTALL) --target-directory=$(jsDir) --mode=0444 jquery-3.2.0.min.js jquery-3.2.0.min.map

clean:
	$(RM) $(jsDir)/jquery-3.2.0*
