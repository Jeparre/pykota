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
# $Id: pjl.py 3198 2007-06-28 20:27:06Z jerome $
#
#

import sys
import os
import socket
import errno
import time
import threading
import Queue

from pykota import constants

FORMFEEDCHAR = chr(0x0c)     # Form Feed character, ends PJL answers.

# Old method : pjlMessage = "\033%-12345X@PJL USTATUSOFF\r\n@PJL INFO STATUS\r\n@PJL INFO PAGECOUNT\r\n\033%-12345X"
# Here's a new method, which seems to work fine on my HP2300N, while the 
# previous one didn't.
# TODO : We could also experiment with USTATUS JOB=ON and we would know for sure 
# when the job is finished, without having to poll the printer repeatedly.
pjlMessage = "\033%-12345X@PJL USTATUS DEVICE=ON\r\n@PJL INFO STATUS\r\n@PJL INFO PAGECOUNT\r\n@PJL USTATUS DEVICE=OFF\033%-12345X"
pjlStatusValues = {
                    "10000" : "Powersave Mode",
                    "10001" : "Ready Online",
                    "10002" : "Ready Offline",
                    "10003" : "Warming Up",
                    "10004" : "Self Test",
                    "10005" : "Reset",
                    "10023" : "Printing",
                    "35078" : "Powersave Mode",         # 10000 is ALSO powersave !!!
                    "40000" : "Sleep Mode",             # Standby
                  }
                  
