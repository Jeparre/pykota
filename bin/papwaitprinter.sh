#! /bin/sh
#
# PyKota - Print Quotas for CUPS and LPRng
#
# (c) 2003, 2004, 2005, 2006, 2007 Jerome Alet <alet@librelogiciel.com>
# You're welcome to redistribute this software under the
# terms of the GNU General Public Licence version 2.0
# or, at your option, any higher version.
#
# You can read the complete GNU GPL in the file COPYING
# which should come along with this software, or visit
# the Free Software Foundation's WEB site http://www.fsf.org
#
# $Id: papwaitprinter.sh 3133 2007-01-17 22:19:42Z jerome $
#
PATH=$PATH:/bin:/usr/bin:/usr/local/bin:/opt/bin:/sbin:/usr/sbin
sleep 5;
until papstatus -p "$1" | grep -i idle >/dev/null ; do 
   sleep 1 ; 
done
