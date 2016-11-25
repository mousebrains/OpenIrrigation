# OpenIrrigation

Enterprise class irrigation control software with a well defined hardware interface layer.

  * This software is written in a mix of:
 1. Pyton 3.x for the backend and CGI processing, 
 2. SQLite 3.x for the database, and
 3. PHP 7.x, HTML, and Javascript for the HTML 5 interface.

  * Backend software includes:
 1. NGINX or Apache software supporting PHP 7.x and CGI scripts,
 2. Python 3.x,
 3. SQLite 3.x,
 4. PHP 7.x, and
 5. Some form of service/crontab process managment.

  * The non-standard Python modules installed are:
 1. sqlite3

  * It is tested on the following system:
 1. A Raspberry Pi 3 running Raspbian Jessie Lite and a MacOS 10.12 system,
 2. a USB-Serial connection to a Tucor TDI board,
 3. 50+ valves, and
 4. Agrimet for evapotranspiration, ET, information.

  * There are well defined APIs between the layers:
 1. There is a hardware interface layer,
 2. a scheduling engine,
 3. a dynamic ET depletion layer invoked by the scheduling enging,
 4. a static ET layer to define available water, root depth, ..., and
 5. an HTML5 interface layer to the database.
