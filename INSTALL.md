
Python packages to install:
 1. python3-psycopg2
 2. python3-astral

In root director of OpenIrrigation run ./config
Here is my implementation:

./config --user=irrigation --group=irrigation  --dbname=irrigation --site=Casa --controller=Casa --prefix=/home/irrigation --simulate

To create a user/role for PostgreSQL, say for user pi, you can run:

sudo -u postgres createuser --createdb --login pi

A user/role will automatically be created for the uer specified in the config command line.
