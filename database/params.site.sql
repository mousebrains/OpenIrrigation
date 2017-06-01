-- user information
INSERT INTO user (name) VALUES ('Pat');
INSERT INTO user (name) VALUES ('Teresa');

-- email information
INSERT INTO email (email,user,format) VALUES 
 ('pat@mousebrains.com', 
  (SELECT id FROM user WHERE name=='Pat'), 
  (SELECT id FROM webList WHERE grp=='email' AND key=='html')
 ),
 ('5412207738@vtext.com', 
  (SELECT id FROM user WHERE name=='Pat'), 
  (SELECT id FROM webList WHERE grp=='email' AND key=='sms')
 ),
 ('welch.teresa@gmail.com', 
  (SELECT id FROM user WHERE name=='Teresa'), 
  (SELECT id FROM webList WHERE grp=='email' AND key=='html')
 ),
 ('5412078955@vtext.com', 
  (SELECT id FROM user WHERE name=='Teresa'), 
  (SELECT id FROM webList WHERE grp=='email' AND key=='sms')
 );

-- report/alerts
INSERT INTO webList(sortOrder,grp,key,label) VALUES(0,'reports','lowFlow', 'Low Flow Alerts');
INSERT INTO webList(sortOrder,grp,key,label) VALUES(1,'reports','highFlow', 'High Flow Alerts');
INSERT INTO webList(sortOrder,grp,key,label) VALUES(2,'reports','electrical', 'Electrical Alerts');
INSERT INTO webList(sortOrder,grp,key,label) VALUES(3,'reports','controller', 'Controller Alerts');
INSERT INTO webList(sortOrder,grp,key,label) VALUES(4,'reports','daily', 'Daily Summary Report');

-- which reports/alerts each email receives
INSERT into emailReports VALUES (
 (SELECT id FROM email WHERE email=='pat@mousebrains.com'),
 (SELECT id FROM webList WHERE grp=='reports' and key=='lowFlow'));
INSERT into emailReports VALUES (
 (SELECT id FROM email WHERE email=='pat@mousebrains.com'),
 (SELECT id FROM webList WHERE grp=='reports' and key=='electrical'));

-- site information
INSERT INTO site (name,addr,timezone,latitude,longitude,elevation) VALUES (
 'Casa', '6513 SW Janet Way, Corvallis, OR 97333, USA', 'US/Pacific',
 44.495399, -123.335120, 350
);

-- SELECT * FROM site;

-- controller information
INSERT INTO controller(site,name,latitude,longitude,driver,maxStations,
                       maxCurrent,make,model,installed) VALUES (
 (SELECT id FROM site WHERE name=='Casa'), 'Casa',
 (SELECT latitude FROM site WHERE name=='Casa'),
 (SELECT longitude FROM site WHERE name=='Casa'),
 'TDI', 10, 1000, 'TPW', 'Pi/TDI', 
 strftime('%s', '2015-10-01')
);

-- SELECT * FROM controller;

-- sensor information, valves, sensors, ...
-- flow sensor
INSERT INTO sensor(name,devType,addr,model) VALUES(
 'Flow 0', (SELECT id FROM webList WHERE grp='sensor' and key=='flow'), 0, 'WT2W-FD');
-- Master Valve
INSERT INTO sensor(name,addr,activeCurrent,make,model) VALUES (
  'MasterValve 0', 240, 30, 'Superior', 3300150);

INSERT INTO sensor(addr) VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9);
INSERT INTO sensor(addr) VALUES (12),(13),(14),(15),(16),(17),(18),(19),(20),(21),(22),(23);
INSERT INTO sensor(addr) VALUES (27),(28),(29);
INSERT INTO sensor(addr) VALUES (33),(34),(35),(36),(37),(38),(39);
INSERT INTO sensor(addr) VALUES (43),(44),(45),(46),(47);
INSERT INTO sensor(addr) VALUES (51),(52),(53);
INSERT INTO sensor(addr) VALUES (57),(58),(59),(60),(61),(62),(63),(64),(65),(66);
INSERT INTO sensor(addr) VALUES (70),(71),(72);

UPDATE sensor SET controller=(SELECT controller.id FROM controller WHERE controller.name=='Casa');
UPDATE sensor SET name=printf('Station %d', addr+1) WHERE name is NULL;
UPDATE sensor SET devType=(
	SELECT webList.id FROM webList WHERE webList.grp=='sensor' AND webList.key=='solenoid') 
	WHERE devType IS NULL;
UPDATE sensor SET latitude=(
	SELECT controller.latitude FROM controller WHERE controller.name=='Casa');
UPDATE sensor SET longitude=(
	SELECT controller.longitude FROM controller WHERE controller.name=='Casa');
