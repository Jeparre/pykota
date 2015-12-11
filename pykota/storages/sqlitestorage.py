# PyKota
# -*- coding: ISO-8859-15 -*-
#
# PyKota : Print Quotas for CUPS and LPRng
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
# $Id: sqlitestorage.py 3184 2007-05-30 20:29:50Z jerome $
#
#

"""This module defines a class to access to a SQLite database backend."""

import time

from pykota.storage import PyKotaStorageError, BaseStorage
from pykota.storages.sql import SQLStorage

try :
    from pysqlite2 import dbapi2 as sqlite
except ImportError :    
    import sys
    # TODO : to translate or not to translate ?
    raise PyKotaStorageError, "This python version (%s) doesn't seem to have the PySQLite module installed correctly." % sys.version.split()[0]

class Storage(BaseStorage, SQLStorage) :
    def __init__(self, pykotatool, host, dbname, user, passwd) :
        """Opens the SQLite database connection."""
        BaseStorage.__init__(self, pykotatool)
        
        self.tool.logdebug("Trying to open database (dbname=%s)..." % dbname)
        self.database = sqlite.connect(dbname, isolation_level=None)
        self.cursor = self.database.cursor()
        self.closed = 0
        self.tool.logdebug("Database opened (dbname=%s)" % dbname)
            
    def close(self) :    
        """Closes the database connection."""
        if not self.closed :
            self.cursor.close()
            self.database.close()
            self.closed = 1
            self.tool.logdebug("Database closed.")
        
    def beginTransaction(self) :    
        """Starts a transaction."""
        self.before = time.time()
        self.cursor.execute("BEGIN;")
        self.tool.logdebug("Transaction begins...")
        
    def commitTransaction(self) :    
        """Commits a transaction."""
        self.cursor.execute("COMMIT;")
        after = time.time()
        self.tool.logdebug("Transaction committed.")
        #self.tool.logdebug("Transaction duration : %.4f seconds" % (after - self.before))
        
    def rollbackTransaction(self) :     
        """Rollbacks a transaction."""
        self.cursor.execute("ROLLBACK;")
        after = time.time()
        self.tool.logdebug("Transaction aborted.")
        #self.tool.logdebug("Transaction duration : %.4f seconds" % (after - self.before))
        
    def doRawSearch(self, query) :
        """Does a raw search query."""
        query = query.strip()    
        if not query.endswith(';') :    
            query += ';'
        try :
            before = time.time()
            self.tool.logdebug("QUERY : %s" % query)
            self.cursor.execute(query)
        except self.database.Error, msg :    
            raise PyKotaStorageError, str(msg)
        else :    
            result = self.cursor.fetchall()
            after = time.time()
            #self.tool.logdebug("Query Duration : %.4f seconds" % (after - before))
            return result
            
    def doSearch(self, query) :        
        """Does a search query."""
        result = self.doRawSearch(query)
        if result : 
            rows = []
            fields = {}
            for i in range(len(self.cursor.description)) :
                fields[i] = self.cursor.description[i][0]
            for row in result :    
                rowdict = {}
                for field in fields.keys() :
                    value = row[field]
                    try :
                        value = value.encode("UTF-8")
                    except :
                        pass
                    rowdict[fields[field]] = value
                rows.append(rowdict)    
            return rows    
        
    def doModify(self, query) :
        """Does a (possibly multiple) modify query."""
        query = query.strip()    
        if not query.endswith(';') :    
            query += ';'
        try :
            before = time.time()
            self.tool.logdebug("QUERY : %s" % query)
            self.cursor.execute(query)
        except self.database.Error, msg :    
            self.tool.logdebug("Query failed : %s" % repr(msg))
            raise PyKotaStorageError, str(msg)
        else :    
            after = time.time()
            #self.tool.logdebug("Query Duration : %.4f seconds" % (after - before))
            
    def doQuote(self, field) :
        """Quotes a field for use as a string in SQL queries."""
        if type(field) == type(0.0) : 
            return field
        elif type(field) == type(0) :    
            return field
        elif type(field) == type(0L) :    
            return field
        elif field is not None :
            return ("'%s'" % field.replace("'", "''")).decode("UTF-8")
        else :     
            return "NULL"
            
    def prepareRawResult(self, result) :
        """Prepares a raw result by including the headers."""
        if result :
            entries = [tuple([f[0] for f in self.cursor.description])]
            for entry in result :    
                row = []
                for value in entry :
                    try :
                        value = value.encode("UTF-8")
                    except :
                        pass
                    row.append(value)
                entries.append(tuple(row))    
            return entries   
        
