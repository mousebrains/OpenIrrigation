#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../Makefile.params

DBNAME ?= irrigation

SQL = db.schema.sql
SQL+= db.funcs.sql
SQL+= db.list.sql
SQL+= db.params.sql
SQL+= db.ET.sql
# SQL+= db.soil.sql
# SQL+= db.crop.sql
SQL+= db.site.sql

.PHONY: all extract install clean mkdb dropdb createdb dumpdb freshdb mkSite createUser dropUser

all:

install:

clean:


freshdb: dropdb createdb mkdb

mkdb: $(SQL)
	for i in $^; do echo $$i; psql --quiet --file=$$i $(DBNAME); done

createUser:
	- sudo -u postgres createuser --createdb --login $(USER)

dropUser:
	- sudo -u postgres dropuser $(USER)

dropdb: dropUser
	- dropdb $(DBNAME)

createdb: createUser
	- sudo -u postgres createuser --createdb --login $(USER)
	sudo -u $(USER) createdb $(DBNAME)

dumpdb:
	pg_dump $(DBNAME) | gzip -v9 >$(DBNAME).dump.gz

mkSite:
	./extract.site.py --db $(DBNAME) >db.site.sql
