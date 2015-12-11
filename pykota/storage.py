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
# $Id: storage.py 3444 2008-10-26 19:39:19Z jerome $
#
#

"""This module is the database abstraction layer for PyKota."""

import os
import imp
from mx import DateTime

class PyKotaStorageError(Exception):
    """An exception for database related stuff."""
    def __init__(self, message = ""):
        self.message = message
        Exception.__init__(self, message)
    def __repr__(self):
        return self.message
    __str__ = __repr__


class StorageObject :
    """Object present in the database."""
    def __init__(self, parent) :
        "Initialize minimal data."""
        self.parent = parent
        self.ident = None
        self.Description = None
        self.isDirty = False
        self.Exists = False

    def setDescription(self, description=None) :
        """Sets the object's description."""
        if description is not None :
            self.Description = str(description)
            self.isDirty = True

    def save(self) :
        """Saves the object to the database."""
        if self.isDirty :
            getattr(self.parent, "save%s" % self.__class__.__name__[7:])(self)
            self.isDirty = False


class StorageUser(StorageObject) :
    """User class."""
    def __init__(self, parent, name) :
        StorageObject.__init__(self, parent)
        self.Name = name
        self.LimitBy = None
        self.AccountBalance = None
        self.LifeTimePaid = None
        self.Email = None
        self.OverCharge = 1.0
        self.Payments = [] # TODO : maybe handle this smartly for SQL, for now just don't retrieve them
        self.PaymentsBacklog = []

    def consumeAccountBalance(self, amount) :
        """Consumes an amount of money from the user's account balance."""
        self.parent.decreaseUserAccountBalance(self, amount)
        self.AccountBalance = float(self.AccountBalance or 0.0) - amount

    def setAccountBalance(self, balance, lifetimepaid, comment="") :
        """Sets the user's account balance in case he pays more money."""
        diff = float(lifetimepaid or 0.0) - float(self.LifeTimePaid or 0.0)
        self.AccountBalance = balance
        self.LifeTimePaid = lifetimepaid
        if diff :
            self.PaymentsBacklog.append((diff, comment))
        self.isDirty = True

    def save(self) :
        """Saves an user and flush its payments backlog."""
        for (value, comment) in self.PaymentsBacklog :
            self.parent.writeNewPayment(self, value, comment)
        self.PaymentsBacklog = []
        StorageObject.save(self)

    def setLimitBy(self, limitby) :
        """Sets the user's limiting factor."""
        try :
            limitby = limitby.lower()
        except AttributeError :
            limitby = "quota"
        if limitby in ["quota", "balance", \
                       "noquota", "noprint", "nochange"] :
            self.LimitBy = limitby
            self.isDirty = True

    def setOverChargeFactor(self, factor) :
        """Sets the user's overcharging coefficient."""
        self.OverCharge = factor
        self.isDirty = True

    def setEmail(self, email) :
        """Sets the user's email address."""
        self.Email = email
        self.isDirty = True

    def delete(self) :
        """Deletes an user from the database."""
        self.parent.deleteUser(self)
        self.parent.flushEntry("USERS", self.Name)
        if self.parent.usecache :
            for (k, v) in self.parent.caches["USERPQUOTAS"].items() :
                if v.User.Name == self.Name :
                    self.parent.flushEntry("USERPQUOTAS", "%s@%s" % (v.User.Name, v.Printer.Name))
        self.Exists = False
        self.isDirty = False

    def refund(self, amount, reason) :
        """Refunds a number of credits to an user."""
        self.consumeAccountBalance(-amount)
        self.parent.writeNewPayment(self, -amount, reason)


