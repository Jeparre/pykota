#! /usr/bin/python
#
# itcxfer.py
# (c) 2007 George Farris <farrisg@shaw.ca>	
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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
#                                          [  Dollar value in this case 0x10 0x04 ]  ________[    chkm]__________
#                                          [     0x1004 = 4100 = $4.10            ] [ checksum add bytes 1 to 15 ]
#                                          [______________________________________] [____________________________]
#
#   Receive from successful transaction from Reader
#     Char line      : <STX><NUL><SOH><SYN><ETX><NUL><FS><BS>
#     Hex translation: 0x02 0x00 0x01 0x16 0x03 0x00 0x1C 0x08
# =====================================================================================================
#0200011703001d08

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

import sys, os, serial, string, binascii, time
import gtk, gtk.glade, gobject, pg

# -------------- User modifiable settings -----------------------------
# Database server settings
HOST = '10.31.50.3'
PORT = 5432
DBNAME = 'pykota'
USER = 'pykotaadmin'
PASS = 'secret'

# Search database as you type function
# These settings control if a database search of the username is performed 
# automatically when they reach a desired length.  This helps in a University
# setting where all student username are the same length.
SEARCH = True
SEARCHLENGTH = 6

# Serial port settings
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600

# Set this to True or False
# If set to True it will not update any cards
TESTMODE = True

# ------------- End of user modifiable settings -----------------------

