#! /usr/bin/python
# -*- coding: ISO-8859-15 -*-

# PyKota Print Quota Reports generator
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
# $Id: printquota.cgi 3133 2007-01-17 22:19:42Z jerome $
#
#

import sys
import os
import cgi
import urllib

from mx import DateTime

from pykota import version
from pykota.tool import PyKotaTool, PyKotaToolError
from pykota.reporter import PyKotaReporterError, openReporter
from pykota.cgifuncs import getLanguagePreference, getCharsetPreference

header = """Content-type: text/html;charset=%s

<html>
  <head>
    <title>%s</title>
    <link rel="stylesheet" type="text/css" href="/pykota.css" />
  </head>
  <body>
    <!-- %s %s -->
    <p>
      <form action="printquota.cgi" method="POST">
        <table>
          <tr>
            <td>
              <p>
                <a href="%s"><img src="%s?version=%s" alt="PyKota's Logo" /></a>
                <br />
                <a href="%s">PyKota v%s</a>
              </p>
            </td>
            <td colspan="2">
              <h1>%s</h1>
            </td>
          </tr>
          <tr>
            <td colspan="3" align="center">
              <input type="submit" name="report" value="%s" />
            </td>
          </tr>
        </table>"""
    
footer = """
        <table>
          <tr>
            <td colspan="3" align="center">
              <input type="submit" name="report" value="%s" />
            </td>
          </tr>
        </table>  
      </form>
    </p>
    <hr width="25%%" />
    <p>
      <font size="-2">
        <a href="http://www.pykota.com/">%s</a>
        &copy; %s %s 
        <br />
        <pre>
%s
        </pre>
      </font>
    </p>
  </body>
</html>"""  