class StorageGroup(StorageObject) :
    """User class."""
    def __init__(self, parent, name) :
        StorageObject.__init__(self, parent)
        self.Name = name
        self.LimitBy = None
        self.AccountBalance = None
        self.LifeTimePaid = None

    def setLimitBy(self, limitby) :
        """Sets the user's limiting factor."""
        try :
            limitby = limitby.lower()
        except AttributeError :
            limitby = "quota"
        if limitby in ["quota", "balance", "noquota"] :
            self.LimitBy = limitby
            self.isDirty = True

    def addUserToGroup(self, user) :
        """Adds an user to an users group."""
        self.parent.addUserToGroup(user, self)

    def delUserFromGroup(self, user) :
        """Removes an user from an users group."""
        self.parent.delUserFromGroup(user, self)

    def delete(self) :
        """Deletes a group from the database."""
        self.parent.deleteGroup(self)
        self.parent.flushEntry("GROUPS", self.Name)
        if self.parent.usecache :
            for (k, v) in self.parent.caches["GROUPPQUOTAS"].items() :
                if v.Group.Name == self.Name :
                    self.parent.flushEntry("GROUPPQUOTAS", "%s@%s" % (v.Group.Name, v.Printer.Name))
        self.Exists = False
        self.isDirty = False


class StoragePrinter(StorageObject) :
    """Printer class."""
    def __init__(self, parent, name) :
        StorageObject.__init__(self, parent)
        self.Name = name
        self.PricePerPage = None
        self.PricePerJob = None
        self.MaxJobSize = None
        self.PassThrough = None

    def __getattr__(self, name) :
        """Delays data retrieval until it's really needed."""
        if name == "LastJob" :
            self.LastJob = self.parent.getPrinterLastJob(self)
            self.parent.tool.logdebug("Lazy retrieval of last job for printer %s" % self.Name)
            return self.LastJob
        elif name == "Coefficients" :
            self.Coefficients = self.parent.tool.config.getPrinterCoefficients(self.Name)
            self.parent.tool.logdebug("Lazy retrieval of coefficients for printer %s : %s" % (self.Name, self.Coefficients))
            return self.Coefficients
        else :
            raise AttributeError, name

    def addJobToHistory(self, jobid, user, pagecounter, action, jobsize=None, jobprice=None, filename=None, title=None, copies=None, options=None, clienthost=None, jobsizebytes=None, jobmd5sum=None, jobpages=None, jobbilling=None, precomputedsize=None, precomputedprice=None) :
        """Adds a job to the printer's history."""
        self.parent.writeJobNew(self, user, jobid, pagecounter, action, jobsize, jobprice, filename, title, copies, options, clienthost, jobsizebytes, jobmd5sum, jobpages, jobbilling, precomputedsize, precomputedprice)
        # TODO : update LastJob object ? Probably not needed.

    def addPrinterToGroup(self, printer) :
        """Adds a printer to a printer group."""
        if (printer not in self.parent.getParentPrinters(self)) and (printer.ident != self.ident) :
            self.parent.writePrinterToGroup(self, printer)
            # TODO : reset cached value for printer parents, or add new parent to cached value

    def delPrinterFromGroup(self, printer) :
        """Deletes a printer from a printer group."""
        self.parent.removePrinterFromGroup(self, printer)
        # TODO : reset cached value for printer parents, or add new parent to cached value

    def setPrices(self, priceperpage = None, priceperjob = None) :
        """Sets the printer's prices."""
        if priceperpage is None :
            priceperpage = self.PricePerPage or 0.0
        else :
            self.PricePerPage = float(priceperpage)
        if priceperjob is None :
            priceperjob = self.PricePerJob or 0.0
        else :
            self.PricePerJob = float(priceperjob)
        self.isDirty = True

    def setPassThrough(self, passthrough) :
        """Sets the printer's passthrough mode."""
        self.PassThrough = passthrough
        self.isDirty = True

    def setMaxJobSize(self, maxjobsize) :
        """Sets the printer's maximal job size."""
        self.MaxJobSize = maxjobsize
        self.isDirty = True

    def delete(self) :
        """Deletes a printer from the database."""
        self.parent.deletePrinter(self)
        self.parent.flushEntry("PRINTERS", self.Name)
        if self.parent.usecache :
            for (k, v) in self.parent.caches["USERPQUOTAS"].items() :
                if v.Printer.Name == self.Name :
                    self.parent.flushEntry("USERPQUOTAS", "%s@%s" % (v.User.Name, v.Printer.Name))
            for (k, v) in self.parent.caches["GROUPPQUOTAS"].items() :
                if v.Printer.Name == self.Name :
                    self.parent.flushEntry("GROUPPQUOTAS", "%s@%s" % (v.Group.Name, v.Printer.Name))
        self.Exists = False
        self.isDirty = False


