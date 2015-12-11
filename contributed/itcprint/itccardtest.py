#! /usr/bin/python
#
# itccardtest.py
# (c) 2007 George Farris <farrisg@shaw.ca>	
#
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


# This documents and provides a demo of the protocol used to maniplulate
# the ITC Print  2015 smart card reader, http://www.itcsystems.com/smart-card-stored.html
# The  2015 is connected to the serial port of the PC to charge for things like 
# computer time usage, pay-for-print, cash registers sales, etc.
#
# The following description assumes that "Host" is the PC and Reader is the 2015
#
# ----------------------------------------------------------------------------------------------------- 
# Poll card reader for indication of card insertion 
# -----------------------------------------------------------------------------------------------------
#   Transmit from Host
#     Char line      : <STX><NUL><SOH><SOH><ETX><NUL><BEL><EOT> 
#     Hex translation: 0x02 0x00 0x01 0x01 0x03 0x00 0x07 0x04
#   Receive from Reader
#     No card inserted
#       Char line      : <STX><NUL><SOH>@<ETX><NUL>F<EOT> 
#       Hex translation: 0x02 0x00 0x01 0x40 0x03 0x00 0x46 0x04
#     Card Inserted
#       Char line      : <STX><NUL><SOH>@<ETX><NUL>F<EOT> 
#       Hex translation: 0x02 0x00 0x01 0x40 0x03 0x00 0x46 0x04
# =====================================================================================================


# ----------------------------------------------------------------------------------------------------- 
# Request current dollar(1) value stored on card
# ----------------------------------------------------------------------------------------------------- 
#   Transmit from Host
#     Char line      : <STX><NUL><SOH>!<ETX><NUL>'<EOT> 
#     Hex translation: 0x02 0x00 0x01 0x21 0x03 0x00 0x27 0x04
#   Receive from Reader
#     Char line      : <STX><NUL><SOH><NUL><NUL><NUL><NUL><NUL><NUL><DLE>h<SOH><ETX><NUL><DEL><EOT> 
#     Hex translation: 0x02 0x00 0x01 0x00 0x00 0x00 0x00 0x00 0x00 0x10 0x68 0x01 0x03 0x00 0x7F 0x04
#                                     [  Dollar value in this case 0x10 0x68 ]
#                                     [     0x1068 = 4200 = $4.20            ]
#                                     [______________________________________]
# =====================================================================================================


# -----------------------------------------------------------------------------------------------------
# Update Reader with new dollar value - must be less than what is stored on card
# -----------------------------------------------------------------------------------------------------
#   Transmit from Host 
#     Char line      : <STX><NUL><SOH>$<NUL><NUL><NUL><NUL><NUL><NUL><DLE><EOT><SOH><ETX><NUL>?<FF> 
#     Hex translation: 0x02 0x00 0x01 0x24 0x00 0x00 0x00 0x00 0x00 0x00 0x10 0x04 0x01 0x03 0x00 0x3F 0x0C
#                                          [  Dollar value in this case 0x10 0x04 ]
#                                          [     0x1004 = 4100 = $4.10            ]
#                                          [______________________________________]
#
#   Receive from successful transaction from Reader
#     Char line      : <STX><NUL><SOH><SYN><ETX><NUL><FS><BS>
#     Hex translation: 0x02 0x00 0x01 0x16 0x03 0x00 0x1C 0x08
# =====================================================================================================


# -----------------------------------------------------------------------------------------------------
# Eject card from Reader
# -----------------------------------------------------------------------------------------------------
#   Transmit from Host 
#     Char line      : <STX><NUL><SOH><SPACE><ETX><NUL>&<EOT>
#     Hex translation: 0x02 0x00 0x01 0x20 0x03 0x00 0x26 0x04
#   Receive from Reader
#     Char line      : <STX><NUL><SOH><SYN><ETX><NUL><FS><BS> 
#     Hex translation: 0x02 0x00 0x01 0x16 0x03 0x00 0x1C 0x08 
# =====================================================================================================

# (1) Currency can be set from the card reader keypad

import sys, os, serial, string, binascii, time, tty, termios

ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
#x = ser.read()          #read one byte

print "Main loop..."
print "  Waiting for card to be inserted..."
ser.write(binascii.a2b_hex("0200010103000704"))
s = ser.read(15)


while binascii.b2a_hex(s) == "0200014003004604":
	time.sleep(2)
	#print binascii.b2a_hex(s)
	ser.write(binascii.a2b_hex("0200010103000704"))
	#print "Tx -> 0200010103000704"
	s = ser.read(15)
	#print "Rx -> %s" % binascii.b2a_hex(s)

if binascii.b2a_hex(s) == "0200016c0300721c":
	print ""
	print "  Card is inserted..."
else:
	print "  Card Error..."
	exit(0)

# Get current value from card
ser.write(binascii.a2b_hex("0200012103002704"))
s1 = ser.read(20)

#020001000000000000 125c 010300 7538 = $4.700
#                   ^^^^ 4700 in decimal
#020001000000000000 0000 010300 0704 = $0.000
#020001000000000000 1068 010300 7F04 = $4.200
#020001000000000000 1004 010300 7F04 = $4.100
#print binascii.b2a_hex(s1[3:11])
print "  %s%.2f" % ("Card valued at -> $",float(string.atoi(binascii.b2a_hex(s1[3:11]), 16))/1000)

print "  Press 'e' to eject the card..."
# Need comms to contiune to keep card in machine.
# This loop keeps the card in until it stops so basically the print 
# job can release the card after it is finished
# The next three lines set the terminal up so one can poll the keyboard
fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)
tty.setraw(sys.stdin.fileno())

while binascii.b2a_hex(s) == "0200016c0300721c":
	if sys.stdin.read(1) == 'e':
		break
	time.sleep(1)
	#print binascii.b2a_hex(s)
	ser.write(binascii.a2b_hex("0200010103000704"))
	#print "Tx -> 0200010103000704"
	s = ser.read(15)
	#print "Rx -> %s" % binascii.b2a_hex(s)
# Reset the terminal after
termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# Eject card
ser.write(binascii.a2b_hex("0200012003002604"))
s2 = ser.read(20)
#print "Rx -> %s" % binascii.b2a_hex(s2)
print "  Ejecting card ..."

# okay so we have a card with $4.70 on it, decrement it to $4.10
#ser.write(binascii.a2b_hex("0200012400000000000010040103003F0C"))
#s2 = ser.read(20)
#print binascii.b2a_hex(s2)
ser.close()
print "Goodbye..."

