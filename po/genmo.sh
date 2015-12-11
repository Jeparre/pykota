#! /bin/sh
#
# PyKota - Print Quotas for CUPS and LPRng
#
# (c) 2003, 2004, 2005, 2006 Jerome Alet <alet@librelogiciel.com>
# You're welcome to redistribute this software under the
# terms of the GNU General Public Licence version 2.0
# or, at your option, any higher version.
#
# You can read the complete GNU GPL in the file COPYING
# which should come along with this software, or visit
# the Free Software Foundation's WEB site http://www.fsf.org
#
# $Id: genmo.sh 3110 2006-12-03 09:30:20Z jerome $
#
for dir in * ; do 
    if [ -d $dir ] ; then
        if [ -e $dir/pykota.po ] ; then
            echo -n $dir ;
            cd $dir ;
            chmod 644 *.?o ;
            msgmerge --no-location --no-fuzzy-matching --output-file=pykota.po.new pykota.po ../pykota.pot ;
            mv pykota.po.new pykota.po ;
            /bin/rm -f pykota.mo ;
            msgfmt -o pykota.mo pykota.po ;
            cd .. ;
        fi ;    
    fi ;     
done
