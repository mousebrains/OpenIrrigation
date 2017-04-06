-- Add plant type information
-- source: http://www.kimberly.uidaho.edu/water/fao56/fao56.pdf
-- source: http://www.usbr.gov/pn/agrimet/cropcurves/crop_curves.html
-- source: http://ucanr.edu/sites/UrbanHort/Water_Use_of_Turfgrass_and_Landscape_Plant_Materials/Plant_Factor_or_Crop_Coefficient__What%E2%80%99s_the_difference/
INSERT INTO crop VALUES(NULL,"Annuals",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.8,0.8,0.8, -- Kc init,mid,end
                        0.5, -- Height (m)
                        0.15, -- root depth (m)
                        0.5, -- MAD
                        "UC Davis Extension" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Apples/Cherries/Pears, ground cover, killing frost",
                        "Mar", -- Plant date
                        30,50,130,30, -- Stage lengths in days
                        0.5,1.2,0.75, -- Kc init,mid,end
                        4, -- Height (m)
                        1.5, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Apples/Cherries/Pears, ground cover, no frost",
                        "Mar", -- Plant date
                        30,50,130,30, -- Stage lengths in days
                        0.8,1.2,0.85, -- Kc init,mid,end
                        4, -- Height (m)
                        1.5, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Apples/Cherries/Pears, no ground cover no frost",
                        "Mar", -- Plant date
                        30,50,130,30, -- Stage lengths in days
                        0.6,0.95,0.7, -- Kc init,mid,end
                        4, -- Height (m)
                        1.5, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Apples/Cherries/Pears, no ground cover, killing frost",
                        "Mar", -- Plant date
                        30,50,130,30, -- Stage lengths in days
                        0.45,0.95,0.7, -- Kc init,mid,end
                        4, -- Height (m)
                        1.5, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Artichokes",
                        "May", -- Plant date
                        40,40,250,30, -- Stage lengths in days
                        0.5,1,0.95, -- Kc init,mid,end
                        0.7, -- Height (m)
                        0.75, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Asparagus",
                        "Feb", -- Plant date
                        90,30,200,45, -- Stage lengths in days
                        0.5,0.95,0.3, -- Kc init,mid,end
                        0.5, -- Height (m)
                        0.91, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Bean, broad",
                        "May", -- Plant date
                        15,25,35,15, -- Stage lengths in days
                        0.5,1.15,1.1, -- Kc init,mid,end
                        0.8, -- Height (m)
                        0.46, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Beans, dry",
                        "Jun", -- Plant date
                        25,25,30,20, -- Stage lengths in days
                        0.4,1.15,0.35, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.46, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Beans, garbanzo",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.4,1.15,0.35, -- Kc init,mid,end
                        0.8, -- Height (m)
                        0.46, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Beans, green",
                        "Feb/Mar", -- Plant date
                        20,30,30,10, -- Stage lengths in days
                        0.5,1.05,0.9, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.46, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Beans, lima",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        NULL,NULL,NULL, -- Kc init,mid,end
                        NULL, -- Height (m)
                        0.46, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Beets",
                        "Apr/May", -- Plant date
                        15,25,20,10, -- Stage lengths in days
                        0.5,1.05,0.95, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.46, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Berries",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.3,1.05,0.5, -- Kc init,mid,end
                        1.5, -- Height (m)
                        0.91, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Broccoli",
                        "Sep", -- Plant date
                        35,45,40,15, -- Stage lengths in days
                        0.7,1.05,0.95, -- Kc init,mid,end
                        0.3, -- Height (m)
                        0.46, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Brussel Sprouts",
                        "Oct/Nov", -- Plant date
                        30,35,90,40, -- Stage lengths in days
                        0.7,1.05,0.95, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.46, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Cabbage",
                        "Sep", -- Plant date
                        40,60,50,15, -- Stage lengths in days
                        0.7,1.05,0.95, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.46, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Cantaloupe",
                        "June", -- Plant date
                        30,45,35,10, -- Stage lengths in days
                        0.5,0.85,0.6, -- Kc init,mid,end
                        0.3, -- Height (m)
                        1.2, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Carrots Feb/Mar",
                        "Feb/Mar", -- Plant date
                        30,40,60,20, -- Stage lengths in days
                        0.7,1.05,0.95, -- Kc init,mid,end
                        0.3, -- Height (m)
                        0.46, -- root depth (m)
                        0.35, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Cauliflower",
                        "Sep", -- Plant date
                        35,50,40,15, -- Stage lengths in days
                        0.7,1.05,0.95, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.46, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Celery ",
                        "Apr", -- Plant date
                        25,40,45,15, -- Stage lengths in days
                        0.7,1.05,1, -- Kc init,mid,end
                        0.6, -- Height (m)
                        0.3, -- root depth (m)
                        0.2, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Conifer Trees",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        1,1,1, -- Kc init,mid,end
                        10, -- Height (m)
                        1.25, -- root depth (m)
                        0.7, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Corn, Sweet",
                        "May/Jun", -- Plant date
                        20,25,25,10, -- Stage lengths in days
                        0.3,1.15,1.05, -- Kc init,mid,end
                        2, -- Height (m)
                        0.61, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Cucumber fresh",
                        "May", -- Plant date
                        20,30,50,15, -- Stage lengths in days
                        0.6,1,0.75, -- Kc init,mid,end
                        0.3, -- Height (m)
                        0.46, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Egg Plant",
                        "May/jun", -- Plant date
                        30,45,40,25, -- Stage lengths in days
                        0.6,1.05,0.9, -- Kc init,mid,end
                        0.8, -- Height (m)
                        0.46, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Garlic",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.7,1,0.7, -- Kc init,mid,end
                        0.3, -- Height (m)
                        0.46, -- root depth (m)
                        0.3, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Grapes, table",
                        "Apr", -- Plant date
                        30,60,40,80, -- Stage lengths in days
                        0.3,0.85,0.45, -- Kc init,mid,end
                        2, -- Height (m)
                        0.91, -- root depth (m)
                        0.35, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Green Gram/Cowpeas",
                        "Mar ", -- Plant date
                        20,30,30,20, -- Stage lengths in days
                        0.4,1.05,0.4, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.46, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Groundnut/Peanut",
                        "May/Jun", -- Plant date
                        35,45,35,25, -- Stage lengths in days
                        0.4,1.15,0.6, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.75, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Herbaceous Perennials",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.5,0.5,0.5, -- Kc init,mid,end
                        0.5, -- Height (m)
                        0.46, -- root depth (m)
                        0.5, -- MAD
                        "UC Davis Extension" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Hops",
                        "Apr", -- Plant date
                        25,40,80,10, -- Stage lengths in days
                        0.3,1.05,0.85, -- Kc init,mid,end
                        5, -- Height (m)
                        1.1, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Kiwi",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.4,1.05,1.05, -- Kc init,mid,end
                        3, -- Height (m)
                        1, -- root depth (m)
                        0.35, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Lentil",
                        "Apr", -- Plant date
                        20,30,60,40, -- Stage lengths in days
                        0.4,1.1,0.3, -- Kc init,mid,end
                        0.5, -- Height (m)
                        0.7, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Lettuce",
                        "Feb", -- Plant date
                        35,50,45,10, -- Stage lengths in days
                        0.7,1,0.95, -- Kc init,mid,end
                        0.3, -- Height (m)
                        0.15, -- root depth (m)
                        0.3, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Mint",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.6,1.15,1.1, -- Kc init,mid,end
                        0.7, -- Height (m)
                        0.6, -- root depth (m)
                        0.4, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Onions dry",
                        "Apr", -- Plant date
                        15,25,70,40, -- Stage lengths in days
                        0.7,1.05,0.75, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.45, -- root depth (m)
                        0.3, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Onions green",
                        "Apr/May", -- Plant date
                        25,30,10,5, -- Stage lengths in days
                        0.7,1,1, -- Kc init,mid,end
                        0.3, -- Height (m)
                        0.45, -- root depth (m)
                        0.3, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Onions seed",
                        "Sep", -- Plant date
                        20,45,165,45, -- Stage lengths in days
                        0.7,1.05,0.8, -- Kc init,mid,end
                        0.5, -- Height (m)
                        0.45, -- root depth (m)
                        0.35, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Parsnip",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.5,1.05,0.95, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.75, -- root depth (m)
                        0.4, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Peas, dry",
                        "May", -- Plant date
                        15,25,35,15, -- Stage lengths in days
                        0.5,1.15,0.3, -- Kc init,mid,end
                        0.5, -- Height (m)
                        0.46, -- root depth (m)
                        0.4, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Peas, fresh",
                        "May", -- Plant date
                        15,25,35,15, -- Stage lengths in days
                        0.5,1.15,1.1, -- Kc init,mid,end
                        0.5, -- Height (m)
                        0.46, -- root depth (m)
                        0.35, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Potato",
                        "Apr/May", -- Plant date
                        45,30,70,20, -- Stage lengths in days
                        0.5,1.15,0.75, -- Kc init,mid,end
                        0.6, -- Height (m)
                        0.46, -- root depth (m)
                        0.35, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Radishes",
                        "Mar/Apr", -- Plant date
                        5,10,15,5, -- Stage lengths in days
                        0.7,0.6,0.85, -- Kc init,mid,end
                        0.3, -- Height (m)
                        0.15, -- root depth (m)
                        0.3, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Soybeans",
                        "May", -- Plant date
                        20,35,60,25, -- Stage lengths in days
                        0.4,1.15,0.5, -- Kc init,mid,end
                        0.75, -- Height (m)
                        0.95, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Spinach",
                        "Sep/Oct", -- Plant date
                        20,20,25,5, -- Stage lengths in days
                        0.7,1,0.95, -- Kc init,mid,end
                        0.3, -- Height (m)
                        0.15, -- root depth (m)
                        0.2, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Stone fruit, ground cover, killing frost",
                        "Mar", -- Plant date
                        30,50,130,30, -- Stage lengths in days
                        0.5,1.15,0.9, -- Kc init,mid,end
                        3, -- Height (m)
                        1.5, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Stone fruit, ground cover, no frost",
                        "Mar", -- Plant date
                        30,50,130,30, -- Stage lengths in days
                        0.8,1.15,0.85, -- Kc init,mid,end
                        3, -- Height (m)
                        1.5, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Stone fruit, no ground cover, killing frost",
                        "Mar", -- Plant date
                        30,50,130,30, -- Stage lengths in days
                        0.45,0.9,0.65, -- Kc init,mid,end
                        3, -- Height (m)
                        1.5, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Stone fruit, no ground cover, no frost",
                        "Mar", -- Plant date
                        30,50,130,30, -- Stage lengths in days
                        0.55,0.9,0.65, -- Kc init,mid,end
                        3, -- Height (m)
                        1.5, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Strawberries",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.4,0.85,0.75, -- Kc init,mid,end
                        0.2, -- Height (m)
                        0.15, -- root depth (m)
                        0.2, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Summer Squash",
                        "May/Jun", -- Plant date
                        20,30,25,15, -- Stage lengths in days
                        0.5,0.95,0.75, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.61, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Sunflower",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.35,1.1,0.35, -- Kc init,mid,end
                        2, -- Height (m)
                        1.15, -- root depth (m)
                        0.45, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Sweet Melons",
                        "May", -- Plant date
                        25,35,40,20, -- Stage lengths in days
                        0.5,1.05,0.75, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.914, -- root depth (m)
                        0.4, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Sweet Peppers",
                        "Jun", -- Plant date
                        30,35,40,20, -- Stage lengths in days
                        0.6,1.05,0.9, -- Kc init,mid,end
                        0.7, -- Height (m)
                        0.46, -- root depth (m)
                        0.4, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Sweet Potato",
                        "Apri", -- Plant date
                        20,30,60,40, -- Stage lengths in days
                        0.5,1.15,0.65, -- Kc init,mid,end
                        0.4, -- Height (m)
                        1.25, -- root depth (m)
                        0.65, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Tomato",
                        "Apr/May", -- Plant date
                        30,40,45,30, -- Stage lengths in days
                        0.6,1.15,0.8, -- Kc init,mid,end
                        0.6, -- Height (m)
                        0.61, -- root depth (m)
                        0.4, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Trees/Shrubs",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.5,0.5,0.5, -- Kc init,mid,end
                        4, -- Height (m)
                        1, -- root depth (m)
                        0.5, -- MAD
                        "UC Davis Extension" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Turf, cool season",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.9,0.95,0.95, -- Kc init,mid,end
                        0.1, -- Height (m)
                        0.75, -- root depth (m)
                        0.4, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Turf, warm season",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.8,0.85,0.85, -- Kc init,mid,end
                        3, -- Height (m)
                        0.75, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Turnip/Rutabaga",
                        NULL, -- Plant date
                        NULL,NULL,NULL,NULL, -- Stage lengths in days
                        0.5,1.1,0.95, -- Kc init,mid,end
                        0.6, -- Height (m)
                        0.46, -- root depth (m)
                        0.5, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Watermelon",
                        "May", -- Plant date
                        20,30,30,30, -- Stage lengths in days
                        0.4,1,0.75, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.61, -- root depth (m)
                        0.4, -- MAD
                        "FAO 56" -- Comment
                        );
INSERT INTO crop VALUES(NULL,"Winter Squash",
                        "Jun", -- Plant date
                        25,35,35,25, -- Stage lengths in days
                        0.5,1,0.8, -- Kc init,mid,end
                        0.4, -- Height (m)
                        0.61, -- root depth (m)
                        0.35, -- MAD
                        "FAO 56" -- Comment
                        );
