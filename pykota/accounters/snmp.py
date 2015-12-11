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
# $Id: snmp.py 3395 2008-07-10 20:03:54Z jerome $
#
#

"""This module is used to extract printer's internal page counter
and status informations using SNMP queries.

The values extracted are defined at least in RFC3805 and RFC2970.
"""


import sys
import os
import time
import select
import socket

try :
    from pysnmp.entity.rfc3413.oneliner import cmdgen
except ImportError :    
    hasV4 = False
    try :
        from pysnmp.asn1.encoding.ber.error import TypeMismatchError
        from pysnmp.mapping.udp.error import SnmpOverUdpError
        from pysnmp.mapping.udp.role import Manager
        from pysnmp.proto.api import alpha
    except ImportError :
        raise RuntimeError, "The pysnmp module is not available. Download it from http://pysnmp.sf.net/"
else :
    hasV4 = True

from pykota import constants

#                      
# Documentation taken from RFC 3805 (Printer MIB v2) and RFC 2790 (Host Resource MIB)
#
pageCounterOID = "1.3.6.1.2.1.43.10.2.1.4.1.1"  # SNMPv2-SMI::mib-2.43.10.2.1.4.1.1
hrPrinterStatusOID = "1.3.6.1.2.1.25.3.5.1.1.1" # SNMPv2-SMI::mib-2.25.3.5.1.1.1
printerStatusValues = { 1 : 'other',
                        2 : 'unknown',
                        3 : 'idle',
                        4 : 'printing',
                        5 : 'warmup',
                      }
hrDeviceStatusOID = "1.3.6.1.2.1.25.3.2.1.5.1" # SNMPv2-SMI::mib-2.25.3.2.1.5.1
deviceStatusValues = { 1 : 'unknown',
                       2 : 'running',
                       3 : 'warning',
                       4 : 'testing',
                       5 : 'down',
                     }  
hrPrinterDetectedErrorStateOID = "1.3.6.1.2.1.25.3.5.1.2.1" # SNMPv2-SMI::mib-2.25.3.5.1.2.1
printerDetectedErrorStateValues = [ { 128 : 'Low Paper',
                                       64 : 'No Paper',
                                       32 : 'Low Toner',
                                       16 : 'No Toner',
                                        8 : 'Door Open',
                                        4 : 'Jammed',
                                        2 : 'Offline',
                                        1 : 'Service Requested',
                                    },
                                    { 128 : 'Input Tray Missing',
                                       64 : 'Output Tray Missing',
                                       32 : 'Marker Supply Missing',
                                       16 : 'Output Near Full',
                                        8 : 'Output Full',
                                        4 : 'Input Tray Empty',
                                        2 : 'Overdue Preventive Maintainance',
                                        1 : 'Not Assigned in RFC3805',
                                    },
                                  ]  
                                  
# The default error mask to use when checking error conditions.
defaultErrorMask = 0x4fcc # [ 'No Paper',
                          #   'Door Open',
                          #   'Jammed',
                          #   'Offline',
                          #   'Service Requested',
                          #   'Input Tray Missing',
                          #   'Output Tray Missing',
                          #   'Output Full',
                          #   'Input Tray Empty',
                          # ]
                          