class Handler :
    """A class for PJL print accounting."""
    def __init__(self, parent, printerhostname, skipinitialwait=False) :
        self.parent = parent
        self.printerHostname = printerhostname
        self.skipinitialwait = skipinitialwait
        try :
            self.port = int(self.parent.arguments.split(":")[1].strip())
        except (IndexError, ValueError) :
            self.port = 9100
        self.printerInternalPageCounter = self.printerStatus = None
        self.closed = False
        self.sock = None
        self.queue = None
        self.readthread = None
        self.quitEvent = threading.Event()
        
    def __del__(self) :    
        """Ensures the network connection is closed at object deletion time."""
        self.close()
        
    def open(self) :    
        """Opens the network connection."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try :
            sock.settimeout(1.0)
            sock.connect((self.printerHostname, self.port))
        except socket.error, msg :
            self.parent.filter.printInfo(_("Problem during connection to %s:%s : %s") % (self.printerHostname, self.port, str(msg)), "warn")
            return False
        else :
            self.sock = sock
            self.closed = False
            self.quitEvent.clear()
            self.queue = Queue.Queue(0)
            self.readthread = threading.Thread(target=self.readloop)
            self.readthread.start()
            time.sleep(1)
            self.parent.filter.logdebug("Connected to printer %s:%s" % (self.printerHostname, self.port))
            return True
        
    def close(self) :    
        """Closes the network connection."""
        if not self.closed :
            self.quitEvent.set()
            if self.readthread is not None :
                self.readthread.join()
                self.readthread = None
            if self.sock is not None :
                self.sock.close()
                self.sock = None
            self.parent.filter.logdebug("Connection to %s:%s is now closed." % (self.printerHostname, self.port))
            self.queue = None
            self.closed = True
            
    def readloop(self) :        
        """Reading loop thread."""
        self.parent.filter.logdebug("Reading thread started.")
        buffer = []
        while not self.quitEvent.isSet() :
            try :
                answer = self.sock.recv(1)
            except socket.timeout :    
                pass
            except socket.error, (err, msg) :
                self.parent.filter.printInfo(_("Problem while receiving PJL answer from %s:%s : %s") % (self.printerHostname, self.port, str(msg)), "warn")
            else :    
                if answer :
                    buffer.append(answer)
                    if answer.endswith(FORMFEEDCHAR) :
                        self.queue.put("".join(buffer))
                        buffer = []
        if buffer :             
            self.queue.put("".join(buffer))            
        self.parent.filter.logdebug("Reading thread ended.")
            
    def retrievePJLValues(self) :    
        """Retrieves a printer's internal page counter and status via PJL."""
        while not self.open() :
            self.parent.filter.logdebug("Will retry in 1 second.")
            time.sleep(1)
        try :
            try :
                nbsent = self.sock.send(pjlMessage)
                if nbsent != len(pjlMessage) :
                    raise socket.error, "Short write"
            except socket.error, msg :
                self.parent.filter.printInfo(_("Problem while sending PJL query to %s:%s : %s") % (self.printerHostname, self.port, str(msg)), "warn")
            else :    
                self.parent.filter.logdebug("Query sent to %s : %s" % (self.printerHostname, repr(pjlMessage)))
                actualpagecount = self.printerStatus = None
                while (actualpagecount is None) or (self.printerStatus is None) :
                    try :
                        answer = self.queue.get(True, 5)
                    except Queue.Empty :    
                        self.parent.filter.logdebug("Timeout when reading printer's answer from %s:%s" % (self.printerHostname, self.port))
                    else :    
                        readnext = False
                        self.parent.filter.logdebug("PJL answer : %s" % repr(answer))
                        for line in [l.strip() for l in answer.split()] : 
                            if line.startswith("CODE=") :
                                self.printerStatus = line.split("=")[1]
                                self.parent.filter.logdebug("Found status : %s" % self.printerStatus)
                            elif line.startswith("PAGECOUNT=") :    
                                try :
                                    actualpagecount = int(line.split('=')[1].strip())
                                except ValueError :    
                                    self.parent.filter.logdebug("Received incorrect datas : [%s]" % line.strip())
                                else :
                                    self.parent.filter.logdebug("Found pages counter : %s" % actualpagecount)
                            elif line.startswith("PAGECOUNT") :    
                                readnext = True # page counter is on next line
                            elif readnext :    
                                try :
                                    actualpagecount = int(line.strip())
                                except ValueError :    
                                    self.parent.filter.logdebug("Received incorrect datas : [%s]" % line.strip())
                                else :
                                    self.parent.filter.logdebug("Found pages counter : %s" % actualpagecount)
                                    readnext = False
                self.printerInternalPageCounter = max(actualpagecount, self.printerInternalPageCounter)
        finally :        
            self.close()
        
    def waitPrinting(self) :
        """Waits for printer status being 'printing'."""
        statusstabilizationdelay = constants.get(self.parent.filter, "StatusStabilizationDelay")
        noprintingmaxdelay = constants.get(self.parent.filter, "NoPrintingMaxDelay")
        if not noprintingmaxdelay :
            self.parent.filter.logdebug("Will wait indefinitely until printer %s is in 'printing' state." % self.parent.filter.PrinterName)
        else :    
            self.parent.filter.logdebug("Will wait until printer %s is in 'printing' state or %i seconds have elapsed." % (self.parent.filter.PrinterName, noprintingmaxdelay))
        previousValue = self.parent.getLastPageCounter()
        timebefore = time.time()
        firstvalue = None
        while True :
            self.retrievePJLValues()
            if self.printerStatus in ('10023', '10003') :
                break
            if self.printerInternalPageCounter is not None :    
                if firstvalue is None :
                    # first time we retrieved a page counter, save it
                    firstvalue = self.printerInternalPageCounter
                else :     
                    # second time (or later)
                    if firstvalue < self.printerInternalPageCounter :
                        # Here we have a printer which lies :
                        # it says it is not printing or warming up
                        # BUT the page counter increases !!!
                        # So we can probably quit being sure it is printing.
                        self.parent.filter.printInfo("Printer %s is lying to us !!!" % self.parent.filter.PrinterName, "warn")
                        break
                    elif noprintingmaxdelay and ((time.time() - timebefore) > noprintingmaxdelay) :
                        # More than X seconds without the printer being in 'printing' mode
                        # We can safely assume this won't change if printer is now 'idle'
                        if self.printerStatus in ('10000', '10001', '35078', '40000') :
                            if self.printerInternalPageCounter == previousValue :
                                # Here the job won't be printed, because probably
                                # the printer rejected it for some reason.
                                self.parent.filter.printInfo("Printer %s probably won't print this job !!!" % self.parent.filter.PrinterName, "warn")
                            else :     
                                # Here the job has already been entirely printed, and
                                # the printer has already passed from 'idle' to 'printing' to 'idle' again.
                                self.parent.filter.printInfo("Printer %s has probably already printed this job !!!" % self.parent.filter.PrinterName, "warn")
                            break
            self.parent.filter.logdebug(_("Waiting for printer %s to be printing...") % self.parent.filter.PrinterName)
            time.sleep(statusstabilizationdelay)
        
    def waitIdle(self) :
        """Waits for printer status being 'idle'."""
        statusstabilizationdelay = constants.get(self.parent.filter, "StatusStabilizationDelay")
        statusstabilizationloops = constants.get(self.parent.filter, "StatusStabilizationLoops")
        idle_num = 0
        while True :
            self.retrievePJLValues()
            if self.printerStatus in ('10000', '10001', '35078', '40000') :
                if (self.printerInternalPageCounter is not None) \
                   and self.skipinitialwait \
                   and (os.environ.get("PYKOTAPHASE") == "BEFORE") :
                    self.parent.filter.logdebug("No need to wait for the printer to be idle, it is the case already.")
                    return 
                idle_num += 1
                if idle_num >= statusstabilizationloops :
                    # printer status is stable, we can exit
                    break
            else :    
                idle_num = 0
            self.parent.filter.logdebug(_("Waiting for printer %s's idle status to stabilize...") % self.parent.filter.PrinterName)
            time.sleep(statusstabilizationdelay)
    
    def retrieveInternalPageCounter(self) :
        """Returns the page counter from the printer via internal PJL handling."""
        try :
            if (os.environ.get("PYKOTASTATUS") != "CANCELLED") and \
               (os.environ.get("PYKOTAACTION") == "ALLOW") and \
               (os.environ.get("PYKOTAPHASE") == "AFTER") and \
               self.parent.filter.JobSizeBytes :
                self.waitPrinting()
            self.waitIdle()    
        except :    
            self.parent.filter.printInfo(_("PJL querying stage interrupted. Using latest value seen for internal page counter (%s) on printer %s.") % (self.printerInternalPageCounter, self.parent.filter.PrinterName), "warn")
            raise
        else :    
            return self.printerInternalPageCounter
            
