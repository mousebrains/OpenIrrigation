#! /usr/bin/env python3
#
# Extract information from a DB and generate SQL commands to install it
#
# Tables to be extract:
# site
#
# May-2017, Pat Welch, pat@mousebrains.com

from FetchTable import FetchTable

with FetchTable() as a:
  a.extract('soil', 'name')
  a.extract('crop', 'name')
  a.extract('user', 'name')
  a.extract('email', 'email', {'id'}, { \
	'user': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
		"(SELECT id FROM YYYY WHERE name==?)" \
		], \
	'format': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
		"(SELECT id FROM webList WHERE grp=='XXXX' and key=?)" \
		] \
	})
  a.extract('emailReports', None, {}, { \
	'email': [ \
		"SELECT YYYY.id,YYYY.YYYY FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
		"(SELECT id FROM YYYY WHERE email=?)" \
		], \
	'report': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
		"(SELECT id FROM webList WHERE grp=='reports' and key=?)" \
		] \
          })
  a.extract('site', 'name')
  a.extract('controller', 'name', {'id'}, { \
	'site': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.site;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ] \
		})
  a.extract('sensor', 'name', {'id'}, { \
	'controller': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ], \
	'devType': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='XXXX' and key=?)" \
                ] \
        })
  a.extract('poc', 'name', {'id'}, { \
	'site': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ] \
        })
  a.extract('pocFlow', 'name', {'id'}, { \
	'poc': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ], \
	'sensor': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ] \
        })
  a.extract('pocMV', 'name', {'id'}, { \
	'poc': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ], \
	'sensor': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ] \
        })
  a.extract('pocPump', 'name', {'id'}, { \
	'poc': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ], \
	'sensor': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ] \
        })
  a.extract('station', 'name', {'id'}, { \
	'poc': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ], \
	'sensor': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ] \
        })
  a.extract('program', 'name', {'id'}, { \
	'site': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ], \
	'onOff': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='YYYY' and key=?)" \
                ], \
	'action': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='evAct' and key=?)" \
                ], \
	'startMode': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='evCell' and key=?)" \
                ], \
	'stopMode': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='evCell' and key=?)" \
                ] \
        })
  a.extract('pgmDOW', None, {'id'}, { \
	'program': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ], \
	'dow': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='YYYY' and key=?)" \
                ] \
        })
  a.extract('pgmStn', ['program', 'station'], {'id'}, { \
	'program': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ], \
	'station': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ], \
	'mode': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='pgm' and key=?)" \
                ] \
        })
  a.extract('event', 'name', {'id'}, { \
	'site': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ], \
	'action': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='evAct' and key=?)" \
                ], \
	'startMode': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='evCell' and key=?)" \
                ], \
	'stopMode': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='evCell' and key=?)" \
                ] \
        })
  a.extract('eventDOW', None, {'id'}, { \
	'event': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ], \
	'dow': [ \
		"SELECT webList.id,webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='YYYY' and key=?)" \
                ] \
        })
  a.extract('groups', ['site', 'name'], {'id'}, { \
	'site': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ] \
	})
  a.extract('groupStation', ['groups', 'station'], {}, { \
	'groups': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
		"(SELECT id FROM YYYY WHERE name=?)" \
		], \
	'station': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ] \
          })
  a.extract('EtStation', ['station'], {'id'}, { \
	'station': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
               ], \
	'crop': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ], \
	'soil': [ \
		"SELECT YYYY.id,YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name==?)" \
                ] \
        })
