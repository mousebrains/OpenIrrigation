#
# Install scripts into appropriate directories for a Raspbian Stretch system
# with a user/group
#

include ../Makefile.params

DBNAME = irrigation

SQL = db.schema.sql
SQL+= db.funcs.sql
SQL+= db.list.sql
SQL+= db.params.sql
SQL+= db.ET.sql
SQL+= db.soil.sql
SQL+= db.crop.sql
SQL+= db.site.sql

.PHONY: all extract install clean mkdb recreatedb dropdb createdb dumpdb

all:

install:

clean:

mkdb: $(SQL)
	for i in $^; do echo $$i; psql --quiet $(DBNAME) <$$i; done

recreatedb: dropdb createdb

dropdb:
	dropdb $(DBNAME)

createdb:
	createdb $(DBNAME)

dumpdb:
	pg_dump $(DBNAME) | gzip -v9 >$(DBNAME).dump.gz
