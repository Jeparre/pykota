#! /bin/sh

# This script was generously contributed by Jem E. Berkes.
# It can't work as-is with PyKota, you first have to adapt it
# and this may require some work on your part.

# It is aimed at printers which support the PJL language, which
# are plugged through a bidirectionnal parallel port.

# Read what Jem has to say about it :

# It seems that network sockets or some other control specific method is the 
# best way to query the printers. What I have is a bit (well, more than just 
# a bit) of a brute forced solution. However, it has been working for us for 
# about a month and only needs a bidirectional /dev/lp0

# I'm not at all happy about the sleep's I have in there. On occasion, there 
# are missing page counts in the log but since the * next * user to print 
# gets a good pagecount, the parser (a separate program) finds the 
# responsibility.
# 
# If you find a way to improve what I have, please let me know. Note that 
# when this is invoked from printcap, it's expecting that the data coming it 
# at stdin is a pre-formatted print job (the Windows machines do that 
# anyway).

# Copyright (C) 2003 Jem E. Berkes
# jb2003@pc9.org
# This script queries the HP LaserJet 1200 for pagecount, then prints a
# pre-formatted job
# Log format: DATE\tUSERNAME\tPRECOUNT

PRINTDEV=/dev/lp0
LOGFILE=$SPOOL_DIR/pagelog

echo -e "\33%-12345X@PJL\n@PJL INFO VARIABLES\n\33%-12345X" > $PRINTDEV
sleep 1
cat $PRINTDEV > /dev/null
echo -e "\33%-12345X@PJL\n@PJL INFO PAGECOUNT\n\33%-12345X" > $PRINTDEV
sleep 1
PAGECOUNT=`cat $PRINTDEV | grep "^[0-9]"`
USERID=`echo $1 | cut -b 3- | sed "s/@.*//"`
echo -e "`date \"+%Y-%m-%d %H:%M:%S\"`\t$USERID\t$PAGECOUNT" >> $LOGFILE
cat > $PRINTDEV