UPDATE sensor SET driver='TDI' WHERE driver IS NULL;
UPDATE sensor SET installed=strftime('%s', '2012-10-01') WHERE installed IS NULL;

UPDATE sensor SET wirePath=0 WHERE addr is NULL AND (addr < 70); -- Two wire path
UPDATE sensor SET wirePath=1 WHERE addr is NULL AND (addr >= 70); -- Two wire path

UPDATE sensor SET make='WeatherTrak' WHERE make IS NULL;
UPDATE sensor SET model='WT2W-SVD-11' WHERE model IS NULL;

-- .schema sensor
-- SELECT * FROM sensor;

-- Point of connection
INSERT INTO poc(site,name,targetFlow,maxFlow,delayOn,delayOff) VALUES
 ((SELECT id FROM site WHERE name='Casa'), 'Outside', 12, 15, 10, 10);
INSERT INTO poc(site,name,targetFlow,maxFlow,delayOn,delayOff) VALUES
 ((SELECT id FROM site WHERE name='Casa'), 'Selva', 5, 5, 10, 10);

-- SELECT * FROM poc;

-- Point of connection flow sensors
INSERT INTO pocFlow(poc,sensor,name,make,model,toHertz,K,offset) VALUES (
  (SELECT id FROM poc WHERE name='Outside'),
  (SELECT id FROM sensor WHERE name='Flow 0'),
  'Outside Flow', 'Creative Sensor', 'FSI-T10-001', 0.1, 0.322, 0.200
);

-- SELECT * FROM pocFlow;

-- Point of connection master valves
INSERT INTO pocMV(poc,sensor,name,make,model,qNormallyOpen) VALUES (
  (SELECT id FROM poc WHERE name='Outside'),
  (SELECT id FROM sensor WHERE addr=240),
  (SELECT name FROM sensor WHERE addr=240),
  (SELECT make FROM sensor WHERE addr=240),
  (SELECT model FROM sensor WHERE addr=240),
  1
);

-- SELECT * FROM pocMV;

