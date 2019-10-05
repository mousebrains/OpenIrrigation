
Python packages to install:
 1. python3-psycopg2
 2. python3-astral
 3. php-pgsql

In root director of OpenIrrigation run ./config
Here is my implementation:

./config --user=irrigation --group=irrigation  --dbname=irrigation --prefix=/home/irrigation --simulate

In OpenIrrigation/database issue the following command to build roles and database schema:

make clean freshdb

You should now be able to go to the web page and fill in the 
 1. Site
 2. Controller
 3. Point-of-connect

Once this is done go to OpenIrrigation/service enter:

make install enable restart

which will install the service scripts and start them. At this point the web page should be showing current and flow in simulation mode.
