#! /bin/sh
#
# $Id: netatalk.sh 2146 2005-03-06 16:35:30Z jerome $
#
# The following was adapted from a post found on usenet.
#
# It works with my Apple LaserWriter 16/600 PS and with
# my HP LasetJet 2100 TN with AppleTalk enabled.
#
# As always, YMMV.
# 
echo Please uncomment one of the lines, adapt the script and restart.
echo You can get AppleTalk printer\'s names with the nbplkup command.
# /usr/bin/pap -p "RAMPAL-16/600:LaserWriter" pagecount.ps 2>/dev/null | grep -v status | grep -v Connect
# /usr/bin/pap -p "LaserJet 2100 NT:LaserWriter" pagecount.ps 2>/dev/null | grep -v status | grep -v Connect
