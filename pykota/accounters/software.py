# PyKota
# -*- coding: ISO-8859-15 -*-
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
# $Id: software.py 3133 2007-01-17 22:19:42Z jerome $
#
#

import os
import popen2
from pykota.accounter import AccounterBase, PyKotaAccounterError

class Accounter(AccounterBase) :
    def computeJobSize(self) :    
        """Feeds an external command with our datas to let it compute the job size, and return its value."""
        if (not self.isPreAccounter) and \
            (self.filter.accounter.arguments == self.filter.preaccounter.arguments) :
            # if precomputing has been done and both accounter and preaccounter are
            # configured the same, no need to launch a second pass since we already
            # know the result.
            self.filter.logdebug("Precomputing pass told us that job is %s pages long." % self.filter.softwareJobSize)
            return self.filter.softwareJobSize   # Optimize : already computed !
            
        if self.arguments :
            self.filter.logdebug("Using external script %s to compute job's size." % self.arguments)
            return self.withExternalScript()
        else :    
            self.filter.logdebug("Using internal parser to compute job's size.")
            return self.withInternalParser()
        
    def withInternalParser(self) :    
        """Does software accounting through an external script."""
        jobsize = 0
        if self.filter.JobSizeBytes :
            try :
                from pkpgpdls import analyzer, pdlparser
            except ImportError :    
                self.filter.printInfo("pkpgcounter is now distributed separately, please grab it from http://www.pykota.com/software/pkpgcounter", "error")
                self.filter.printInfo("Precomputed job size will be forced to 0 pages.", "error")
            else :     
                infile = open(self.filter.DataFile, "rb")
                try :
                    parser = analyzer.PDLAnalyzer(infile)
                    jobsize = parser.getJobSize()
                except pdlparser.PDLParserError, msg :    
                    # Here we just log the failure, but
                    # we finally ignore it and return 0 since this
                    # computation is just an indication of what the
                    # job's size MAY be.
                    self.filter.printInfo(_("Unable to precompute the job's size with the generic PDL analyzer : %s") % msg, "warn")
                else :    
                    if self.filter.InputFile is not None :
                        # when a filename is passed as an argument, the backend 
                        # must generate the correct number of copies.
                        jobsize *= self.filter.Copies
                infile.close()        
        return jobsize        
                
    def withExternalScript(self) :    
        """Does software accounting through an external script."""
        self.filter.printInfo(_("Launching SOFTWARE(%s)...") % self.arguments)
        MEGABYTE = 1024*1024
        infile = open(self.filter.DataFile, "rb")
        child = popen2.Popen4(self.arguments)
        try :
            data = infile.read(MEGABYTE)    
            while data :
                child.tochild.write(data)
                data = infile.read(MEGABYTE)
            child.tochild.flush()
            child.tochild.close()    
        except (IOError, OSError), msg :    
            msg = "%s : %s" % (self.arguments, msg) 
            self.filter.printInfo(_("Unable to compute job size with accounter %s") % msg)
        infile.close()
        pagecounter = None
        try :
            answer = child.fromchild.read()
        except (IOError, OSError), msg :    
            msg = "%s : %s" % (self.arguments, msg) 
            self.filter.printInfo(_("Unable to compute job size with accounter %s") % msg)
        else :    
            lines = [l.strip() for l in answer.split("\n")]
            for i in range(len(lines)) : 
                try :
                    pagecounter = int(lines[i])
                except (AttributeError, ValueError) :
                    self.filter.printInfo(_("Line [%s] skipped in accounter's output. Trying again...") % lines[i])
                else :    
                    break
        child.fromchild.close()
        
        try :
            status = child.wait()
        except OSError, msg :    
            self.filter.printInfo(_("Problem while waiting for software accounter pid %s to exit : %s") % (child.pid, msg))
        else :    
            if os.WIFEXITED(status) :
                status = os.WEXITSTATUS(status)
            self.filter.printInfo(_("Software accounter %s exit code is %s") % (self.arguments, str(status)))
            
        if pagecounter is None :    
            message = _("Unable to compute job size with accounter %s") % self.arguments
            if self.onerror == "CONTINUE" :
                self.filter.printInfo(message, "error")
            else :
                raise PyKotaAccounterError, message
        self.filter.logdebug("Software accounter %s said job is %s pages long." % (self.arguments, repr(pagecounter)))
            
        pagecounter = pagecounter or 0    
        if self.filter.InputFile is not None :
            # when a filename is passed as an argument, the backend 
            # must generate the correct number of copies.
            pagecounter *= self.filter.Copies
                        
        return pagecounter
