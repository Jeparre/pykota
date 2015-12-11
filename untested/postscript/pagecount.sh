#!/bin/sh
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
# $Id: pagecount.sh 3133 2007-01-17 22:19:42Z jerome $
#
#
#
# This script was freely adapted and modified from the printquota project 
# http://printquota.sourceforge.net for inclusion into PyKota.
#
# printquota (c) 2002-2003 Ahmet Ozturk & Cagatay Koksoy
# printquota is distributed under the GNU General Public License
#
# Usage : pagecount.sh <file.ps
#
(
(sed -n -e '/%!PS-Adobe-/,/\%\%EOF/p' | grep -E -v "/Duplex|PageSize")
echo currentdevice /PageCount gsgetdeviceprop == flush
) | gs -q -sDEVICE=bit -sOutputFile=/dev/null -r5 - | tail -1

