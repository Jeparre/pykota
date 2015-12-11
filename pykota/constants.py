# PyKota
# -*- coding: ISO-8859-15 -*-
#
# PyKota : Print Quotas for CUPS
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
# $Id: constants.py 3180 2007-05-29 21:03:12Z jerome $
#

"""This module contains the definitions of constants used by PyKota."""

STATUSSTABILIZATIONDELAY = 4.0 # time to sleep between two loops
STATUSSTABILIZATIONLOOPS = 5  # number of consecutive times the 'idle' status must be seen before we consider it to be stable
NOPRINTINGMAXDELAY = 60 # The printer must begin to print within 60 seconds by default.

def get(application, varname) :
    """Retrieves the value of a particular printer variable from configuration file, else a constant defined here."""
    pname = application.PrinterName
    try :
        value = getattr(application.config, "get%(varname)s" % locals())(pname)
        if value is None :
            raise TypeError     # Use hardcoded value
    except (TypeError, AttributeError) : # NB : AttributeError in testing mode because I'm lazy !
        value = globals().get(varname.upper())
        application.logdebug("No value defined for %(varname)s for printer %(pname)s, using %(value)s." % locals())
    return value    
