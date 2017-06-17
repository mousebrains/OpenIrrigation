-- Add plant type information
-- source: http://www.kimberly.uidaho.edu/water/fao56/fao56.pdf
-- source: http://www.usbr.gov/pn/agrimet/cropcurves/crop_curves.html
-- source: http://ucanr.edu/sites/UrbanHort/Water_Use_of_Turfgrass_and_Landscape_Plant_Materials/Plant_Factor_or_Crop_Coefficient__What%E2%80%99s_the_difference/
INSERT INTO crop(name,plantDate,Lini,Ldev,Lmid,Llate,KcInit,KcMid,KcEnd,height,depth,MAD,notes)
	 VALUES
	('Annuals',
         NULL, -- Plant date
         NULL,NULL,NULL,NULL, -- Stage lengths in days
         0.8,0.8,0.8, -- Kc init,mid,end
         0.5, -- Height (m)
         0.15, -- root depth (m)
         0.5, -- MAD
         'UC Davis Extension' -- Comment
        ),
	('Apples/Cherries/Pears, ground cover, killing frost',
         date '2017-03-15', -- Plant date
         30,50,130,30, -- Stage lengths in days
         0.5,1.2,0.75, -- Kc init,mid,end
         4, -- Height (m)
         1.5, -- root depth (m)
         0.5, -- MAD
         'FAO 56' -- Comment
        ),
	('Apples/Cherries/Pears, ground cover, no frost',
         date '2017-03-15', -- Plant date
         30,50,130,30, -- Stage lengths in days
         0.8,1.2,0.85, -- Kc init,mid,end
         4, -- Height (m)
         1.5, -- root depth (m)
         0.5, -- MAD
         'FAO 56' -- Comment
        ),
	('Apples/Cherries/Pears, no ground cover no frost',
         date '2017-03-15', -- Plant date
         30,50,130,30, -- Stage lengths in days
         0.6,0.95,0.7, -- Kc init,mid,end
         4, -- Height (m)
         1.5, -- root depth (m)
         0.5, -- MAD
         'FAO 56' -- Comment
        ),
	('Apples/Cherries/Pears, no ground cover, killing frost',
	 date '2017-03-15', -- Plant date
	 30,50,130,30, -- Stage lengths in days
	 0.45,0.95,0.7, -- Kc init,mid,end
	 4, -- Height (m)
	 1.5, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Artichokes',
	 date '2017-05-15', -- Plant date
	 40,40,250,30, -- Stage lengths in days
	 0.5,1,0.95, -- Kc init,mid,end
	 0.7, -- Height (m)
	 0.75, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Asparagus',
	 date '2017-02-15', -- Plant date
	 90,30,200,45, -- Stage lengths in days
	 0.5,0.95,0.3, -- Kc init,mid,end
	 0.5, -- Height (m)
	 0.91, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Bean, broad',
	 date '2017-05-15', -- Plant date
	 15,25,35,15, -- Stage lengths in days
	 0.5,1.15,1.1, -- Kc init,mid,end
	 0.8, -- Height (m)
	 0.46, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Beans, dry',
	 date '2017-06-15', -- Plant date
	 25,25,30,20, -- Stage lengths in days
	 0.4,1.15,0.35, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.46, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Beans, garbanzo',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.4,1.15,0.35, -- Kc init,mid,end
	 0.8, -- Height (m)
	 0.46, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Beans, green',
	 date '2017-03-01', -- Plant date
	 20,30,30,10, -- Stage lengths in days
	 0.5,1.05,0.9, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.46, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Beans, lima',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 NULL,NULL,NULL, -- Kc init,mid,end
	 NULL, -- Height (m)
	 0.46, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Beets',
	 date '2017-05-01', -- Plant date
	 15,25,20,10, -- Stage lengths in days
	 0.5,1.05,0.95, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.46, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Berries',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.3,1.05,0.5, -- Kc init,mid,end
	 1.5, -- Height (m)
	 0.91, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Broccoli',
	 date '2017-09-15', -- Plant date
	 35,45,40,15, -- Stage lengths in days
	 0.7,1.05,0.95, -- Kc init,mid,end
	 0.3, -- Height (m)
	 0.46, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Brussel Sprouts',
	 date '2017-11-01', -- Plant date
	 30,35,90,40, -- Stage lengths in days
	 0.7,1.05,0.95, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.46, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Cabbage',
	 date '2017-09-15', -- Plant date
	 40,60,50,15, -- Stage lengths in days
	 0.7,1.05,0.95, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.46, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Cantaloupe',
	 date '2017-06-15', -- Plant date
	 30,45,35,10, -- Stage lengths in days
	 0.5,0.85,0.6, -- Kc init,mid,end
	 0.3, -- Height (m)
	 1.2, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Carrots Feb/Mar',
	 date '2017-03-01', -- Plant date
	 30,40,60,20, -- Stage lengths in days
	 0.7,1.05,0.95, -- Kc init,mid,end
	 0.3, -- Height (m)
	 0.46, -- root depth (m)
	 0.35, -- MAD
	 'FAO 56' -- Comment
	),
	('Cauliflower',
	 date '2017-09-15', -- Plant date
	 35,50,40,15, -- Stage lengths in days
	 0.7,1.05,0.95, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.46, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Celery ',
	 date '2017-04-15', -- Plant date
	 25,40,45,15, -- Stage lengths in days
	 0.7,1.05,1, -- Kc init,mid,end
	 0.6, -- Height (m)
	 0.3, -- root depth (m)
	 0.2, -- MAD
	 'FAO 56' -- Comment
	),
	('Conifer Trees',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 1,1,1, -- Kc init,mid,end
	 10, -- Height (m)
	 1.25, -- root depth (m)
	 0.7, -- MAD
	 'FAO 56' -- Comment
	),
	('Corn, Sweet',
	 date '2017-06-01', -- Plant date
	 20,25,25,10, -- Stage lengths in days
	 0.3,1.15,1.05, -- Kc init,mid,end
	 2, -- Height (m)
	 0.61, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Cucumber fresh',
	 date '2017-05-15', -- Plant date
	 20,30,50,15, -- Stage lengths in days
	 0.6,1,0.75, -- Kc init,mid,end
	 0.3, -- Height (m)
	 0.46, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Egg Plant',
	 date '2017-06-01', -- Plant date
	 30,45,40,25, -- Stage lengths in days
	 0.6,1.05,0.9, -- Kc init,mid,end
	 0.8, -- Height (m)
	 0.46, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Garlic',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.7,1,0.7, -- Kc init,mid,end
	 0.3, -- Height (m)
	 0.46, -- root depth (m)
	 0.3, -- MAD
	 'FAO 56' -- Comment
	),
	('Grapes, table',
	 date '2017-04-15', -- Plant date
	 30,60,40,80, -- Stage lengths in days
	 0.3,0.85,0.45, -- Kc init,mid,end
	 2, -- Height (m)
	 0.91, -- root depth (m)
	 0.35, -- MAD
	 'FAO 56' -- Comment
	),
	('Green Gram/Cowpeas',
	 date '2017-03-15', -- Plant date
	 20,30,30,20, -- Stage lengths in days
	 0.4,1.05,0.4, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.46, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Groundnut/Peanut',
	 date '2017-06-01', -- Plant date
	 35,45,35,25, -- Stage lengths in days
	 0.4,1.15,0.6, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.75, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Herbaceous Perennials',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.5,0.5,0.5, -- Kc init,mid,end
	 0.5, -- Height (m)
	 0.46, -- root depth (m)
	 0.5, -- MAD
	 'UC Davis Extension' -- Comment
	),
	('Hops',
	 date '2017-04-15', -- Plant date
	 25,40,80,10, -- Stage lengths in days
	 0.3,1.05,0.85, -- Kc init,mid,end
	 5, -- Height (m)
	 1.1, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Kiwi',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.4,1.05,1.05, -- Kc init,mid,end
	 3, -- Height (m)
	 1, -- root depth (m)
	 0.35, -- MAD
	 'FAO 56' -- Comment
	),
	('Lentil',
	 date '2017-04-15', -- Plant date
	 20,30,60,40, -- Stage lengths in days
	 0.4,1.1,0.3, -- Kc init,mid,end
	 0.5, -- Height (m)
	 0.7, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Lettuce',
	 date '2017-02-15', -- Plant date
	 35,50,45,10, -- Stage lengths in days
	 0.7,1,0.95, -- Kc init,mid,end
	 0.3, -- Height (m)
	 0.15, -- root depth (m)
	 0.3, -- MAD
	 'FAO 56' -- Comment
	),
	('Mint',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.6,1.15,1.1, -- Kc init,mid,end
	 0.7, -- Height (m)
	 0.6, -- root depth (m)
	 0.4, -- MAD
	 'FAO 56' -- Comment
	),
	('Onions dry',
	 date '2017-04-15', -- Plant date
	 15,25,70,40, -- Stage lengths in days
	 0.7,1.05,0.75, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.45, -- root depth (m)
	 0.3, -- MAD
	 'FAO 56' -- Comment
	),
	('Onions green',
	 date '2017-05-01', -- Plant date
	 25,30,10,5, -- Stage lengths in days
	 0.7,1,1, -- Kc init,mid,end
	 0.3, -- Height (m)
	 0.45, -- root depth (m)
	 0.3, -- MAD
	 'FAO 56' -- Comment
	),
	('Onions seed',
	 date '2017-09-15', -- Plant date
	 20,45,165,45, -- Stage lengths in days
	 0.7,1.05,0.8, -- Kc init,mid,end
	 0.5, -- Height (m)
	 0.45, -- root depth (m)
	 0.35, -- MAD
	 'FAO 56' -- Comment
	),
	('Parsnip',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.5,1.05,0.95, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.75, -- root depth (m)
	 0.4, -- MAD
	 'FAO 56' -- Comment
	),
	('Peas, dry',
	 date '2017-05-15', -- Plant date
	 15,25,35,15, -- Stage lengths in days
	 0.5,1.15,0.3, -- Kc init,mid,end
	 0.5, -- Height (m)
	 0.46, -- root depth (m)
	 0.4, -- MAD
	 'FAO 56' -- Comment
	),
	('Peas, fresh',
	 date '2017-05-15', -- Plant date
	 15,25,35,15, -- Stage lengths in days
	 0.5,1.15,1.1, -- Kc init,mid,end
	 0.5, -- Height (m)
	 0.46, -- root depth (m)
	 0.35, -- MAD
	 'FAO 56' -- Comment
	),
	('Potato',
	 date '2017-05-01', -- Plant date
	 45,30,70,20, -- Stage lengths in days
	 0.5,1.15,0.75, -- Kc init,mid,end
	 0.6, -- Height (m)
	 0.46, -- root depth (m)
	 0.35, -- MAD
	 'FAO 56' -- Comment
	),
	('Radishes',
	 date '2017-04-01', -- Plant date
	 5,10,15,5, -- Stage lengths in days
	 0.7,0.6,0.85, -- Kc init,mid,end
	 0.3, -- Height (m)
	 0.15, -- root depth (m)
	 0.3, -- MAD
	 'FAO 56' -- Comment
	),
	('Soybeans',
	 date '2017-05-15', -- Plant date
	 20,35,60,25, -- Stage lengths in days
	 0.4,1.15,0.5, -- Kc init,mid,end
	 0.75, -- Height (m)
	 0.95, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Spinach',
	 date '2017-10-01', -- Plant date
	 20,20,25,5, -- Stage lengths in days
	 0.7,1,0.95, -- Kc init,mid,end
	 0.3, -- Height (m)
	 0.15, -- root depth (m)
	 0.2, -- MAD
	 'FAO 56' -- Comment
	),
	('Stone fruit, ground cover, killing frost',
	 date '2017-03-15', -- Plant date
	 30,50,130,30, -- Stage lengths in days
	 0.5,1.15,0.9, -- Kc init,mid,end
	 3, -- Height (m)
	 1.5, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Stone fruit, ground cover, no frost',
	 date '2017-03-15', -- Plant date
	 30,50,130,30, -- Stage lengths in days
	 0.8,1.15,0.85, -- Kc init,mid,end
	 3, -- Height (m)
	 1.5, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Stone fruit, no ground cover, killing frost',
	 date '2017-03-15', -- Plant date
	 30,50,130,30, -- Stage lengths in days
	 0.45,0.9,0.65, -- Kc init,mid,end
	 3, -- Height (m)
	 1.5, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Stone fruit, no ground cover, no frost',
	 date '2017-03-15', -- Plant date
	 30,50,130,30, -- Stage lengths in days
	 0.55,0.9,0.65, -- Kc init,mid,end
	 3, -- Height (m)
	 1.5, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Strawberries',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.4,0.85,0.75, -- Kc init,mid,end
	 0.2, -- Height (m)
	 0.15, -- root depth (m)
	 0.2, -- MAD
	 'FAO 56' -- Comment
	),
	('Summer Squash',
	 date '2017-06-01', -- Plant date
	 20,30,25,15, -- Stage lengths in days
	 0.5,0.95,0.75, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.61, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Sunflower',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.35,1.1,0.35, -- Kc init,mid,end
	 2, -- Height (m)
	 1.15, -- root depth (m)
	 0.45, -- MAD
	 'FAO 56' -- Comment
	),
	('Sweet Melons',
	 date '2017-05-15', -- Plant date
	 25,35,40,20, -- Stage lengths in days
	 0.5,1.05,0.75, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.914, -- root depth (m)
	 0.4, -- MAD
	 'FAO 56' -- Comment
	),
	('Sweet Peppers',
	 date '2017-06-15', -- Plant date
	 30,35,40,20, -- Stage lengths in days
	 0.6,1.05,0.9, -- Kc init,mid,end
	 0.7, -- Height (m)
	 0.46, -- root depth (m)
	 0.4, -- MAD
	 'FAO 56' -- Comment
	),
	('Sweet Potato',
	 date '2017-04-15', -- Plant date
	 20,30,60,40, -- Stage lengths in days
	 0.5,1.15,0.65, -- Kc init,mid,end
	 0.4, -- Height (m)
	 1.25, -- root depth (m)
	 0.65, -- MAD
	 'FAO 56' -- Comment
	),
	('Tomato',
	 date '2017-05-01', -- Plant date
	 30,40,45,30, -- Stage lengths in days
	 0.6,1.15,0.8, -- Kc init,mid,end
	 0.6, -- Height (m)
	 0.61, -- root depth (m)
	 0.4, -- MAD
	 'FAO 56' -- Comment
	),
	('Trees/Shrubs',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.5,0.5,0.5, -- Kc init,mid,end
	 4, -- Height (m)
	 1, -- root depth (m)
	 0.5, -- MAD
	 'UC Davis Extension' -- Comment
	),
	('Turf, cool season',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.9,0.95,0.95, -- Kc init,mid,end
	 0.1, -- Height (m)
	 0.75, -- root depth (m)
	 0.4, -- MAD
	 'FAO 56' -- Comment
	),
	('Turf, warm season',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.8,0.85,0.85, -- Kc init,mid,end
	 3, -- Height (m)
	 0.75, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Turnip/Rutabaga',
	 NULL, -- Plant date
	 NULL,NULL,NULL,NULL, -- Stage lengths in days
	 0.5,1.1,0.95, -- Kc init,mid,end
	 0.6, -- Height (m)
	 0.46, -- root depth (m)
	 0.5, -- MAD
	 'FAO 56' -- Comment
	),
	('Watermelon',
	 date '2017-05-15', -- Plant date
	 20,30,30,30, -- Stage lengths in days
	 0.4,1,0.75, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.61, -- root depth (m)
	 0.4, -- MAD
	 'FAO 56' -- Comment
	),
	('Winter Squash',
	 date '2017-06-15', -- Plant date
	 25,35,35,25, -- Stage lengths in days
	 0.5,1,0.8, -- Kc init,mid,end
	 0.4, -- Height (m)
	 0.61, -- root depth (m)
	 0.35, -- MAD
	 'FAO 56' -- Comment
	);
