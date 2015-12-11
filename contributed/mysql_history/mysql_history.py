#!/usr/bin/env python

import MySQLdb, pwd, string, sys
from ConfigParser import *
from os import environ

try:
	pykotauser = pwd.getpwnam("pykota")
except KeyError:
	pykotauser = None
	confdir = "/etc/pykota"
else:
	confdir = pykotauser[5]

configfile = confdir + "/mysql_history.conf"

config = ConfigParser()
config.read(configfile)
mysqlserver = config.get("default", "server").strip()
mysqluser = config.get("default", "username").strip()
mysqlpass = config.get("default", "password").strip()
mysqldb = config.get("default", "database").strip()
mysqltable = config.get("default", "table").strip()

try:
	db = MySQLdb.connect(mysqlserver,mysqluser,mysqlpass,mysqldb)
except:
	print "Unable to connect to MySQL database."
	sys.exit(1)

cursor = db.cursor()

cursor.execute("""INSERT INTO %s (id, jobid, username, printername, pgroups, 
	jobsize, jobprice, action, title, copies, options, 
	printeroriginatinghostname, md5sum, precomputedjobsize, 
	precomputedjobprice) VALUES 
	("", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s")""" % 
	(mysqltable, environ['PYKOTAJOBID'], environ['PYKOTAUSERNAME'], environ['PYKOTAPRINTERNAME'], environ['PYKOTAPGROUPS'], environ['PYKOTAJOBSIZE'],environ['PYKOTAJOBPRICE'], environ['PYKOTAACTION'], environ['PYKOTATITLE'],environ['PYKOTACOPIES'],environ['PYKOTAOPTIONS'],environ['PYKOTAJOBORIGINATINGHOSTNAME'],environ['PYKOTAMD5SUM'],environ['PYKOTAPRECOMPUTEDJOBSIZE'],environ['PYKOTAPRECOMPUTEDJOBPRICE']))

cursor.close()

# vim:tabstop=4
