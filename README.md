# OpenIrrigation
## Enterprise class irrigation control software with a well defined hardware interface layer.
---
* The feature set includes:
  - Multiple sites
  - Multiple controllers per site (Currently only a Tucor TDI 2 wire board is implemented.)
    + Maximum number of stations per controller.
    + Maximum current per controller.
  - Multiple points of connect, POCs, which can span controllers.
    + Maximum flow per POC.
    + Delay before turning on valves per POC.
    + Delay after turning off valves per POC.
    + Each POC can have multiple flow sensors. 
    + Each POC can have multiple master valves.
    + Each POC can have multiple booster pumps. (Not yet implemented in the scheduler.)
  - Multiple users
    + Each user can have multiple emails
    + Each email can have multiple report types, i.e. critical to SMS and others to email
  - Unlimited number of valves or sensors per controller.
    + Device active and passive currents.
    + Each sensor can be associated with an irrigation station.
  - An Irrigation station will be associated with a sensor.
    + Each station has a priority for scheduling.
    + Each station has a maximum number of contemporaneous valves that can be running while it is one.
    + Each station has a delay after turning on and before turning off for estimating flows.
    + Each station has an associated POC.
    + Each station has soak time.
    + Each station has mininum and maximum cycle time.
    + Each station has a user supplied and estimated flow rate.
    + Each station has low and high flow alert thresholds.

  - Unlimited number of programs spanning controllers and POCs.
    + Programs can be individually turned on or off.
    + Programs can be scheduled every n days or by day of week.
    + Programs start times can be wall clock time or referenced to sunrise/sunset/...
    + Programs can have a maximum number of simultaneous stations.
    + Programs can have a maximum allowed flow.

  - Each station can be associated with multiple programs, a program station.
    + Program stations can be individually turned on or off.
    + Program stations have a total run time.
    + Program stations have a priority associated which defines the scheduling order.

  - GPS coordinates for each asset.

  - There is a start at evapo-transpiration, ET, but it is not fully implemented.

* This software is written in a mix of:
  - Python >= 3.11 for the backend processing,
  - PostgreSQL 17 for the database, and
  - PHP 8.x, HTML, and Javascript for the HTML 5 interface.

---
* Backend software needed:
  - A webserver such as NGINX or Apache software supporting PHP 8.x
  - Python >= 3.11
  - PostgreSQL 17
  - Some form of service/crontab process management

* The non-standard Python modules installed are:
  - serial
  - psycopg (v3)
  - astral

---
* It is tested on the following system:
  - A Raspberry Pi 3 running Raspberry Pi OS (Debian Trixie),
  - a USB-Serial connection to a Tucor TDI board,
  - 50+ valves, and
  - Agrimet for evapotranspiration, ET, information.

---
* There are well defined APIs between the layers:
  - There is a hardware interface layer,
  - a scheduling engine,
  - an HTML5 interface layer to the database.

---
## The non-web user visible processing is written entirely in English.
