-- Add soil type information
-- source: https://nrcca.cals.cornell.edu/soil/CA2/CA0212.1-3.php
-- source: http://qcode.us/codes/sacramentocounty/view.php?topic=14-14_10-14_10_110
INSERT INTO soil (name, paw, infiltration, infiltrationSlope) VALUES
 ('Peat', 6.0*1000/12, 0.13*25.4, (0.13-0.03)/16*25.4),
 ('Clay', 2.4*1000/12, 0.13*25.4, (0.13-0.03)/16*25.4),
 ('Silty Clay',       2.6*1000/12, 0.19*25.4, (0.19-0.05)/16*25.4),
 ('Clay Loam',        2.2*1000/12, 0.25*25.4, (0.25-0.06)/16*25.4),
 ('Silt Loam',        4.2*1000/12, 0.50*25.4, (0.50-0.13)/16*25.4),
 ('Loam',             3.8*1000/12, 0.54*25.4, (0.54-0.14)/16*25.4),
 ('Sandy Loam',       2.4*1000/12, 0.75*25.4, (0.75-0.19)/16*25.4),
 ('Loamy Sand',       2.0*1000/12, 0.80*25.4, (0.80-0.22)/16*25.4),
 ('Fine Sand',        1.8*1000/12, 0.94*25.4, (0.94-0.24)/16*25.4),
 ('Coarse Sand',      0.9*1000/12, 1.25*25.4, (1.25-0.31)/16*25.4);
