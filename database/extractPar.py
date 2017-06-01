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
  a.extract('soil')
  a.extract('crop')
  a.extract('user')
  a.extract('email', {'id'}, { \
	'user': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'format': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='XXXX' and key='{}')" \
                ] \
          })
  a.extract('emailReports', {}, { \
	'email': [ \
		"SELECT YYYY.YYYY FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE email='{}')" \
                ], \
	'report': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='reports' and key='{}')" \
                ] \
          })
  a.extract('site')
  a.extract('controller', {'id'}, { \
	'site': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.site;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ] \
        })
  a.extract('sensor', {'id'}, { \
	'controller': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'devType': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='XXXX' and key='{}')" \
                ] \
        })
  a.extract('poc', {'id'}, { \
	'site': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ] \
        })
  a.extract('pocFlow', {'id'}, { \
	'poc': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'sensor': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ] \
        })
  a.extract('pocMV', {'id'}, { \
	'poc': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'sensor': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ] \
        })
  a.extract('pocPump', {'id'}, { \
	'poc': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'sensor': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ] \
        })
  a.extract('station', {'id'}, { \
	'poc': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'sensor': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ] \
        })
  a.extract('program', {'id'}, { \
	'site': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'onOff': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='YYYY' and key='{}')" \
                ], \
	'action': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='evAct' and key='{}')" \
                ], \
	'startMode': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='evCell' and key='{}')" \
                ], \
	'stopMode': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='evCell' and key='{}')" \
                ] \
        })
  a.extract('pgmDOW', {'id'}, { \
	'program': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'dow': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='YYYY' and key='{}')" \
                ] \
        })
  a.extract('pgmStn', {'id'}, { \
	'program': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'station': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'mode': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='pgm' and key='{}')" \
                ] \
        })
  a.extract('event', {'id'}, { \
	'site': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'action': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='evAct' and key='{}')" \
                ], \
	'startMode': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='evCell' and key='{}')" \
                ], \
	'stopMode': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='evCell' and key='{}')" \
                ] \
        })
  a.extract('eventDOW', {'id'}, { \
	'event': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'dow': [ \
		"SELECT webList.key FROM webList INNER JOIN XXXX ON webList.id==XXXX.YYYY;", \
                "(SELECT id FROM webList WHERE grp=='YYYY' and key='{}')" \
                ] \
        })
  a.extract('EtStation', {'id'}, { \
	'station': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'crop': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ], \
	'soil': [ \
		"SELECT YYYY.name FROM YYYY INNER JOIN XXXX ON YYYY.id==XXXX.YYYY;", \
                "(SELECT id FROM YYYY WHERE name='{}')" \
                ] \
        })
