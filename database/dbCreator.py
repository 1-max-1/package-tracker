import sqlite3
with sqlite3.connect("./database/database.db") as con:
	with open("./database/database_schema.sql") as schemaFile:
		con.executescript(schemaFile.read())