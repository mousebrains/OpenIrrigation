# Scripts, schemas, and information to create/update the irrigation databases

## SQL Files
- db.schema.sql -- Main file defining the database schema (custom domains, tables, constraints, NOTIFY triggers)
- db.site.sql -- Defines a trigger on insertions into site to add a manual program for it
- db.funcs.sql -- Collection of utility functions, mostly for the web, including the generic_notify trigger
- db.list.sql -- Populate the webList table
- db.params.sql -- Populate the params table
- db.ET.sql -- Populate the ET parameters into the params table
- db.soil.sql -- Populate the soil table
- db.crop.sql -- Populate the crop table
- db.changelog.sql -- Schema migration/changelog entries

## Utilities
- extract.site.py -- Extract site and configuration data from an existing database into portable SQL INSERT statements