class gui:
	def __init__(self):
		self.cardstate = 0  # 0 not inserted, 1 inserted
		
		self.gladefile = "itcprint.glade"  
		self.xml = gtk.glade.XML(self.gladefile) 

		self.window = self.xml.get_widget("MainWindow")
		self.utext = self.xml.get_widget("UsernameEntry")
		self.cardlabel = self.xml.get_widget("CardBalanceLabel")
		self.printlabel = self.xml.get_widget("PrintBalanceLabel")
		self.spinbutton = self.xml.get_widget("Spinbutton")
		self.xferbutton = self.xml.get_widget("TransferButton")
		
		self.spinbutton.set_range(0,0)
		self.spinbutton.set_sensitive(False)
		self.xferbutton.set_sensitive(False)
		self.cardlabel.set_label('<big><b>unknown</b></big>')
		self.printlabel.set_label('<big><b>unknown</b></big>')
		
		self.cardbalance = 0.0
		self.validuser = False
		self.addbalance = 0.0

		if not TESTMODE :
			print "We are in test mode...."

		self.db = pgsql()						
		self.sc = smartcard(self.db)
		
		#If you wanted to pass an argument, you would use a tuple like this:
    	# dic = { "on button1_clicked" : (self.button1_clicked, arg1,arg2) }
		dic = { "on_TransferButton_clicked" : self.xferbutton_clicked,
				"on_GetbalanceButton_clicked" : self.getcardbalance_clicked,
				"on_EjectButton_clicked" : self.ejectbutton_clicked,
				"on_quit_activate" : (gtk.main_quit),
				"on_UsernameEntry_changed" : self.username_changed,
				"on_Spinbutton_value_changed" : self.spinvalue_changed,
				"on_UsernameEntry_focus_out_event" : self.username_entered,
				"on_UsernameEntry_activate" : (self.username_entered, None),
				"on_ItcPrint_destroy" : (gtk.main_quit) }
				
		self.xml.signal_autoconnect (dic)
		
		self.completion = gtk.EntryCompletion()
  		self.utext.set_completion(self.completion)
  		self.liststore = gtk.ListStore(gobject.TYPE_STRING)
  		self.completion.set_model(self.liststore)
  		self.completion.set_text_column(0)
  		self.completion.connect("match-selected", self.username_found)
  		
  		#self.liststore.append(['string text'])
  		
		return

	# Don't allow the transfer button to be senitive unless there is a valid value
	def spinvalue_changed(self, widget):
		if self.spinbutton.get_value() > 0.0:
			self.xferbutton.set_sensitive(True)
		else:
			self.xferbutton.set_sensitive(False)
		
  	# I might want to do username search as you type later
	def username_changed (self, widget):
		if SEARCH :
			if len(self.utext.get_text()) == SEARCHLENGTH:
				if not self.db.alreadyopen:
					if not self.db.pgopen():
						result = gtk.RESPONSE_CANCEL
						dlg = gtk.MessageDialog(None,gtk.DIALOG_MODAL |
							gtk.DIALOG_DESTROY_WITH_PARENT,gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, 
							"Cannot connect or open the database.\nPlease contact technical suppport...", )
						result = dlg.run()
						dlg.destroy()
						return
				if self.db.get_userslist(self.utext.get_text(), self.liststore):
					pass
				else:
					return
				
				#self.username_entered(None, None)
	
	def username_found(self, completion, model, iter):
		self.username = model[iter][0], 'was selected'
		self.utext.set_text(model[iter][0])
		self.username_entered(self, None)
					
	def username_entered (self, widget, event):
		uname = self.utext.get_text()
		print "Username is ->", uname
		# This is where we need to look up username in wbinfo
		

		if not self.db.alreadyopen:
			if not self.db.pgopen():
				result = gtk.RESPONSE_CANCEL
				dlg = gtk.MessageDialog(None,gtk.DIALOG_MODAL |
					gtk.DIALOG_DESTROY_WITH_PARENT,gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, 
					"Cannot connect or open the database.\nPlease contact technical suppport...", )
				result = dlg.run()
				dlg.destroy()
				return
			
		if self.db.get_pykotaid(uname):
			self.validuser = True
		else:
			result = gtk.RESPONSE_CANCEL
			dlg = gtk.MessageDialog(None,gtk.DIALOG_MODAL |
				gtk.DIALOG_DESTROY_WITH_PARENT,gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE, 
				"Your username is invalid or does not exist.\nPlease try re-entering it", )
			result = dlg.run()
			dlg.destroy()
			return
		
		#self.liststore.append(['string text'])
			
		balance = self.db.get_pykotabalance()
		if balance :
			self.printlabel.set_label("%s%.2f%s" % ("<big><b>$",balance,"</b></big>"))
		else:
			result = gtk.RESPONSE_CANCEL
			dlg = gtk.MessageDialog(None,gtk.DIALOG_MODAL |
				gtk.DIALOG_DESTROY_WITH_PARENT,gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, 
				"Cannot retrieve your printing balance.\nPlease contact technical suppport...", )
			result = dlg.run()
			dlg.destroy()
			self.validuser = False
			return
					
		if not self.db.get_pykotalifebalance():
			result = gtk.RESPONSE_CANCEL
			dlg = gtk.MessageDialog(None,gtk.DIALOG_MODAL |
				gtk.DIALOG_DESTROY_WITH_PARENT,gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, 
				"Cannot retrieve your life time printing balance.\nPlease contact technical suppport...", )
			result = dlg.run()
			dlg.destroy()
			self.validuser = False
			return
			
		# Only set transfer button if both card balance and username valid
		if  self.cardbalance > 0.1 and self.validuser:
			self.spinbutton.set_sensitive(True)

			
	def xferbutton_clicked (self, widget):
		print "xfer button clicked...."
		addbalance = self.spinbutton.get_value()
		
		if not self.db.set_pykotabalances(addbalance):
			result = gtk.RESPONSE_CANCEL
			dlg = gtk.MessageDialog(None,gtk.DIALOG_MODAL |
				gtk.DIALOG_DESTROY_WITH_PARENT,gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, 
				"An error was encountered while updating your record.\nPlease contact technical support.")
			result = dlg.run()
			dlg.destroy()
			return
			
		self.sc.set_balance(addbalance, self.cardbalance)
		time.sleep(3)
		self.ejectbutton_clicked(None)
		self.spinbutton.set_range(0,float(0))
		
				
	def getcardbalance_clicked(self, widget):
		if self.sc.checkforcardready():
			self.sc.waitforcardready()
			self.cardbalance = self.sc.get_balance()
			self.cardlabel.set_label("%s%.2f%s" % ("<big><b>$",self.cardbalance,"</b></big>"))
			self.cardstate = 1
			self.source_id = gobject.timeout_add(2000, self.sc.inhibit_eject)
			# Only allow the spin button to go up to the value of the card
			self.spinbutton.set_range(0,float(self.cardbalance))
		
		if self.cardbalance > 0.1 and self.validuser:
			self.spinbutton.set_sensitive(True)
			
	def ejectbutton_clicked(self, widget):
		self.sc.eject_card()
		self.cardlabel.set_label('<big><b>unknown</b></big>')
		self.printlabel.set_label('<big><b>unknown</b></big>')
		self.cardstate = 0
		self.cardbalance = 0.0
		self.validuser = False
		self.utext.set_text('')
		self.addbalance = 0.0
		self.spinbutton.set_range(0,0)
		self.spinbutton.set_sensitive(False)
		self.xferbutton.set_sensitive(False)
		
		self.db.pgclose()
				
		# Is it possible this might not be set
		try:
			gobject.source_remove(self.source_id)
		except:
			pass
		
		
