CREATE TABLE 'users' (
'id' INTEGER NOT NULL  PRIMARY KEY AUTOINCREMENT,
'email' TEXT(254) NOT NULL ,
'password' TEXT(128) NOT NULL 
);

CREATE TABLE 'packages' (
'id' INTEGER NOT NULL  PRIMARY KEY AUTOINCREMENT,
'title' TEXT(50) DEFAULT NULL,
'trackingNumber' TEXT NOT NULL ,
'user_id' INTEGER NOT NULL  REFERENCES 'users' ('id'),
'last_updated' INTEGER(15) NOT NULL  DEFAULT 0
);

CREATE TABLE 'queue' (
'id' INTEGER NOT NULL  PRIMARY KEY AUTOINCREMENT,
'package_id' INTEGER NOT NULL  REFERENCES 'packages' ('id')
);

CREATE TABLE 'package_data' (
'id' INTEGER NOT NULL  PRIMARY KEY AUTOINCREMENT,
'package_id' INTEGER NOT NULL  REFERENCES 'packages' ('id'),
'date' TEXT(12) NOT NULL ,
'time' TEXT(8) NOT NULL ,
'data' TEXT NOT NULL 
);

CREATE TABLE 'pending_users' (
'id' INTEGER NOT NULL  PRIMARY KEY AUTOINCREMENT,
'email' TEXT(254) NOT NULL ,
'password' TEXT(128) NOT NULL ,
'verification_token' TEXT(32) NOT NULL ,
'time_created' INTEGER(15) NOT NULL 
);

CREATE TABLE 'password_resets' (
'user_id' INTEGER NOT NULL  PRIMARY KEY REFERENCES 'users' ('id'),
'token' TEXT(32) NOT NULL ,
'time_created' INTEGER(15) NOT NULL  DEFAULT 0
);