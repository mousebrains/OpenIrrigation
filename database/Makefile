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

.PHONY: all extract install clean mkdb dropdb createdb dumpdb freshdb mkSite

all:

install:

clean:

freshdb: dropdb createdb mkdb

mkdb: $(SQL)
	for i in $^; do echo $$i; psql --quiet --file=$$i $(DBNAME); done

dropdb:
	dropdb $(DBNAME)

createdb:
	createdb $(DBNAME)

dumpdb:
	pg_dump $(DBNAME) | gzip -v9 >$(DBNAME).dump.gz

mkSite:
	./extract.site.py --db $(DBNAME) >db.site.sql
