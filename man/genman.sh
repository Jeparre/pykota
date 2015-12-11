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
# $Id: genman.sh 3231 2007-07-24 10:46:05Z jerome $
#
for prog in pksetup pkrefund pknotify pkusers pkinvoice pkturnkey pkbcodes pkmail pkbanner autopykota dumpykota edpykota pykotme repykota warnpykota pkprinters pykosd ; do 
    echo $prog ;
    help2man --no-info --section=1 --manual "User Commands" --source="C@LL - Conseil Internet & Logiciels Libres" --output=$prog.1 $prog ; 
    cd ../po ;
    for dir in * ; do 
        if [ -d $dir ] ; then
            if [ -e $dir/pykota.po ] ; then
                echo "  $dir" ;
                cd ../man/$dir ;
                help2man --no-info --locale=$dir --section=1 --manual "User Commands" --source="C@LL - Conseil Internet & Logiciels Libres" --output=$prog.1 $prog ; 
                cd ../../po ;
            fi ;    
        fi ;     
    done
    cd ../man ;
    echo ;
done