class StorageUserPQuota(StorageObject) :
    """User Print Quota class."""
    def __init__(self, parent, user, printer) :
        StorageObject.__init__(self, parent)
        self.User = user
        self.Printer = printer
        self.PageCounter = None
        self.LifePageCounter = None
        self.SoftLimit = None
        self.HardLimit = None
        self.DateLimit = None
        self.WarnCount = None
        self.MaxJobSize = None

    def __getattr__(self, name) :
        """Delays data retrieval until it's really needed."""
        if name == "ParentPrintersUserPQuota" :
            self.ParentPrintersUserPQuota = (self.User.Exists and self.Printer.Exists and self.parent.getParentPrintersUserPQuota(self)) or []
            return self.ParentPrintersUserPQuota
        else :
            raise AttributeError, name

    def setDateLimit(self, datelimit) :
        """Sets the date limit for this quota."""
        datelimit = DateTime.ISO.ParseDateTime(str(datelimit)[:19])
        date = "%04i-%02i-%02i %02i:%02i:%02i" % (datelimit.year, datelimit.month, datelimit.day, datelimit.hour, datelimit.minute, datelimit.second)
        self.parent.writeUserPQuotaDateLimit(self, date)
        self.DateLimit = date

    def setLimits(self, softlimit, hardlimit) :
        """Sets the soft and hard limit for this quota."""
        self.SoftLimit = softlimit
        self.HardLimit = hardlimit
        self.DateLimit = None
        self.WarnCount = 0
        self.isDirty = True

    def setUsage(self, used) :
        """Sets the PageCounter and LifePageCounter to used, or if used is + or - prefixed, changes the values of {Life,}PageCounter by that amount."""
        vused = int(used)
        if used.startswith("+") or used.startswith("-") :
            self.PageCounter += vused
            self.LifePageCounter += vused
        else :
            self.PageCounter = self.LifePageCounter = vused
        self.DateLimit = None
        self.WarnCount = 0
        self.isDirty = 1

    def incDenyBannerCounter(self) :
        """Increment the deny banner counter for this user quota."""
        self.parent.increaseUserPQuotaWarnCount(self)
        self.WarnCount = (self.WarnCount or 0) + 1

    def resetDenyBannerCounter(self) :
        """Resets the deny banner counter for this user quota."""
        self.parent.writeUserPQuotaWarnCount(self, 0)
        self.WarnCount = 0

    def reset(self) :
        """Resets page counter to 0."""
        self.PageCounter = 0
        self.DateLimit = None
        self.isDirty = True

    def hardreset(self) :
        """Resets actual and life time page counters to 0."""
        self.PageCounter = self.LifePageCounter = 0
        self.DateLimit = None
        self.isDirty = True

    def computeJobPrice(self, jobsize, inkusage=[]) :
        """Computes the job price as the sum of all parent printers' prices + current printer's ones."""
        totalprice = 0.0
        if jobsize :
            if self.User.OverCharge != 0.0 :    # optimization, but TODO : beware of rounding errors
                for upq in [ self ] + self.ParentPrintersUserPQuota :
                    totalprice += float(upq.Printer.PricePerJob or 0.0)
                    pageprice = float(upq.Printer.PricePerPage or 0.0)
                    if not inkusage :
                        totalprice += (jobsize * pageprice)
                    else :
                        for pageindex in range(jobsize) :
                            try :
                                usage = inkusage[pageindex]
                            except IndexError :
                                self.parent.tool.logdebug("No ink usage information. Using base cost of %f credits for page %i." % (pageprice, pageindex+1))
                                totalprice += pageprice
                            else :
                                coefficients = self.Printer.Coefficients
                                for (ink, value) in usage.items() :
                                    coefvalue = coefficients.get(ink, 1.0)
                                    coefprice = (coefvalue * pageprice) / 100.0
                                    inkprice = coefprice * value
                                    self.parent.tool.logdebug("Applying coefficient %f for color %s (used at %f%% on page %i) to base cost %f gives %f" % (coefvalue, ink, value, pageindex+1, pageprice, inkprice))
                                    totalprice += inkprice
        if self.User.OverCharge != 1.0 : # TODO : beware of rounding errors
            overcharged = totalprice * self.User.OverCharge
            self.parent.tool.logdebug("Overcharging %s by a factor of %s ===> User %s will be charged for %s credits." % (totalprice, self.User.OverCharge, self.User.Name, overcharged))
            return overcharged
        else :
            return totalprice

    def increasePagesUsage(self, jobsize, inkusage=[]) :
        """Increase the value of used pages and money."""
        jobprice = self.computeJobPrice(jobsize, inkusage)
        if jobsize :
            if jobprice :
                self.User.consumeAccountBalance(jobprice)
            for upq in [ self ] + self.ParentPrintersUserPQuota :
                self.parent.increaseUserPQuotaPagesCounters(upq, jobsize)
                upq.PageCounter = int(upq.PageCounter or 0) + jobsize
                upq.LifePageCounter = int(upq.LifePageCounter or 0) + jobsize
        return jobprice

    def delete(self) :
        """Deletes an user print quota entry from the database."""
        self.parent.deleteUserPQuota(self)
        if self.parent.usecache :
            self.parent.flushEntry("USERPQUOTAS", "%s@%s" % (self.User.Name, self.Printer.Name))
        self.Exists = False
        self.isDirty = False

    def refund(self, nbpages) :
        """Refunds a number of pages to an user on a particular printer."""
        self.parent.increaseUserPQuotaPagesCounters(self, -nbpages)
        self.PageCounter = int(self.PageCounter or 0) - nbpages
        self.LifePageCounter = int(self.LifePageCounter or 0) - nbpages


