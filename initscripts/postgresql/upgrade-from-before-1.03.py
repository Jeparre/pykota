#! /usr/bin/env python

# PyKota Print Quota Warning sender
#
# PyKota - Print Quotas for CUPS and LPRng
#
# (c) 2003, 2004, 2005, 2006, 2007 Jerome Alet <alet@librelogiciel.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# $Id: upgrade-from-before-1.03.py 3133 2007-01-17 22:19:42Z jerome $
#
# THIS IS AN UPGRADE SCRIPT FOR OLD PYKOTA DATABASES TO THE 1.03 VERSION
#

import sys
import os
try :
    import pg
except ImportError :    
    sys.stderr.write("The PyGreSQL Python module doesn't seem to be available. ABORTED.\n")
    sys.exit(-1)

def dump_old_database() :
    """Dumps the existing PyKota database to a file, to avoir loosing data.
    
       Returns 1 if dump is successfull, 0 if it isn't.
    """   
    pipeinput = os.popen("pg_dump -C -D -N -U postgres -f pykota-dump.sql pykota")
    dummy = pipeinput.read()
    return (pipeinput.close() is None) or 0

def create_new_database() :
    """Creates the empty database."""
    pipeinput = os.popen("psql -U postgres template1 <pykota-postgresql.sql")
    dummy = pipeinput.read()
    return (pipeinput.close() is None) or 0
    
def restore_original_database() :
    """Creates the empty database."""
    pipeinput = os.popen("psql -U postgres template1 <pykota-dump.sql")
    dummy = pipeinput.read()
    return (pipeinput.close() is None) or 0
    
def open_database(dbname="pykota") :
    """Returns the database object or None if we can't connect to it."""
    try :
        pykotadb = pg.connect(host="localhost", port=5432, dbname=dbname, user="postgres")
    except pg.error, msg :     
        sys.stderr.write("%s\n" % msg)
        sys.stderr.write("Unable to connect to the local PostgreSQL server.\nPlease modify the open_database() method in %s\nto connect to the correct PostgreSQL server\nand relaunch the script.\n" % sys.argv[0])
        return 
    else :    
        return pykotadb
        
        
def doQuote(field) :
    """Quotes a field for use as a string in SQL queries."""
    if type(field) == type(0) : # TODO : do something safer
        typ = "decimal"
    else :    
        typ = "text"
    return pg._quote(field, typ)
        
def main() :
    """Does the work."""
    
    # First we make a dump of the old database
    print "Dumping old database for safety...",
    if not dump_old_database() :
        sys.stderr.write("Error while dumping old database. ABORTED.\n")
        return -1
    print "Done."
        
    # Second we try to connect to it    
    print "Extracting datas from old database...", 
    db = open_database()
    if db is None :
        sys.stderr.write("Impossible to connect to old PyKota database. ABORTED.\nAre you sure you are upgrading an existing installation ?\n")
        return -1
    
    # Third we extract datas
    oldprinters = db.query("SELECT * FROM printers ORDER BY id;")
    oldusers = db.query("SELECT * FROM users ORDER BY id;")
    oldquotas = db.query("SELECT * FROM userpquota ORDER BY printerid, userid;")
    
    # Fourth close the database
    db.close()
    print "Done."
    
    # Fifth we delete the old database !
    answer = raw_input("The old database will be deleted for the upgrade to take place.\nAre you sure you want to continue (y/N) ? ")
    if answer[0:1].upper() != 'Y' :
        sys.stderr.write("User wants to stop now ! ABORTED.\n")
        return -1
    db = open_database("template1")
    if db is None :
        sys.stderr.write("Impossible to connect to database template1. ABORTED.\nPlease report to your Database administrator.\n")
        return -1
    try :
        db.query("DROP DATABASE pykota;")
    except pg.error, msg :
        sys.stderr.write("Impossible to delete old database. ABORTED.\n%s\n" % msg)
        db.close()
        return -1
    else :    
        db.close()
        
    # Sixth we create the new database
    print "Creating the new database...",
    if not create_new_database() :
        sys.stderr.write("impossible to create new database ! ABORTED.\n")
        return -1
    print "Done."
    
    # Seventh we restore old data
    print "Restoring old datas..."
    db = open_database()
    if db is None :
        sys.stderr.write("Impossible to connect to new PyKota database. ABORTED.\nOld database will be restored if possible.")
        print "An error occured, I'll try to restore the original database..."
        if not restore_original_database() :
            sys.stderr.write("Shit ! A double-error occured !!!\nPlease report problem to your database administrator.\n")
            sys.stderr.write("And file a bug report to alet@librelogiciel.com\n")
        else :    
            print "Done."
        return -1
    db.query("BEGIN;")    
    try :
        newprinters = {}
        for oldprinter in oldprinters.dictresult() :
            db.query("INSERT INTO printers (printername) VALUES (%s);" % doQuote(oldprinter["printername"]))
            newid = db.query("SELECT id FROM printers WHERE printername='%s';" % oldprinter["printername"]).dictresult()[0]["id"]
            newprinters[oldprinter["id"]] = newid
        newusers = {}    
        for olduser in oldusers.dictresult() :    
            db.query("INSERT INTO users (username) VALUES (%s);" % doQuote(olduser["username"]))
            newid = db.query("SELECT id FROM users WHERE username='%s';" % olduser["username"]).dictresult()[0]["id"]
            newusers[olduser["id"]] = newid
        for oldquota in oldquotas.dictresult() :   
            db.query("INSERT INTO userpquota (userid, printerid, pagecounter, lifepagecounter, softlimit, hardlimit, datelimit) VALUES (%s, %s, %s, %s, %s, %s, %s);" % 
                                              (doQuote(newusers[oldquota["userid"]]) , doQuote(newprinters[oldquota["printerid"]]), doQuote(oldquota["pagecounter"]), doQuote(oldquota["lifepagecounter"]), doQuote(oldquota["softlimit"]), doQuote(oldquota["hardlimit"]), doQuote(oldquota["datelimit"])))
    except pg.error, msg :    
        sys.stderr.write("ERROR : %s\nABORTED.\n" % msg)
        db.query("ROLLBACK;")
        db.close()    
        return -1
    except :    
        sys.stderr.write("Unknown error ! ABORTED.\n")
        db.query("ROLLBACK;")
        db.close()    
        return -1
    else :    
        db.query("COMMIT;")
        db.close()
    print "Done."
    print "NB : Last job on each printer was lost. This is normal !"
    return 0
    
if __name__ == "__main__" :
    sys.exit(main())