-- Station information
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (1,'Huerto S/norte', 1.2,120,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (2,'Huerto S/oeste', 0.8,60,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (3,'Huerto S/centro', 1.9,120,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (4,'Huerto S/sur', 6.8,120,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (5,'Huerto N/arriba', 3.9, 20,20);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (6,'Huerto N/abajo', 5.0, 60,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (7,'Huerto E/NE', 0.0, 60,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (8,'Huerto E/NO', 0.0, 60,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (9,'Huerto E/SE', 0.0, 60,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (10,'Huerto E/SO', 0.0, 60,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (13,'Este/norte y centro', 1.1, 30,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (14,'Este/fondo', 1.1, 60,20);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (15,'Este/sur', 0.8, 90,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (16,'Franja/oeste', 1.4, 75,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (17,'Franja/curva', 0.9, 30,30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (18,'Franja/este', 0.3, 75,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (19,'Isla/norte', 1.6, 80,30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (20,'Isla/sur', 1.4, 75,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (21,'Abeto Douglas', 1.1, 90,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (22,'Sala/patio abierto', 0.3, 50,20);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (23,'Sala/patio cuierto', 0.3, 60,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (24,'Hierbas', 2.7, 80,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (28,'Sala', 0.5, 70,20);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (29,'Comedor/patio', 0.5, 50,20);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (30,'Comedor', 0.6, 75,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (34,'Entrada/azaleas', 2, 25,20);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (35,'Entrada/centro', 1, 100,20);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (36,'Entrada/frente', 0.1, 15,20);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (37,'Entrada/isla', 1.3, 70,10);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (38,'Berma/oeste', 2.3, 80,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (39,'Escobon', 2.1, 60,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (40,'Berma/este', 1.4, 75,15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (44,'Abedul', 1.8, 80,20);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (45,'Janet Way', 5.5, 90, 15);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (46,'Azaleas/brezo/arbustos', 5.4, 80, 20);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (47,'Rododendros', 3.1, 60, 30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (48,'Rosales', 0.4, 60, 30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (52,'Cesta colgante', 0.1, 2, 10);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (53,'Barriles', 0.1, 5, 10);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (54,'Bebedero', 1, 100, 1);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (58,'Cesped entrada', 11, 10, 30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (59,'Cesped rosales norte', 10.8, 10,30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (60,'Cesped rosales sur', 12.4, 10,30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (61,'Cesped centro', 9.8, 10,30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (62,'Cesped arbol', 9.8, 10,30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (63,'Cesped abeto', 6.3, 10,30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (64,'Cesped huerto sur', 8, 10,30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (65,'Cesped isla', 7.6, 10,30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (66,'Cesped manzanas', 8.7, 10,30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (67,'Cesped huerto norte', 7.2, 10,30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (71,'Selva plantas', 0.1, 2, 10);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (72,'Selva goteo', 2.0,300, 30);
INSERT INTO station(station,name,userFlow,maxCycleTime,soakTime) VALUES (73,'Selva rocio', 0.1, 2, 2);

UPDATE station SET poc=(SELECT poc.id FROM poc WHERE poc.name='Outside') WHERE station < 71;
UPDATE station SET poc=(SELECT poc.id FROM poc WHERE poc.name='Selva') WHERE station > 70;
UPDATE station SET sensor=(
	SELECT sensor.id FROM sensor 
	INNER JOIN webList 
	ON webList.id==sensor.devType AND webList.key=='solenoid' 
	WHERE station.station==(sensor.addr+1)) 
	WHERE sensor IS NULL;
UPDATE station SET make='Hunter',model='PGV-100A';
UPDATE station SET sortOrder=id;
UPDATE station SET soakTime=soakTime*60; -- minutes to seconds
UPDATE station SET maxCycleTime=maxCycleTime*60; -- minutes to seconds

-- SELECT * FROM station;

-- Specialized programs
INSERT INTO program (name,priority,startTime,endTime,qHide) VALUES
	('Manual', -1, 60, 86400-60,1); -- all day
INSERT INTO program (name,priority,startTime,endTime,qHide) VALUES
	('Flow Check', 100000, 60, 86400-60,1); -- all day
INSERT INTO program (name,priority,startTime,endTime,qHide) VALUES
	('Electrical Check', 1000000, 60, 86400-60,1); -- all day

-- programs
INSERT INTO program (name,priority,startTime,endTime) VALUES
	('Selva plantas', 1,
 	strftime('%s', '20:00:00')-strftime('%s','00:00:00'),
 	strftime('%s', '22:00:00')-strftime('%s','00:00:00')
	);

INSERT INTO program (name,priority,action,nDays,refDate,startTime,endTime) VALUES
	('Selva goteo', 3,
	(SELECT id FROM webList WHERE grp=='evAct' AND key=='nDays'), 
	21,
 	strftime('%s', '2017-04-05 12:00'),
 	strftime('%s', '18:00:00')-strftime('%s','00:00:00'),
 	strftime('%s', '22:00:00')-strftime('%s','00:00:00')
	);

INSERT INTO program (name,priority,startTime,endTime) VALUES
	('Selva rocio', 0,
 	strftime('%s', '20:00:00')-strftime('%s','00:00:00'),
 	strftime('%s', '22:00:00')-strftime('%s','00:00:00')
	);

UPDATE program SET maxStations=100 where maxStations is 1;
UPDATE program SET site=(SELECT id FROM site WHERE name=='Casa');
UPDATE program SET onOff=(SELECT id FROM webList WHERE grp=='onOff' AND key='on');
UPDATE program SET startMode=(SELECT id FROM webList WHERE grp=='evCel' AND key='clock');
UPDATE program SET stopMode=(SELECT id FROM webList WHERE grp=='evCel' AND key='clock');
UPDATE program SET action=(SELECT id FROM webList WHERE grp=='evAct' AND key=='dow') WHERE action IS NULL;


INSERT INTO pgmDOW -- All days of the week
	SELECT program.id,weblist.id FROM program INNER JOIN webList ON program.name=='Manual' AND grp=='dow';

INSERT INTO pgmDOW -- All days of the week
	SELECT program.id,weblist.id FROM program INNER JOIN webList ON program.name=='Selva rocio' AND grp=='dow';

INSERT INTO pgmDOW  -- Only Wednesday
	SELECT program.id,weblist.id FROM program INNER JOIN webList ON program.name=='Manual' AND grp=='dow' AND key=='wed';

-- SELECT * FROM program;
-- SELECT * FROM pgmDOW;

-- program stations association

INSERT INTO pgmStn (program,station,runTime) VALUES
   ((SELECT id FROM program WHERE name='Selva plantas'), (SELECT id FROM station WHERE station==71), 4*60)
  ,((SELECT id FROM program WHERE name='Selva goteo'),   (SELECT id FROM station WHERE station==72), 150*60)
  ,((SELECT id FROM program WHERE name='Selva rocio'),   (SELECT id FROM station WHERE station==73), 2*60)
  ;

UPDATE pgmStn SET mode=(SELECT id FROM webList WHERE grp=='pgm' AND key=='on') WHERE mode IS NULL;

-- SELECT * FROM programStation;

-- SELECT * FROM event;