class StorageGroupPQuota(StorageObject) :
    """Group Print Quota class."""
    def __init__(self, parent, group, printer) :
        StorageObject.__init__(self, parent)
        self.Group = group
        self.Printer = printer
        self.PageCounter = None
        self.LifePageCounter = None
        self.SoftLimit = None
        self.HardLimit = None
        self.DateLimit = None
        self.MaxJobSize = None

    def __getattr__(self, name) :
        """Delays data retrieval until it's really needed."""
        if name == "ParentPrintersGroupPQuota" :
            self.ParentPrintersGroupPQuota = (self.Group.Exists and self.Printer.Exists and self.parent.getParentPrintersGroupPQuota(self)) or []
            return self.ParentPrintersGroupPQuota
        else :
            raise AttributeError, name

    def reset(self) :
        """Resets page counter to 0."""
        for user in self.parent.getGroupMembers(self.Group) :
            uq = self.parent.getUserPQuota(user, self.Printer)
            uq.reset()
            uq.save()
        self.PageCounter = 0
        self.DateLimit = None
        self.isDirty = True

    def hardreset(self) :
        """Resets actual and life time page counters to 0."""
        for user in self.parent.getGroupMembers(self.Group) :
            uq = self.parent.getUserPQuota(user, self.Printer)
            uq.hardreset()
            uq.save()
        self.PageCounter = self.LifePageCounter = 0
        self.DateLimit = None
        self.isDirty = True

    def setDateLimit(self, datelimit) :
        """Sets the date limit for this quota."""
        datelimit = DateTime.ISO.ParseDateTime(str(datelimit)[:19])
        date = "%04i-%02i-%02i %02i:%02i:%02i" % (datelimit.year, \
                                                  datelimit.month, \
                                                  datelimit.day, \
                                                  datelimit.hour, \
                                                  datelimit.minute, \
                                                  datelimit.second)
        self.parent.writeGroupPQuotaDateLimit(self, date)
        self.DateLimit = date

    def setLimits(self, softlimit, hardlimit) :
        """Sets the soft and hard limit for this quota."""
        self.SoftLimit = softlimit
        self.HardLimit = hardlimit
        self.DateLimit = None
        self.isDirty = True

    def delete(self) :
        """Deletes a group print quota entry from the database."""
        self.parent.deleteGroupPQuota(self)
        if self.parent.usecache :
            self.parent.flushEntry("GROUPPQUOTAS", "%s@%s" % (self.Group.Name, self.Printer.Name))
        self.Exists = False
        self.isDirty = False


