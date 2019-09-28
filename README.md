# OpenIrrigation

Enterprise class irrigation control software with a well defined hardware interface layer.

  * The feature set includes:
 1. Support for one flow sensor per point of connection, POC, with a known K and offset.
 2. Support for multiple booster pumps per point of connect with flow thresholds.
 3. Support for for multiple organzations.
 4. Support for unlimited sites per organization.
 5. Support for unlimited number of users and rolls per site/organization/web interface.
 6. Support for unlimited number of  controlers per site.
 7. Support for an unlimited number of valves.
 8. Support for an unlimited number of programs spanning controllers and POCs.
 9. Support for multiple prioritiezed water windows per program.
 10. Support for sunrise/sunset relative start/end times in water windows.
 11. Support for an unlimited number of valves per program.
 12. Support for an unlimited number of POCs per program.
 13. Support for an flow constrained number of active valves per POC.
 14. Support for a maximum number of active valves per controller.
 15. Support for low/high flow alerts.
 16. Support for low/high current alerts.
 17. GPS coordinates for each asset.
 18. A reference evapotranspiration, ETr, source per site.
 19. Time dependent root depths and crop coefficients

  * This software is written in a mix of:
 1. Pyton 3.x for the backend and CGI processing, 
 2. SQLite 3.x for the database, and
 3. PHP 7.x, HTML, and Javascript for the HTML 5 interface.

  * Backend software includes:
 1. NGINX or Apache software supporting PHP 7.x and CGI scripts,
 2. Python 3.x,
 3. PostgreSQL
 4. PHP 7.x, and php-fpm
 5. Some form of service/crontab process managment.

  * The non-standard Python modules installed are:
 1. postgresql
 1. Astral

  * It is tested on the following system:
 1. A Raspberry Pi 3 running Raspbian Buster Lite and a MacOS 10.12 system,
 2. a USB-Serial connection to a Tucor TDI board,
 3. 50+ valves, and
 4. Agrimet for evapotranspiration, ET, information.

  * There are well defined APIs between the layers:
 1. There is a hardware interface layer,
 2. a scheduling engine,
 3. a dynamic ET depletion layer invoked by the scheduling enging,
 4. a static ET layer to define available water, root depth, ..., and
 5. an HTML5 interface layer to the database.

## The non-web user visible processing is written entirely in English.

  * PostgreSQL
  1. Due to concurrency issues, the underlying database is PostgreSQL.
  2. Install PostgreSQL.
  3. Create roll, irrigation.
  4. Create database, irrigation.
