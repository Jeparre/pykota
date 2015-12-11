#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# PyKota
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
# $Id: checkdeps.py 3133 2007-01-17 22:19:42Z jerome $
#
#

import sys
import os

def checkModule(module) :
    """Checks if a Python module is available or not."""
    try :
        exec "import %s" % module
    except ImportError :    
        return 0
    else :    
        return 1
        
def checkCommand(command) :
    """Checks if a command is available or not."""
    input = os.popen("type %s 2>/dev/null" % command)
    result = input.read().strip()
    input.close()
    return result
    
def checkWithPrompt(prompt, module=None, command=None, helper=None) :
    """Tells the user what will be checked, and asks him what to do if something is absent."""
    sys.stdout.write("Checking for %s availability : " % prompt)
    sys.stdout.flush()
    if command is not None :
        result = checkCommand(command)
    elif module is not None :    
        result = checkModule(module)
    if result :    
        sys.stdout.write("OK\n")
    else :    
        sys.stdout.write("NO.\n")
        sys.stderr.write("ERROR : %s not available !\n" % prompt)
        sys.stdout.write("%s\n" % helper)
    
if __name__ == "__main__" :    
    print "Checking PyKota dependencies..."
    
    # checks if Python version is correct, we need >= 2.2
    if not (sys.version > "2.2") :
        sys.stderr.write("PyKota needs at least Python v2.2 !\nYour version seems to be older than that, please update.\nAborted !\n")
        sys.exit(-1)
        
    # checks if some needed Python modules are there or not.
    modulestocheck = [ ("Python-PygreSQL", "pg", "PygreSQL is mandatory if you want to use PostgreSQL as the quota database backend.\nSee http://www.pygresql.org"),
                       ("Python-SQLite", "pysqlite2", "Python-SQLite is mandatory if you want to use SQLite as the quota database backend.\nSee http://www.pysqlite.org"),
                       ("MySQL-Python", "MySQLdb", "MySQL-Python is mandatory if you want to use MySQL as the quota database backend.\nSee http://sourceforge.net/projects/mysql-python"),
                       ("Python-egenix-mxDateTime", "mx.DateTime", "eGenix' mxDateTime is mandatory for PyKota to work.\nSee http://www.egenix.com"),
                       ("Python-LDAP", "ldap", "Python-LDAP is mandatory if you plan to use an LDAP\ndirectory as the quota database backend.\nSee http://python-ldap.sf.net"),
                       ("Python-OSD", "pyosd", "Python-OSD is recommended if you plan to use the X Window On Screen Display\nprint quota reminder named pykosd. See http://repose.cx/pyosd/"),
                       ("Python-SNMP", "pysnmp", "Python-SNMP is recommended if you plan to use hardware\naccounting with printers which support SNMP.\nSee http://pysnmp.sf.net"),
                       ("Python-JAXML", "jaxml", "Python-JAXML is recommended if you plan to dump datas in the XML format.\nSee http://www.librelogiciel.com/software/"),
                       ("Python-ReportLab", "reportlab.pdfgen.canvas", "Python-ReportLab is required if you plan to have PyKota generate banners.\nSee http://www.reportlab.org/"),
                       ("Python-Imaging", "PIL.Image", "Python-Imaging is required if you plan to have PyKota generate banners.\nSee http://www.pythonware.com/downloads/"),
                       ("Python-Psyco", "psyco", "Python-Psyco speeds up parsing of print files, you should use it.\nSee http://psyco.sourceforge.net/"),
                       ("Python-pkpgcounter", "pkpgpdls", "Python-pkpgcounter is mandatory.\nGrab it from http://www.pykota.com/software/pkpgcounter/"),
                       ("Python-PAM", "PAM", "Python-PAM is recommended if you plan to use pknotify+PyKotIcon.\nGrab it from http://www.pangalactic.org/PyPAM/"),
                       ("Python-pkipplib", "pkipplib", "Python-pkipplib is now mandatory.\nGrab it from http://www.pykota.com/software/pkipplib/"),
                       ("Python-chardet", "chardet", "Python-chardet is recommended.\nGrab it from http://chardet.feedparser.org/"),
                     ]
    commandstocheck = [ ("GhostScript", "gs", "Depending on your configuration, GhostScript may be needed in different parts of PyKota."),
                        ("SNMP Tools", "snmpget", "SNMP Tools are needed if you want to use SNMP enabled printers."), 
                        ("Netatalk", "pap", "Netatalk is needed if you want to use AppleTalk enabled printers.")
                      ]
    for (name, module, helper) in modulestocheck :
        checkWithPrompt(name, module=module, helper=helper)
            
    # checks if some software are there or not.
    for (name, command, helper) in commandstocheck :
        checkWithPrompt(name, command=command, helper=helper)
            