class StorageJob(StorageObject) :
    """Printer's Job class."""
    def __init__(self, parent) :
        StorageObject.__init__(self, parent)
        self.UserName = None
        self.PrinterName = None
        self.JobId = None
        self.PrinterPageCounter = None
        self.JobSizeBytes = None
        self.JobSize = None
        self.JobAction = None
        self.JobDate = None
        self.JobPrice = None
        self.JobFileName = None
        self.JobTitle = None
        self.JobCopies = None
        self.JobOptions = None
        self.JobHostName = None
        self.JobMD5Sum = None
        self.JobPages = None
        self.JobBillingCode = None
        self.PrecomputedJobSize = None
        self.PrecomputedJobPrice = None

    def __getattr__(self, name) :
        """Delays data retrieval until it's really needed."""
        if name == "User" :
            self.User = self.parent.getUser(self.UserName)
            return self.User
        elif name == "Printer" :
            self.Printer = self.parent.getPrinter(self.PrinterName)
            return self.Printer
        else :
            raise AttributeError, name

    def refund(self, reason) :
        """Refund a particular print job."""
        if (not self.JobSize) or (self.JobAction in ("DENY", "CANCEL", "REFUND")) :
            return
        try :
            loginname = os.getlogin()
        except OSError :
            import pwd
            loginname = pwd.getpwuid(os.getuid()).pw_name
        basereason = _("Refunded %i pages and %.3f credits by %s (%s) on %s") \
                        % (self.JobSize,
                           self.JobPrice,
                           self.parent.tool.originalUserName,
                           loginname,
                           str(DateTime.now())[:19])
        if reason :
            reason = "%s : %s" % (basereason, reason)
        else :
            reason = basereason
        self.parent.tool.logdebug("Refunding job %s..." % self.ident)
        self.parent.beginTransaction()
        try :
            if self.JobBillingCode :
                bcode = self.parent.getBillingCode(self.JobBillingCode)
                bcode.refund(self.JobSize, self.JobPrice)

            if self.User.Exists :
                self.User.refund(self.JobPrice, reason)
                if self.Printer.Exists :
                    upq = self.parent.getUserPQuota(self.User, self.Printer)
                    if upq.Exists :
                        upq.refund(self.JobSize)
            self.parent.refundJob(self.ident)
        except :
            self.parent.rollbackTransaction()
            self.parent.tool.logdebug("Error while refunding job %s." % self.ident)
            raise
        else :
            self.parent.commitTransaction()
            self.parent.tool.logdebug("Job %s refunded." % self.ident)


class StorageLastJob(StorageJob) :
    """Printer's Last Job class."""
    def __init__(self, parent, printer) :
        StorageJob.__init__(self, parent)
        self.PrinterName = printer.Name # not needed
        self.Printer = printer


class StorageBillingCode(StorageObject) :
    """Billing code class."""
    def __init__(self, parent, name) :
        StorageObject.__init__(self, parent)
        self.BillingCode = name
        self.PageCounter = None
        self.Balance = None

    def delete(self) :
        """Deletes the billing code from the database."""
        self.parent.deleteBillingCode(self)
        self.parent.flushEntry("BILLINGCODES", self.BillingCode)
        self.isDirty = False
        self.Exists = False

    def reset(self, balance=0.0, pagecounter=0) :
        """Resets the pagecounter and balance for this billing code."""
        self.Balance = balance
        self.PageCounter = pagecounter
        self.isDirty = True

    def consume(self, pages, price) :
        """Consumes some pages and credits for this billing code."""
        if pages :
            self.parent.consumeBillingCode(self, pages, price)
            self.PageCounter += pages
            self.Balance -= price

    def refund(self, pages, price) :
        """Refunds a particular billing code."""
        self.consume(-pages, -price)