# WARNING : some printers don't support this one :                  
prtConsoleDisplayBufferTextOID = "1.3.6.1.2.1.43.16.5.1.2.1.1" # SNMPv2-SMI::mib-2.43.16.5.1.2.1.1
class BaseHandler :
    """A class for SNMP print accounting."""
    def __init__(self, parent, printerhostname, skipinitialwait=False) :
        self.parent = parent
        self.printerHostname = printerhostname
        self.skipinitialwait = skipinitialwait
        try :
            self.community = self.parent.arguments.split(":")[1].strip()
        except IndexError :    
            self.community = "public"
        self.port = 161
        self.initValues()
        
    def initValues(self) :    
        """Initializes SNMP values."""
        self.printerInternalPageCounter = None
        self.printerStatus = None
        self.deviceStatus = None
        self.printerDetectedErrorState = None
        self.timebefore = time.time()   # resets timer also in case of error
        
    def retrieveSNMPValues(self) :    
        """Retrieves a printer's internal page counter and status via SNMP."""
        raise RuntimeError, "You have to overload this method."
        
    def extractErrorStates(self, value) :    
        """Returns a list of textual error states from a binary value."""
        states = []
        for i in range(min(len(value), len(printerDetectedErrorStateValues))) :
            byte = ord(value[i])
            bytedescription = printerDetectedErrorStateValues[i]
            for (k, v) in bytedescription.items() :
                if byte & k :
                    states.append(v)
        return states            
        
    def checkIfError(self, errorstates) :    
        """Checks if any error state is fatal or not."""
        if errorstates is None :
            return True
        else :
            try :
                errormask = self.parent.filter.config.getPrinterSNMPErrorMask(self.parent.filter.PrinterName)
            except AttributeError : # debug mode    
                errormask = defaultErrorMask
            if errormask is None :
                errormask = defaultErrorMask
            errormaskbytes = [ chr((errormask & 0xff00) >> 8),
                               chr((errormask & 0x00ff)),
                             ]
            errorConditions = self.extractErrorStates(errormaskbytes)
            self.parent.filter.logdebug("Error conditions for mask 0x%04x : %s" \
                                               % (errormask, errorConditions))
            for err in errorstates :
                if err in errorConditions :
                    self.parent.filter.logdebug("Error condition '%s' encountered. PyKota will wait until this problem is fixed." % err)
                    return True
            self.parent.filter.logdebug("No error condition matching mask 0x%04x" % errormask)
            return False    
        
    def waitPrinting(self) :
        """Waits for printer status being 'printing'."""
        statusstabilizationdelay = constants.get(self.parent.filter, "StatusStabilizationDelay")
        noprintingmaxdelay = constants.get(self.parent.filter, "NoPrintingMaxDelay")
        if not noprintingmaxdelay :
            self.parent.filter.logdebug("Will wait indefinitely until printer %s is in 'printing' state." % self.parent.filter.PrinterName)
        else :    
            self.parent.filter.logdebug("Will wait until printer %s is in 'printing' state or %i seconds have elapsed." % (self.parent.filter.PrinterName, noprintingmaxdelay))
        previousValue = self.parent.getLastPageCounter()
        firstvalue = None
        while 1:
            self.retrieveSNMPValues()
            statusAsString = printerStatusValues.get(self.printerStatus)
            if statusAsString in ('printing', 'warmup') :
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
                    elif noprintingmaxdelay \
                         and ((time.time() - self.timebefore) > noprintingmaxdelay) \
                         and not self.checkIfError(self.printerDetectedErrorState) :
                        # More than X seconds without the printer being in 'printing' mode
                        # We can safely assume this won't change if printer is now 'idle'
                        pstatusAsString = printerStatusValues.get(self.printerStatus)
                        dstatusAsString = deviceStatusValues.get(self.deviceStatus)
                        if (pstatusAsString == 'idle') or \
                            ((pstatusAsString == 'other') and \
                             (dstatusAsString == 'running')) :
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
        idle_num = idle_flag = 0
        while 1 :
            self.retrieveSNMPValues()
            pstatusAsString = printerStatusValues.get(self.printerStatus)
            dstatusAsString = deviceStatusValues.get(self.deviceStatus)
            idle_flag = 0
            if (not self.checkIfError(self.printerDetectedErrorState)) \
               and ((pstatusAsString == 'idle') or \
                         ((pstatusAsString == 'other') and \
                          (dstatusAsString == 'running'))) :
                idle_flag = 1       # Standby / Powersave is considered idle
            if idle_flag :    
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
        """Returns the page counter from the printer via internal SNMP handling."""
        try :
            if (os.environ.get("PYKOTASTATUS") != "CANCELLED") and \
               (os.environ.get("PYKOTAACTION") == "ALLOW") and \
               (os.environ.get("PYKOTAPHASE") == "AFTER") and \
               self.parent.filter.JobSizeBytes :
                self.waitPrinting()
            self.waitIdle()    
        except :    
            self.parent.filter.printInfo(_("SNMP querying stage interrupted. Using latest value seen for internal page counter (%s) on printer %s.") % (self.printerInternalPageCounter, self.parent.filter.PrinterName), "warn")
            raise
        return self.printerInternalPageCounter
            