class smartcard:
	def __init__(self, sql):
		try:
			self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
		except:
			result = gtk.RESPONSE_CANCEL
			dlg = gtk.MessageDialog(None,gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, 
				gtk.BUTTONS_CLOSE, "Fatal error - Could not open serial port...", )
			result = dlg.run()
			dlg.destroy()
			exit(1)
			
	# Need comms to contiune to keep card in machine.
	# This loop keeps the card in until it stops so basically the print 
	# job can release the card after it is finished
	def checkforcardready(self):
		# A bit of a sleep here prevents the card dialog popping up if 
		# the card is already inserted.
		time.sleep(1)
		self.ser.write(binascii.a2b_hex("0200010103000704"))
		s = self.ser.read(8)

		if binascii.b2a_hex(s) == "0200014003004604":
			result = gtk.RESPONSE_CANCEL
			dlg = gtk.MessageDialog(None,gtk.DIALOG_MODAL |
				gtk.DIALOG_DESTROY_WITH_PARENT,gtk.MESSAGE_INFO, gtk.BUTTONS_OK_CANCEL, "Please insert your card...", )
			result = dlg.run()
			if (result==gtk.RESPONSE_OK):
				dlg.destroy()
				return 1
			else:
				dlg.destroy()
				return 0
		if binascii.b2a_hex(s) == "0200016c0300721c":
			return 1
				
	def waitforcardready(self):
		print "  Waiting for card to be inserted..."
		self.ser.write(binascii.a2b_hex("0200010103000704"))
		s = self.ser.read(8)

		while binascii.b2a_hex(s) == "0200014003004604":
			#time.sleep(2)
			#print binascii.b2a_hex(s)
			self.ser.write(binascii.a2b_hex("0200010103000704"))
			#print "Tx -> 0200010103000704"
			s = self.ser.read(8)
			#print "Rx -> %s" % binascii.b2a_hex(s)
		
		if binascii.b2a_hex(s) == "0200016c0300721c":
			print "  Card is inserted..."
			return 1
		else:
			print "  Card Error..."
			return 0

	# Get current value from card
	def get_balance(self):
		# TODO Test checksum
		self.ser.write(binascii.a2b_hex("0200012103002704"))
		s1 = self.ser.read(16)
		print binascii.b2a_hex(s1)
		print "  %s%.2f" % ("Card valued at -> $",float(string.atoi(binascii.b2a_hex(s1[3:11]), 16))/1000)
		return float(string.atoi(binascii.b2a_hex(s1[3:11]), 16))/1000

	def set_balance(self, subvalue, cardbalance):
		newbalance = cardbalance - subvalue
		a = (str(newbalance)).split('.')
		b = a[0] + string.ljust(a[1],3,'0')
		c = "%X" % (string.atoi(b))
		d = string.zfill(c,16)
		chksum = self.checksum(d) 
		decrementvalue = "02000124" + d + "0103" + chksum + "0C"

		if TESTMODE:
			print "Current card balance -> ", cardbalance
			print "Amount to subtract from card -> ", subvalue
			print "New card balance -> ", newbalance
			print "Checksum -> ", chksum
			print "Sent to card -> ",decrementvalue 
			return
		
		print "Sent to card -> ",decrementvalue 
		self.ser.write(binascii.a2b_hex(decrementvalue))
		s2 = self.ser.read(8)
		print "Result -> ", binascii.b2a_hex(s2)

	def eject_card(self):
		print "  Ejecting card ..."
		self.ser.write(binascii.a2b_hex("0200012003002604"))
		s2 = self.ser.read(8)
		#print "Rx -> %s" % binascii.b2a_hex(s2)

	def inhibit_eject(self):
		self.ser.write(binascii.a2b_hex("0200010103000704"))
		s = self.ser.read(8)
		return True

	def checksum(self, s):
		i = 0
		j = int('0', 16)

		while i < len(s): 
			j = int(s[i:i+2], 16) + j
			i = i+2
		j = j + int('2B', 16)  # 2B is the header command and footer bytes previously added
		return string.zfill(("%X" % j), 4)
	
	def close_port(self):	
		self.ser.close()