class BaseStorage :
    def __init__(self, pykotatool) :
        """Opens the storage connection."""
        self.closed = 1
        self.tool = pykotatool
        self.usecache = pykotatool.config.getCaching()
        self.disablehistory = pykotatool.config.getDisableHistory()
        self.privacy = pykotatool.config.getPrivacy()
        if self.privacy :
            pykotatool.logdebug("Jobs' title, filename and options will be hidden because of privacy concerns.")
        if self.usecache :
            self.tool.logdebug("Caching enabled.")
            self.caches = { "USERS" : {}, \
                            "GROUPS" : {}, \
                            "PRINTERS" : {}, \
                            "USERPQUOTAS" : {}, \
                            "GROUPPQUOTAS" : {}, \
                            "JOBS" : {}, \
                            "LASTJOBS" : {}, \
                            "BILLINGCODES" : {} }

    def close(self) :
        """Must be overriden in children classes."""
        raise RuntimeError, "BaseStorage.close() must be overriden !"

    def __del__(self) :
        """Ensures that the database connection is closed."""
        self.close()

    def getFromCache(self, cachetype, key) :
        """Tries to extract something from the cache."""
        if self.usecache :
            entry = self.caches[cachetype].get(key)
            if entry is not None :
                self.tool.logdebug("Cache hit (%s->%s)" % (cachetype, key))
            else :
                self.tool.logdebug("Cache miss (%s->%s)" % (cachetype, key))
            return entry

    def cacheEntry(self, cachetype, key, value) :
        """Puts an entry in the cache."""
        if self.usecache and getattr(value, "Exists", 0) :
            self.caches[cachetype][key] = value
            self.tool.logdebug("Cache store (%s->%s)" % (cachetype, key))

    def flushEntry(self, cachetype, key) :
        """Removes an entry from the cache."""
        if self.usecache :
            try :
                del self.caches[cachetype][key]
            except KeyError :
                pass
            else :
                self.tool.logdebug("Cache flush (%s->%s)" % (cachetype, key))

    def getUser(self, username) :
        """Returns the user from cache."""
        user = self.getFromCache("USERS", username)
        if user is None :
            user = self.getUserFromBackend(username)
            self.cacheEntry("USERS", username, user)
        return user

    def getGroup(self, groupname) :
        """Returns the group from cache."""
        group = self.getFromCache("GROUPS", groupname)
        if group is None :
            group = self.getGroupFromBackend(groupname)
            self.cacheEntry("GROUPS", groupname, group)
        return group

    def getPrinter(self, printername) :
        """Returns the printer from cache."""
        printer = self.getFromCache("PRINTERS", printername)
        if printer is None :
            printer = self.getPrinterFromBackend(printername)
            self.cacheEntry("PRINTERS", printername, printer)
        return printer

    def getUserPQuota(self, user, printer) :
        """Returns the user quota information from cache."""
        useratprinter = "%s@%s" % (user.Name, printer.Name)
        upquota = self.getFromCache("USERPQUOTAS", useratprinter)
        if upquota is None :
            upquota = self.getUserPQuotaFromBackend(user, printer)
            self.cacheEntry("USERPQUOTAS", useratprinter, upquota)
        return upquota

    def getGroupPQuota(self, group, printer) :
        """Returns the group quota information from cache."""
        groupatprinter = "%s@%s" % (group.Name, printer.Name)
        gpquota = self.getFromCache("GROUPPQUOTAS", groupatprinter)
        if gpquota is None :
            gpquota = self.getGroupPQuotaFromBackend(group, printer)
            self.cacheEntry("GROUPPQUOTAS", groupatprinter, gpquota)
        return gpquota

    def getPrinterLastJob(self, printer) :
        """Extracts last job information for a given printer from cache."""
        lastjob = self.getFromCache("LASTJOBS", printer.Name)
        if lastjob is None :
            lastjob = self.getPrinterLastJobFromBackend(printer)
            self.cacheEntry("LASTJOBS", printer.Name, lastjob)
        return lastjob

    def getBillingCode(self, label) :
        """Returns the user from cache."""
        code = self.getFromCache("BILLINGCODES", label)
        if code is None :
            code = self.getBillingCodeFromBackend(label)
            self.cacheEntry("BILLINGCODES", label, code)
        return code

    def getParentPrinters(self, printer) :
        """Extracts parent printers information for a given printer from cache."""
        if self.usecache :
            if not hasattr(printer, "Parents") :
                self.tool.logdebug("Cache miss (%s->Parents)" % printer.Name)
                printer.Parents = self.getParentPrintersFromBackend(printer)
                self.tool.logdebug("Cache store (%s->Parents)" % printer.Name)
            else :
                self.tool.logdebug("Cache hit (%s->Parents)" % printer.Name)
        else :
            printer.Parents = self.getParentPrintersFromBackend(printer)
        for parent in printer.Parents[:] :
            printer.Parents.extend(self.getParentPrinters(parent))
        uniquedic = {}
        for parent in printer.Parents :
            uniquedic[parent.Name] = parent
        printer.Parents = uniquedic.values()
        return printer.Parents

    def getGroupMembers(self, group) :
        """Returns the group's members list from in-group cache."""
        if self.usecache :
            if not hasattr(group, "Members") :
                self.tool.logdebug("Cache miss (%s->Members)" % group.Name)
                group.Members = self.getGroupMembersFromBackend(group)
                self.tool.logdebug("Cache store (%s->Members)" % group.Name)
            else :
                self.tool.logdebug("Cache hit (%s->Members)" % group.Name)
        else :
            group.Members = self.getGroupMembersFromBackend(group)
        return group.Members

    def getUserGroups(self, user) :
        """Returns the user's groups list from in-user cache."""
        if self.usecache :
            if not hasattr(user, "Groups") :
                self.tool.logdebug("Cache miss (%s->Groups)" % user.Name)
                user.Groups = self.getUserGroupsFromBackend(user)
                self.tool.logdebug("Cache store (%s->Groups)" % user.Name)
            else :
                self.tool.logdebug("Cache hit (%s->Groups)" % user.Name)
        else :
            user.Groups = self.getUserGroupsFromBackend(user)
        return user.Groups

    def getParentPrintersUserPQuota(self, userpquota) :
        """Returns all user print quota on the printer and all its parents recursively."""
        upquotas = [ ]
        for printer in self.getParentPrinters(userpquota.Printer) :
            upq = self.getUserPQuota(userpquota.User, printer)
            if upq.Exists :
                upquotas.append(upq)
        return upquotas

    def getParentPrintersGroupPQuota(self, grouppquota) :
        """Returns all group print quota on the printer and all its parents recursively."""
        gpquotas = [ ]
        for printer in self.getParentPrinters(grouppquota.Printer) :
            gpq = self.getGroupPQuota(grouppquota.Group, printer)
            if gpq.Exists :
                gpquotas.append(gpq)
        return gpquotas

    def databaseToUserCharset(self, text) :
        """Converts from database format (UTF-8) to user's charset."""
        return self.tool.UTF8ToUserCharset(text)

    def userCharsetToDatabase(self, text) :
        """Converts from user's charset to database format (UTF-8)."""
        return self.tool.userCharsetToUTF8(text)

    def cleanDates(self, startdate, enddate) :
        """Clean the dates to create a correct filter."""
        if startdate :
            startdate = startdate.strip().lower()
        if enddate :
            enddate = enddate.strip().lower()
        if (not startdate) and (not enddate) :
            return (None, None)

        now = DateTime.now()
        nameddates = ('yesterday', 'today', 'now', 'tomorrow')
        datedict = { "start" : startdate, "end" : enddate }
        for limit in datedict.keys() :
            dateval = datedict[limit]
            if dateval :
                for name in nameddates :
                    if dateval.startswith(name) :
                        try :
                            offset = int(dateval[len(name):])
                        except :
                            offset = 0
                        dateval = dateval[:len(name)]
                        if limit == "start" :
                            if dateval == "yesterday" :
                                dateval = (now - 1 + offset).Format("%Y%m%d000000")
                            elif dateval == "today" :
                                dateval = (now + offset).Format("%Y%m%d000000")
                            elif dateval == "now" :
                                dateval = (now + offset).Format("%Y%m%d%H%M%S")
                            else : # tomorrow
                                dateval = (now + 1 + offset).Format("%Y%m%d000000")
                        else :
                            if dateval == "yesterday" :
                                dateval = (now - 1 + offset).Format("%Y%m%d235959")
                            elif dateval == "today" :
                                dateval = (now + offset).Format("%Y%m%d235959")
                            elif dateval == "now" :
                                dateval = (now + offset).Format("%Y%m%d%H%M%S")
                            else : # tomorrow
                                dateval = (now + 1 + offset).Format("%Y%m%d235959")
                        break

                if not dateval.isdigit() :
                    dateval = None
                else :
                    lgdateval = len(dateval)
                    if lgdateval == 4 :
                        if limit == "start" :
                            dateval = "%s0101 00:00:00" % dateval
                        else :
                            dateval = "%s1231 23:59:59" % dateval
                    elif lgdateval == 6 :
                        if limit == "start" :
                            dateval = "%s01 00:00:00" % dateval
                        else :
                            mxdate = DateTime.ISO.ParseDateTime("%s01 00:00:00" % dateval)
                            dateval = "%s%02i 23:59:59" % (dateval, mxdate.days_in_month)
                    elif lgdateval == 8 :
                        if limit == "start" :
                            dateval = "%s 00:00:00" % dateval
                        else :
                            dateval = "%s 23:59:59" % dateval
                    elif lgdateval == 10 :
                        if limit == "start" :
                            dateval = "%s %s:00:00" % (dateval[:8], dateval[8:])
                        else :
                            dateval = "%s %s:59:59" % (dateval[:8], dateval[8:])
                    elif lgdateval == 12 :
                        if limit == "start" :
                            dateval = "%s %s:%s:00" % (dateval[:8], dateval[8:10], dateval[10:])
                        else :
                            dateval = "%s %s:%s:59" % (dateval[:8], dateval[8:10], dateval[10:])
                    elif lgdateval == 14 :
                        dateval = "%s %s:%s:%s" % (dateval[:8], dateval[8:10], dateval[10:12], dateval[12:])
                    else :
                        dateval = None
                    try :
                        DateTime.ISO.ParseDateTime(dateval[:19])
                    except :
                        dateval = None
                datedict[limit] = dateval
        (start, end) = (datedict["start"], datedict["end"])
        if start and end and (start > end) :
            (start, end) = (end, start)
        try :
            if len(start) == 17 :
                start = "%s-%s-%s %s" % (start[0:4], start[4:6], start[6:8], start[9:])
        except TypeError :
            pass

        try :
            if len(end) == 17 :
                end = "%s-%s-%s %s" % (end[0:4], end[4:6], end[6:8], end[9:])
        except TypeError :
            pass

        return (start, end)

def openConnection(pykotatool) :
    """Returns a connection handle to the appropriate database."""
    backendinfo = pykotatool.config.getStorageBackend()
    backend = backendinfo["storagebackend"]
    try :
        storagebackend = imp.load_source("storagebackend",
                                         os.path.join(os.path.dirname(__file__),
                                                      "storages",
                                                      "%s.py" % backend.lower()))
    except ImportError :
        raise PyKotaStorageError, _("Unsupported quota storage backend %s") % backend
    else :
        host = backendinfo["storageserver"]
        database = backendinfo["storagename"]
        admin = backendinfo["storageadmin"] or backendinfo["storageuser"]
        adminpw = backendinfo["storageadminpw"] or backendinfo["storageuserpw"]
        return storagebackend.Storage(pykotatool, host, database, admin, adminpw)