if hasV4 :            
    class Handler(BaseHandler) :
        """A class for pysnmp v4.x"""
        def retrieveSNMPValues(self) :
            """Retrieves a printer's internal page counter and status via SNMP."""
            try :
                errorIndication, errorStatus, errorIndex, varBinds = \
                 cmdgen.CommandGenerator().getCmd(cmdgen.CommunityData("pykota", self.community, 0), \
                                                  cmdgen.UdpTransportTarget((self.printerHostname, self.port)), \
                                                  tuple([int(i) for i in pageCounterOID.split('.')]), \
                                                  tuple([int(i) for i in hrPrinterStatusOID.split('.')]), \
                                                  tuple([int(i) for i in hrDeviceStatusOID.split('.')]), \
                                                  tuple([int(i) for i in hrPrinterDetectedErrorStateOID.split('.')]))
            except socket.gaierror, msg :                                      
                errorIndication = repr(msg)
            except :                                      
                errorIndication = "Unknown SNMP/Network error. Check your wires."
            if errorIndication :                                                  
                self.parent.filter.printInfo("SNMP Error : %s" % errorIndication, "error")
                self.initValues()
            elif errorStatus :    
                self.parent.filter.printInfo("SNMP Error : %s at %s" % (errorStatus.prettyPrint(), \
                                                                        varBinds[int(errorIndex)-1]), \
                                             "error")
                self.initValues()
            else :                                 
                self.printerInternalPageCounter = max(self.printerInternalPageCounter, int(varBinds[0][1].prettyPrint() or "0"))
                self.printerStatus = int(varBinds[1][1].prettyPrint())
                self.deviceStatus = int(varBinds[2][1].prettyPrint())
                self.printerDetectedErrorState = self.extractErrorStates(str(varBinds[3][1]))
                self.parent.filter.logdebug("SNMP answer decoded : PageCounter : %s  PrinterStatus : '%s'  DeviceStatus : '%s'  PrinterErrorState : '%s'" \
                     % (self.printerInternalPageCounter, \
                        printerStatusValues.get(self.printerStatus), \
                        deviceStatusValues.get(self.deviceStatus), \
                        self.printerDetectedErrorState))
else :
    class Handler(BaseHandler) :
        """A class for pysnmp v3.4.x"""
        def retrieveSNMPValues(self) :    
            """Retrieves a printer's internal page counter and status via SNMP."""
            ver = alpha.protoVersions[alpha.protoVersionId1]
            req = ver.Message()
            req.apiAlphaSetCommunity(self.community)
            req.apiAlphaSetPdu(ver.GetRequestPdu())
            req.apiAlphaGetPdu().apiAlphaSetVarBindList((pageCounterOID, ver.Null()), \
                                                        (hrPrinterStatusOID, ver.Null()), \
                                                        (hrDeviceStatusOID, ver.Null()), \
                                                        (hrPrinterDetectedErrorStateOID, ver.Null()))
            tsp = Manager()
            try :
                tsp.sendAndReceive(req.berEncode(), \
                                   (self.printerHostname, self.port), \
                                   (self.handleAnswer, req))
            except (SnmpOverUdpError, select.error), msg :    
                self.parent.filter.printInfo(_("Network error while doing SNMP queries on printer %s : %s") % (self.printerHostname, msg), "warn")
                self.initValues()
            tsp.close()
        
        def handleAnswer(self, wholeMsg, notusedhere, req):
            """Decodes and handles the SNMP answer."""
            ver = alpha.protoVersions[alpha.protoVersionId1]
            rsp = ver.Message()
            try :
                rsp.berDecode(wholeMsg)
            except TypeMismatchError, msg :    
                self.parent.filter.printInfo(_("SNMP message decoding error for printer %s : %s") % (self.printerHostname, msg), "warn")
                self.initValues()
            else :
                if req.apiAlphaMatch(rsp):
                    errorStatus = rsp.apiAlphaGetPdu().apiAlphaGetErrorStatus()
                    if errorStatus:
                        self.parent.filter.printInfo(_("Problem encountered while doing SNMP queries on printer %s : %s") % (self.printerHostname, errorStatus), "warn")
                    else:
                        self.values = []
                        for varBind in rsp.apiAlphaGetPdu().apiAlphaGetVarBindList():
                            self.values.append(varBind.apiAlphaGetOidVal()[1].rawAsn1Value)
                        try :    
                            # keep maximum value seen for printer's internal page counter
                            self.printerInternalPageCounter = max(self.printerInternalPageCounter, self.values[0])
                            self.printerStatus = self.values[1]
                            self.deviceStatus = self.values[2]
                            self.printerDetectedErrorState = self.extractErrorStates(self.values[3])
                            self.parent.filter.logdebug("SNMP answer decoded : PageCounter : %s  PrinterStatus : '%s'  DeviceStatus : '%s'  PrinterErrorState : '%s'" \
                                 % (self.printerInternalPageCounter, \
                                    printerStatusValues.get(self.printerStatus), \
                                    deviceStatusValues.get(self.deviceStatus), \
                                    self.printerDetectedErrorState))
                        except IndexError :    
                            self.parent.filter.logdebug("SNMP answer is incomplete : %s" % str(self.values))
                            pass
                        else :    
                            return 1
                    
def main(hostname) :
    """Tries SNMP accounting for a printer host."""
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
            self.arguments = "snmp:public"
            self.filter = fakeFilter()
            self.protocolHandler = Handler(self, hostname)
            
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