class pgsql:
	def __init__(self):
		self.sql = None
		self.username = ''
		self.pykotauid = ''
		self.balance = 0
		self.lifebalance = 0
		self.alreadyopen = False
		
	def pgopen(self):
		try:
			self.sql = pg.connect(dbname=DBNAME, host=HOST, port=PORT, user=USER, passwd=PASS)
			self.alreadyopen = True
			return True
		except:
			print "Problem opening database on server " + HOST + "...."
			return False
	
	def pgclose(self):
		self.username = ''
		self.pykotauid = ''
		self.balance = 0
		self.lifebalance = 0
		self.alreadyopen = False
		self.sql.close()
	
	def get_userslist(self, uname,ls):
		try:
			query = self.sql.query("SELECT username FROM users WHERE username LIKE '%s'" % (uname+'%'))
			users = query.getresult()
			print "Users are ->", users
			ls.clear()
			for i in users:
				ls.append([i[0]])
			#self.username = uname
			return True
		except:
			#print "Username is invalid"
			return False

				
	def get_pykotaid(self, uname):
		try:
			query = self.sql.query("SELECT id FROM users WHERE username='%s'" % (uname))
			self.pykotauid = (query.dictresult()[0])['id']
			print "User ID is  ->", self.pykotauid
			self.username = uname
			return True
		except:
			print "Username is invalid"
			return False
	
	def get_pykotabalance(self):
		try:
			query = self.sql.query("SELECT balance FROM users WHERE id='%s'" % (self.pykotauid))
			self.balance = float((query.dictresult()[0])['balance'])
			return self.balance
		except:
			print "balance sql error..."
			return None

	def get_pykotalifebalance(self):
		try:
			query = self.sql.query("SELECT lifetimepaid FROM users WHERE id='%s'" % (self.pykotauid))
			self.lifebalance = float((query.dictresult()[0])['lifetimepaid'])
			print "%s%.2f" % ("pykotalifebalance -> $", self.lifebalance)
			return True
		except:
			print "lifetimepaid sql error..."
			return False
		
	def set_pykotabalances(self, addbalance):	
		newbalance = addbalance + self.balance
		newlifebalance = self.lifebalance + addbalance
		try:
			query = self.sql.query("UPDATE users SET balance=%s, lifetimepaid=%s WHERE id='%s'" % 
				(newbalance, newlifebalance, self.pykotauid))
			return True
		except:
			print "sql update error..."
			return False


if __name__ == "__main__":
	hwg = gui()
	gtk.main()
	print "Goodbye..."

