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
# $Id: pgstorage.py 3500 2009-05-20 08:27:33Z jerome $
#
#

"""This module defines a class to access to a PostgreSQL database backend."""

import time
from types import StringType

from pykota.storage import PyKotaStorageError, BaseStorage
from pykota.storages.sql import SQLStorage

try :
    import pg
except ImportError :
    import sys
    # TODO : to translate or not to translate ?
    raise PyKotaStorageError, "This python version (%s) doesn't seem to have the PygreSQL module installed correctly." % sys.version.split()[0]
else :
    try :
        PGError = pg.Error
    except AttributeError :
        PGError = pg.error

class Storage(BaseStorage, SQLStorage) :
    def __init__(self, pykotatool, host, dbname, user, passwd) :
        """Opens the PostgreSQL database connection."""
        BaseStorage.__init__(self, pykotatool)
        try :
            (host, port) = host.split(":")
            port = int(port)
        except ValueError :
            port = 5432         # Use PostgreSQL's default tcp/ip port (5432).

        self.tool.logdebug("Trying to open database (host=%s, port=%s, dbname=%s, user=%s)..." % (host, port, dbname, user))
        try :
            self.database = pg.DB(host=host, port=port, dbname=dbname, user=user, passwd=passwd)
        except PGError, msg :
            msg = "%(msg)s --- the most probable cause of your problem is that PostgreSQL is down, or doesn't accept incoming connections because you didn't configure it as explained in PyKota's documentation." % locals()
            raise PGError, msg
        self.closed = 0
        try :
            self.database.query("SET CLIENT_ENCODING TO 'UTF-8';")
        except PGError, msg :
            self.tool.logdebug("Impossible to set database client encoding to UTF-8 : %s" % msg)
        self.tool.logdebug("Database opened (host=%s, port=%s, dbname=%s, user=%s)" % (host, port, dbname, user))

    def close(self) :
        """Closes the database connection."""
        if not self.closed :
            self.database.close()
            self.closed = 1
            self.tool.logdebug("Database closed.")

    def beginTransaction(self) :
        """Starts a transaction."""
        self.before = time.time()
        self.database.query("BEGIN;")
        self.tool.logdebug("Transaction begins...")

    def commitTransaction(self) :
        """Commits a transaction."""
        self.database.query("COMMIT;")
        after = time.time()
        self.tool.logdebug("Transaction committed.")
        #self.tool.logdebug("Transaction duration : %.4f seconds" % (after - self.before))

    def rollbackTransaction(self) :
        """Rollbacks a transaction."""
        self.database.query("ROLLBACK;")
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
            result = self.database.query(query)
        except PGError, msg :
            raise PyKotaStorageError, str(msg)
        else :
            after = time.time()
            #self.tool.logdebug("Query Duration : %.4f seconds" % (after - before))
            return result

    def doSearch(self, query) :
        """Does a search query."""
        result = self.doRawSearch(query)
        if (result is not None) and (result.ntuples() > 0) :
            return result.dictresult()

    def doModify(self, query) :
        """Does a (possibly multiple) modify query."""
        query = query.strip()
        if not query.endswith(';') :
            query += ';'
        try :
            before = time.time()
            self.tool.logdebug("QUERY : %s" % query)
            result = self.database.query(query)
        except PGError, msg :
            self.tool.logdebug("Query failed : %s" % repr(msg))
            raise PyKotaStorageError, str(msg)
        else :
            after = time.time()
            #self.tool.logdebug("Query Duration : %.4f seconds" % (after - before))
            return result

    def doQuote(self, field) :
        """Quotes a field for use as a string in SQL queries."""
        return self.database.adapter.adapt_inline(field)

    def prepareRawResult(self, result) :
        """Prepares a raw result by including the headers."""
        if result.ntuples() > 0 :
            entries = [result.listfields()]
            entries.extend(result.getresult())
            nbfields = len(entries[0])
            for i in range(1, len(entries)) :
                fields = list(entries[i])
                for j in range(nbfields) :
                    field = fields[j]
                    if type(field) == StringType :
                        fields[j] = self.databaseToUserCharset(field)
                entries[i] = tuple(fields)
            return entries