class PyKotaReportGUI(PyKotaTool) :
    """PyKota Administrative GUI"""
    def guiDisplay(self) :
        """Displays the administrative interface."""
        global header, footer
        print header % (self.charset, _("PyKota Reports"), \
                        self.language, self.charset, \
                        self.config.getLogoLink(), \
                        self.config.getLogoURL(), version.__version__, \
                        self.config.getLogoLink(), \
                        version.__version__, _("PyKota Reports"), \
                        _("Report"))
        print self.body
        print footer % (_("Report"), version.__doc__, version.__years__, version.__author__, version.__gplblurb__)
        
    def error(self, message) :
        """Adds an error message to the GUI's body."""
        if message :
            self.body = '<p><font color="red">%s</font></p>\n%s' % (message, self.body)
        
    def htmlListPrinters(self, selected=[], mask="*") :    
        """Displays the printers multiple selection list."""
        printers = self.storage.getMatchingPrinters(mask)
        selectednames = [p.Name for p in selected]
        message = '<table><tr><td valign="top">%s :</td><td valign="top"><select name="printers" multiple="multiple">' % _("Printer")
        for printer in printers :
            if printer.Name in selectednames :
                message += '<option value="%s" selected="selected">%s (%s)</option>' % (printer.Name, printer.Name, printer.Description)
            else :
                message += '<option value="%s">%s (%s)</option>' % (printer.Name, printer.Name, printer.Description)
        message += '</select></td></tr></table>'
        return message
        
    def htmlUGNamesInput(self, value="*") :    
        """Input field for user/group names wildcard."""
        return _("User / Group names mask") + (' : <input type="text" name="ugmask" size="20" value="%s" /> <em>e.g. <strong>jo*</strong></em>' % (value or "*"))
        
    def htmlGroupsCheckbox(self, isgroup=0) :
        """Groups checkbox."""
        if isgroup :
            return _("Groups report") + ' : <input type="checkbox" checked="checked" name="isgroup" />'
        else :    
            return _("Groups report") + ' : <input type="checkbox" name="isgroup" />'
            
    def guiAction(self) :
        """Main function"""
        printers = ugmask = isgroup = None
        remuser = os.environ.get("REMOTE_USER", "root")    
        # special hack to accomodate mod_auth_ldap Apache module
        try :
            remuser = remuser.split("=")[1].split(",")[0]
        except IndexError :    
            pass
        self.body = "<p>%s</p>\n" % _("Please click on the above button")
        if self.form.has_key("report") :
            if self.form.has_key("printers") :
                printersfield = self.form["printers"]
                if type(printersfield) != type([]) :
                    printersfield = [ printersfield ]
                printers = [self.storage.getPrinter(p.value) for p in printersfield]
            else :    
                printers = self.storage.getMatchingPrinters("*")
            if remuser == "root" :
                if self.form.has_key("ugmask") :     
                    ugmask = self.form["ugmask"].value
                else :     
                    ugmask = "*"
            else :        
                if self.form.has_key("isgroup") :    
                    user = self.storage.getUser(remuser)
                    if user.Exists :
                        ugmask = " ".join([ g.Name for g in self.storage.getUserGroups(user) ])
                    else :    
                        ugmask = remuser # result will probably be empty, we don't care
                else :    
                    ugmask = remuser
            if self.form.has_key("isgroup") :    
                isgroup = 1
            else :    
                isgroup = 0
        self.body += self.htmlListPrinters(printers or [])            
        self.body += "<br />"
        self.body += self.htmlUGNamesInput(ugmask)
        self.body += "<br />"
        self.body += self.htmlGroupsCheckbox(isgroup)
        try :
            if not self.form.has_key("history") :
                if printers and ugmask :
                    self.reportingtool = openReporter(admin, "html", printers, ugmask.split(), isgroup)
                    self.body += "%s" % self.reportingtool.generateReport()
            else :        
                if remuser != "root" :
                    username = remuser
                elif self.form.has_key("username") :    
                    username = self.form["username"].value
                else :    
                    username = None
                if username is not None :    
                    user = self.storage.getUser(username)
                else :    
                    user = None
                if self.form.has_key("printername") :
                    printer = self.storage.getPrinter(self.form["printername"].value)
                else :    
                    printer = None
                if self.form.has_key("datelimit") :    
                    datelimit = self.form["datelimit"].value
                else :    
                    datelimit = None
                if self.form.has_key("hostname") :    
                    hostname = self.form["hostname"].value
                else :    
                    hostname = None
                if self.form.has_key("billingcode") :    
                    billingcode = self.form["billingcode"].value
                else :    
                    billingcode = None
                self.report = ["<h2>%s</h2>" % _("History")]    
                history = self.storage.retrieveHistory(user=user, printer=printer, hostname=hostname, billingcode=billingcode, end=datelimit)
                if not history :
                    self.report.append("<h3>%s</h3>" % _("Empty"))
                else :
                    self.report.append('<table class="pykotatable" border="1">')
                    headers = [_("Date"), _("Action"), _("User"), _("Printer"), \
                               _("Hostname"), _("JobId"), _("Number of pages"), \
                               _("Cost"), _("Copies"), _("Number of bytes"), \
                               _("Printer's internal counter"), _("Title"), _("Filename"), \
                               _("Options"), _("MD5Sum"), _("Billing code"), \
                               _("Precomputed number of pages"), _("Precomputed cost"), _("Pages details") + " " + _("(not supported yet)")]
                    self.report.append('<tr class="pykotacolsheader">%s</tr>' % "".join(["<th>%s</th>" % h for h in headers]))
                    oddeven = 0
                    for job in history :
                        oddeven += 1
                        if job.JobAction == "ALLOW" :    
                            if oddeven % 2 :
                                oddevenclass = "odd"
                            else :    
                                oddevenclass = "even"
                        else :
                            oddevenclass = (job.JobAction or "UNKNOWN").lower()
                        username_url = '<a href="%s?%s">%s</a>' % (os.environ.get("SCRIPT_NAME", ""), urllib.urlencode({"history" : 1, "username" : job.UserName}), job.UserName)
                        printername_url = '<a href="%s?%s">%s</a>' % (os.environ.get("SCRIPT_NAME", ""), urllib.urlencode({"history" : 1, "printername" : job.PrinterName}), job.PrinterName)
                        if job.JobHostName :
                            hostname_url = '<a href="%s?%s">%s</a>' % (os.environ.get("SCRIPT_NAME", ""), urllib.urlencode({"history" : 1, "hostname" : job.JobHostName}), job.JobHostName)
                        else :    
                            hostname_url = None
                        if job.JobBillingCode :
                            billingcode_url = '<a href="%s?%s">%s</a>' % (os.environ.get("SCRIPT_NAME", ""), urllib.urlencode({"history" : 1, "billingcode" : job.JobBillingCode}), job.JobBillingCode)
                        else :    
                            billingcode_url = None
                        curdate = DateTime.ISO.ParseDateTime(str(job.JobDate)[:19])
                        self.report.append('<tr class="%s">%s</tr>' % \
                                              (oddevenclass, \
                                               "".join(["<td>%s</td>" % (h or "&nbsp;") \
                                                  for h in (str(curdate)[:19], \
                                                            _(job.JobAction), \
                                                            username_url, \
                                                            printername_url, \
                                                            hostname_url, \
                                                            job.JobId, \
                                                            job.JobSize, \
                                                            job.JobPrice, \
                                                            job.JobCopies, \
                                                            job.JobSizeBytes, \
                                                            job.PrinterPageCounter, \
                                                            job.JobTitle, \
                                                            job.JobFileName, \
                                                            job.JobOptions, \
                                                            job.JobMD5Sum, \
                                                            billingcode_url, \
                                                            job.PrecomputedJobSize, \
                                                            job.PrecomputedJobPrice, \
                                                            job.JobPages)])))
                    self.report.append('</table>')
                    dico = { "history" : 1,
                             "datelimit" : "%04i-%02i-%02i %02i:%02i:%02i" \
                                                         % (curdate.year, \
                                                            curdate.month, \
                                                            curdate.day, \
                                                            curdate.hour, \
                                                            curdate.minute, \
                                                            curdate.second),
                           }
                    if user and user.Exists :
                        dico.update({ "username" : user.Name })
                    if printer and printer.Exists :
                        dico.update({ "printername" : printer.Name })
                    if hostname :    
                        dico.update({ "hostname" : hostname })
                    prevurl = "%s?%s" % (os.environ.get("SCRIPT_NAME", ""), urllib.urlencode(dico))
                    self.report.append('<a href="%s">%s</a>' % (prevurl, _("Previous page")))
                self.body = "\n".join(self.report)    
        except :
                self.body += '<p><font color="red">%s</font></p>' % self.crashed("CGI Error").replace("\n", "<br />")
            
if __name__ == "__main__" :
    admin = PyKotaReportGUI(lang=getLanguagePreference(), charset=getCharsetPreference())
    admin.deferredInit()
    admin.form = cgi.FieldStorage()
    admin.guiAction()
    admin.guiDisplay()
    try :
        admin.storage.close()
    except (TypeError, NameError, AttributeError) :    
        pass
        
    sys.exit(0)
