# Installation of OpenIrrigation

## For detailed instructions of how to setup a [Debian system](https://github.com/mousebrains/OpenIrrigation/blob/master/INSTALL.debian.md#git-installation)
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
- Retention maintenance archives expired rows as gzip'd CSV into --archiveDir (default <prefix>/archive) before deleting them; with no archive directory it deletes nothing.
---
## Build and initialize
- make all # Build generated files without modifying the database
- New installs only: make freshdb FORCE=1 # Drop and recreate the database and its roles; an existing database is pg_dumped into database/dump.<db>.<time> first
- Existing databases only: run every database/migrate_NNN.py, in order; each is idempotent, so re-running them is safe (see database/README.md)
  - for f in database/migrate_*.py; do python3 "$f" --db irrigation || break; done
  - python3 database/check_schema.py --db irrigation # Reports anything missing and the newest migration applied
- sudo make install # install everything, including services and the archive directory
- make clean # Remove generated build files only
- sudo make uninstall # Explicitly remove installed application files
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
---
## Site map (optional)
map.php ("Site Map" in the menu) shows aerial imagery with your valve boxes, shutoffs and hose bibs on top; a valve box's popup lists the decoders in it, their stations, programs and last/next runs.
- Needs migrate_017.py, and a Makefile.params from a ./config that knows --tileDir (default <prefix>/tiles; rerun ./config with your original options, then sudo make install, which creates the directory)
- Add the features under "Map Features" (name, kind, latitude, longitude, notes), then on each "Sensor" set its "Map box", "Position in box" and "Order in box"
- Cache the imagery, as the install user, so the map works without the imagery server; a rerun only fetches missing tiles:
  - sudo -u irrigation ~irrigation/bin/fetchMapTiles.py --db irrigation --preset osip2024
  - Presets are Oregon's 1-ft statewide imagery (osip2024, osip2022). Its server's TLS certificate expired 2026-09-26; add --insecure until it is renewed (the tiles are public imagery)
  - Elsewhere, any ArcGIS ImageServer or MapServer: --layer NAME --url URL --label TEXT --attribution TEXT
  - The area is the map features plus --margin meters (default 150), zooms --zmin..--zmax (15..20, about 300 tiles and a few MB for a house lot); --dry-run counts the tiles
- Without cached imagery the map falls back to OpenStreetMap, which needs the internet
