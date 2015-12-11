#! /bin/sh
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
# $Id: clean.sh 3156 2007-03-23 15:16:30Z jerome $

# Use this to clean the tree from temporary files

rm -f MANIFEST ChangeLog
find . -name "*.bak" -exec rm -f {} \;
find . -name "*~" -exec rm -f {} \;
find . -name "*.pyc" -exec rm -f {} \;
find . -name "*.pyo" -exec rm -f {} \;
find . -name "*.jem" -exec rm -f {} \;
find docs -name "*.html" -exec rm -f {} \;
find docs -name "*.pdf" -exec rm -f {} \;
find docs -name "*.tex" -exec rm -f {} \;
find docs -name "*.dvi" -exec rm -f {} \;
rm -fr build dist
rm -fr debian/tmp/
rm -fr docs/pykota/ docs/pykota.junk/
