# PyKota
# -*- coding: ISO-8859-15 -*-
#
# PyKota : Print Quotas for CUPS and LPRng
#
# (c) 2003, 2004, 2005, 2006, 2007 Jerome Alet <alet@librelogiciel.com>
# (c) 2005, 2006 Matt Hyclak <hyclak@math.ohiou.edu>
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
# $Id: mysqlstorage.py 3184 2007-05-30 20:29:50Z jerome $
#
#

"""This module defines a class to access to a MySQL database backend."""

import time

from pykota.storage import PyKotaStorageError, BaseStorage
from pykota.storages.sql import SQLStorage

try :
    import MySQLdb
except ImportError :    
    import sys
    # TODO : to translate or not to translate ?
    raise PyKotaStorageError, "This python version (%s) doesn't seem to have the MySQL module installed correctly." % sys.version.split()[0]

class Storage(BaseStorage, SQLStorage) :
    def __init__(self, pykotatool, host, dbname, user, passwd) :
        """Opens the MySQL database connection."""
        BaseStorage.__init__(self, pykotatool)
        try :
            (host, port) = host.split(":")
            port = int(port)
        except ValueError :    
            port = 3306           # Use the default MySQL port
        
        self.tool.logdebug("Trying to open database (host=%s, port=%s, dbname=%s, user=%s)..." % (host, port, dbname, user))
        try :
            self.database = MySQLdb.connect(host=host, port=port, db=dbname, user=user, passwd=passwd, charset="utf8")
        except TypeError :    
            self.tool.logdebug("'charset' argument not allowed with this version of python-mysqldb, retrying without...")
            self.database = MySQLdb.connect(host=host, port=port, db=dbname, user=user, passwd=passwd)
            
        try :
            self.database.autocommit(1)
        except AttributeError :    
            raise PyKotaStorageError, _("Your version of python-mysqldb is too old. Please install a newer release.")
        self.cursor = self.database.cursor()
        self.cursor.execute("SET NAMES 'utf8';")
        self.cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED;") # Same as PostgreSQL and Oracle's default
        self.closed = 0
        self.tool.logdebug("Database opened (host=%s, port=%s, dbname=%s, user=%s)" % (host, port, dbname, user))
            
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
        self.database.commit()
        after = time.time()
        self.tool.logdebug("Transaction committed.")
        #self.tool.logdebug("Transaction duration : %.4f seconds" % (after - self.before))
        
    def rollbackTransaction(self) :     
        """Rollbacks a transaction."""
        self.database.rollback()
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
            # This returns a list of lists. Integers are returned as longs.
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
                    except:
                        pass
                    rowdict[fields[field]] = value
                rows.append(rowdict)
            # returns a list of dicts
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
            newfield = self.database.string_literal(field)
            try :
                return newfield.encode("UTF-8")
            except :    
                return newfield
        else :
            self.tool.logdebug("WARNING: field has no type, returning NULL")
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
