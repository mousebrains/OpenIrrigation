# Installation of OpenIrrigation

## For detailed instructions of how to setup a [Raspbian system](https://github.com/mousebrains/OpenIrrigation/blob/master/INSTALL.raspbian.md#git-installation)
---
## Get The OpenIrrigation package
I do this as my non-irrigation user, i.e. foo above or whatever you call it. It does need to be a sudoer user.
- cd ~
- git clone git@github.com:mousebrains/OpenIrrigation.git
---
## Configure the OpenIrrigation system
- cd OpenIrrigation
- ./config --help # To obtain config options.
- For a production system this is the config command I use:
  - . /config --prefix=~irrigation --user=irrigation --roles=irrigation --roles=foo --port=/tty/tty-USB0
- For a simulation system this is the config command I use:
  - ./config --prefix=~irrigation --user=irrigation --roles=irrigation --roles=foo  --simulate
- After configuration examine Makefile.params to make sure the configuration is what you want!
---
## Build a fresh database
- make all # Build a fresh database
- sudo make install # install everything, including services
- At this point you should be able to go to open a web page and start the configuration. The order I use is:
  - site
  - controller
  - user
  - email
  - sensor
  - point of connect
  - point of connect flow
  - point of connect mastervalve
  - point of connect pump
  - station
  - program
  - program station
- sudo make enable start # Enable and start the services
- make status # Will show you the status of the services.
- If a service fails look in /var/log/syslog and ~irrigation/logs/*
