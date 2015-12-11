# PyKota
# -*- coding: ISO-8859-15 -*-

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
# $Id: html.py 3184 2007-05-30 20:29:50Z jerome $
#
#

"""This module defines a class for HTML reporting."""

import os
import urllib

from pykota.reporter import BaseReporter
    
class Reporter(BaseReporter) :    
    """HTML reporter."""
    def generateReport(self) :
        """Produces a simple HTML report."""
        self.report = []
        if self.isgroup :
            prefix = "Group"
        else :    
            prefix = "User"
        for printer in self.printers :
            phistoryurl = { "printername" : printer.Name, "history" : 1 }
            self.report.append('<a href="%s?%s"><h2 class="printername">%s</h2></a>' % (os.environ.get("SCRIPT_NAME", ""), urllib.urlencode(phistoryurl), self.getPrinterTitle(printer)))
            self.report.append('<h3 class="printergracedelay">%s</h3>' % self.getPrinterGraceDelay(printer))
            (pjob, ppage) = self.getPrinterPrices(printer)
            self.report.append('<h4 class="priceperjob">%s</h4>' % pjob)
            self.report.append('<h4 class="priceperpage">%s</h4>' % ppage)
            total = 0
            totalmoney = 0.0
            self.report.append('<table class="pykotatable" border="1">')
            headers = self.getReportHeader().split()
            headers.insert(1, "LimitBy")
            self.report.append('<tr class="pykotacolsheader">%s</tr>' % "".join(["<th>%s</th>" % h for h in headers]))
            oddeven = 0
            for (entry, entrypquota) in getattr(self.tool.storage, "getPrinter%ssAndQuotas" % prefix)(printer, self.ugnames) :
                oddeven += 1
                if oddeven % 2 :
                    oddevenclass = "odd"
                else :    
                    oddevenclass = "even"
                (pages, money, name, reached, pagecounter, soft, hard, balance, datelimit, lifepagecounter, lifetimepaid, overcharge, warncount) = self.getQuota(entry, entrypquota)
                if datelimit :
                    if datelimit == "DENY" :
                        oddevenclass = "deny"
                    else :    
                        oddevenclass = "warn"
                if (not self.tool.config.getDisableHistory()) and (not self.isgroup) :
                    name = '<a href="%s?username=%s&printername=%s&history=1">%s</a>' % (os.environ.get("SCRIPT_NAME", ""), name, printer.Name, name)
                self.report.append('<tr class="%s">%s</tr>' % (oddevenclass, "".join(["<td>%s</td>" % h for h in (name, reached, overcharge, pagecounter, soft, hard, balance, datelimit or "&nbsp;", lifepagecounter, lifetimepaid, warncount)])))
                total += pages
                totalmoney += money
                
            if total or totalmoney :        
                (tpage, tmoney) = self.getTotals(total, totalmoney)
                self.report.append('<tr class="totals"><td colspan="8">&nbsp;</td><td align="right">%s</td><td align="right">%s</td><td>&nbsp;</td></tr>' % (tpage, tmoney))
            self.report.append('<tr class="realpagecounter"><td colspan="8">&nbsp;</td><td align="right">%s</td><td>&nbsp;</td></tr>' % self.getPrinterRealPageCounter(printer))
            self.report.append('</table>')
        if self.isgroup :    
            self.report.append('<p class="warning">%s</p>' % _("Totals may be inaccurate if some users are members of several groups."))
        return "\n".join(self.report)    
                        