def main(hostname) :
    """Tries PJL accounting for a printer host."""
    class fakeFilter :
        """Fakes a filter for testing purposes."""
        def __init__(self) :
            """Initializes the fake filter."""
            self.PrinterName = "FakePrintQueue"
            self.JobSizeBytes = 1
            
        def printInfo(self, msg, level="info") :
            """Prints informational message."""
            sys.stderr.write("%s : %s\n" % (level.upper(), msg))
            sys.stderr.flush()
            
        def logdebug(self, msg) :    
            """Prints debug message."""
            self.printInfo(msg, "debug")
            
    class fakeAccounter :        
        """Fakes an accounter for testing purposes."""
        def __init__(self) :
            """Initializes fake accounter."""
            self.arguments = "pjl:9100"
            self.filter = fakeFilter()
            self.protocolHandler = Handler(self, sys.argv[1])
            
        def getLastPageCounter(self) :    
            """Fakes the return of a page counter."""
            return 0
        
    acc = fakeAccounter()            
    return acc.protocolHandler.retrieveInternalPageCounter()
    
if __name__ == "__main__" :            
    if len(sys.argv) != 2 :    
        sys.stderr.write("Usage :  python  %s  printer_ip_address\n" % sys.argv[0])
    else :    
        def _(msg) :
            return msg
            
        pagecounter = main(sys.argv[1])
        print "Internal page counter's value is : %s" % pagecounter
        
