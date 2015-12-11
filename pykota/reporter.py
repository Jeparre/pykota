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
# $Id: reporter.py 3184 2007-05-30 20:29:50Z jerome $
#
#

"""This module defines bases classes used by all reporters."""

import os
import imp
from mx import DateTime

class PyKotaReporterError(Exception):
    """An exception for Reporter related stuff."""
    def __init__(self, message = ""):
        self.message = message
        Exception.__init__(self, message)
    def __repr__(self):
        return self.message
    __str__ = __repr__
    
class BaseReporter :    
    """Base class for all reports."""
    def __init__(self, tool, printers, ugnames, isgroup) :
        """Initialize local datas."""
        self.tool = tool
        self.printers = printers
        self.ugnames = ugnames
        self.isgroup = isgroup
        
    def getPrinterTitle(self, printer) :     
        """Returns the formatted title for a given printer."""
        return (_("Report for %s quota on printer %s") % ((self.isgroup and "group") or "user", printer.Name)) + (" (%s)" % printer.Description)
        
    def getPrinterGraceDelay(self, printer) :    
        """Returns the formatted grace delay for a given printer."""
        return _("Pages grace time: %i days") % self.tool.config.getGraceDelay(printer.Name)
        
    def getPrinterPrices(self, printer) :    
        """Returns the formatted prices for a given printer."""
        return (_("Price per job: %.3f") % (printer.PricePerJob or 0.0), _("Price per page: %.3f") % (printer.PricePerPage or 0.0))
            
    def getReportHeader(self) :        
        """Returns the correct header depending on users vs users groups."""
        if self.isgroup :
            return _("Group          overcharge   used    soft    hard    balance grace         total       paid warn")
        else :    
            return _("User           overcharge   used    soft    hard    balance grace         total       paid warn")
            
    def getPrinterRealPageCounter(self, printer) :        
        """Returns the formatted real page counter for a given printer."""
        msg = _("unknown")
        if printer.LastJob.Exists :
            try :
                msg = "%9i" % printer.LastJob.PrinterPageCounter
            except TypeError :     
                pass
        return _("Real : %s") % msg
                
    def getTotals(self, total, totalmoney) :            
        """Returns the formatted totals."""
        return (_("Total : %9i") % (total or 0.0), ("%11s" % ("%7.2f" % (totalmoney or 0.0))[:11]))
            
    def getQuota(self, entry, quota) :
        """Prints the quota information."""
        lifepagecounter = int(quota.LifePageCounter or 0)
        pagecounter = int(quota.PageCounter or 0)
        balance = float(entry.AccountBalance or 0.0)
        lifetimepaid = float(entry.LifeTimePaid or 0.0)
        if not hasattr(entry, "OverCharge") :
            overcharge = _("N/A")       # Not available for groups
        else :    
            overcharge = float(entry.OverCharge or 0.0)
        if not hasattr(quota, "WarnCount") :    
            warncount = _("N/A")        # Not available for groups
        else :    
            warncount = int(quota.WarnCount or 0)
        
        if (not entry.LimitBy) or (entry.LimitBy.lower() == "quota") :
            if (quota.HardLimit is not None) and (pagecounter >= quota.HardLimit) :    
                datelimit = "DENY"
            elif (quota.HardLimit is None) and (quota.SoftLimit is not None) and (pagecounter >= quota.SoftLimit) :
                datelimit = "DENY"
            elif quota.DateLimit is not None :
                now = DateTime.now()
                datelimit = DateTime.ISO.ParseDateTime(str(quota.DateLimit)[:19])
                if now >= datelimit :
                    datelimit = "DENY"
            else :    
                datelimit = ""
            reached = (((quota.SoftLimit is not None) and (pagecounter >= quota.SoftLimit) and "+") or "-") + "Q"
        else :
            if entry.LimitBy.lower() == "balance" :
                balancezero = self.tool.config.getBalanceZero()
                if balance == balancezero :
                    if entry.OverCharge > 0 :
                        datelimit = "DENY"
                        reached = "+B"
                    else :    
                        # overcharging by a negative or nul factor means user is always allowed to print
                        # TODO : do something when printer prices are negative as well !
                        datelimit = ""
                        reached = "-B"
                elif balance < balancezero :
                    datelimit = "DENY"
                    reached = "+B"
                elif balance <= self.tool.config.getPoorMan() :
                    datelimit = "WARNING"
                    reached = "?B"
                else :    
                    datelimit = ""
                    reached = "-B"
            elif entry.LimitBy.lower() == "noquota" :
                reached = "NQ"
                datelimit = ""
            elif entry.LimitBy.lower() == "nochange" :
                reached = "NC"
                datelimit = ""
            else :
                # noprint
                reached = "NP"
                datelimit = "DENY"
            
        strbalance = ("%5.2f" % balance)[:10]
        strlifetimepaid = ("%6.2f" % lifetimepaid)[:10]
        strovercharge = ("%5s" % overcharge)[:5]
        strwarncount = ("%4s" % warncount)[:4]
        return (lifepagecounter, lifetimepaid, entry.Name, reached, \
                pagecounter, str(quota.SoftLimit), str(quota.HardLimit), \
                strbalance, str(datelimit)[:10], lifepagecounter, \
                strlifetimepaid, strovercharge, strwarncount)
        
def openReporter(tool, reporttype, printers, ugnames, isgroup) :
    """Returns a reporter instance of the proper reporter."""
    try :
        reporterbackend = imp.load_source("reporterbackend", 
                                           os.path.join(os.path.dirname(__file__),
                                                        "reporters",
                                                        "%s.py" % reporttype.lower()))
    except ImportError :
        raise PyKotaReporterError, _("Unsupported reporter backend %s") % reporttype
    else :    
        return reporterbackend.Reporter(tool, printers, ugnames, isgroup)
