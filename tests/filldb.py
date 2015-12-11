#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-

# $Id: filldb.py 2800 2006-03-21 23:43:51Z jerome $


import sys
import os

def createBillingCodes(number) :
    """Creates a number of billing codes."""
    sys.stdout.write("Adding %i billing codes...\n" % number)
    billingcodes = [ "test-billingcode-%05i" % i for i in range(number) ]
    argsfile = open("arguments.list", "w")
    argsfile.write('--add\n--reset\n--description\n"a billing code"\n')
    for bname in billingcodes :
        argsfile.write("%s\n" % bname)
    argsfile.close()    
    os.system('pkbcodes --arguments arguments.list') 
    return billingcodes

def deleteBillingCodes(billingcodes) :
    """Deletes all test billing codes."""
    sys.stdout.write("Deleting billing codes...\n")
    argsfile = open("arguments.list", "w")
    argsfile.write('--delete\n')
    for bname in billingcodes :
        argsfile.write("%s\n" % bname)
    argsfile.close()    
    os.system('pkbcodes --arguments arguments.list') 
    
def createPrinters(number) :
    """Creates a number of printers."""
    sys.stdout.write("Adding %i printers...\n" % number)
    printernames = [ "test-printer-%05i" % i for i in range(number) ]
    argsfile = open("arguments.list", "w")
    argsfile.write('--add\n--charge\n0.05\n--maxjobsize\n5\n--passthrough\n--description\n"a printer"\n')
    for pname in printernames :
        argsfile.write("%s\n" % pname)
    argsfile.close()    
    os.system('pkprinters --arguments arguments.list') 
    return printernames

def deletePrinters(printernames) :
    """Deletes all test printers."""
    sys.stdout.write("Deleting printers...\n")
    argsfile = open("arguments.list", "w")
    argsfile.write('--delete\n')
    for pname in printernames :
        argsfile.write("%s\n" % pname)
    argsfile.close()    
    os.system('pkprinters --arguments arguments.list') 
    
def createUsers(number) :
    """Creates a number of users."""
    sys.stdout.write("Adding %i users...\n" % number)
    usernames = [ "test-user-%05i" % i for i in range(number) ]
    argsfile = open("arguments.list", "w")
    argsfile.write('--add\n--limitby\nbalance\n--balance\n50.0\n--description\n"an user"\n--comment\n"fake payment"\n')
    for uname in usernames :
        argsfile.write("%s\n" % uname)
    argsfile.close()    
    os.system('pkusers --arguments arguments.list') 
    return usernames

def deleteUsers(usernames) :
    """Deletes all test users."""
    sys.stdout.write("Deleting users...\n")
    argsfile = open("arguments.list", "w")
    argsfile.write('--delete\n')
    for uname in usernames :
        argsfile.write("%s\n" % uname)
    argsfile.close()    
    os.system('pkusers --arguments arguments.list') 
    
def createGroups(number) :
    """Creates a number of groups."""
    sys.stdout.write("Adding %i groups...\n" % number)
    groupnames = [ "test-group-%05i" % i for i in range(number) ]
    argsfile = open("arguments.list", "w")
    argsfile.write('--groups\n--add\n--limitby\nquota\n--description\n"a group"\n')
    for gname in groupnames :
        argsfile.write("%s\n" % gname)
    argsfile.close()    
    os.system('pkusers --arguments arguments.list') 
    return groupnames

def deleteGroups(groupnames) :
    """Deletes all test groups."""
    sys.stdout.write("Deleting groups...\n")
    argsfile = open("arguments.list", "w")
    argsfile.write('--groups\n--delete\n')
    for gname in groupnames :
        argsfile.write("%s\n" % gname)
    argsfile.close()    
    os.system('pkusers --arguments arguments.list') 
    
def createUserPQuotas(usernames, printernames) :
    """Creates a number of user print quota entries."""
    number = len(usernames) * len(printernames)
    sys.stdout.write("Adding %i user print quota entries...\n" % number)
    argsfile = open("arguments.list", "w")
    argsfile.write('--add\n--softlimit\n100\n--hardlimit\n110\n--reset\n--hardreset\n--printer\n')
    argsfile.write("%s\n" % ",".join(printernames))
    for uname in usernames :
        argsfile.write("%s\n" % uname)
    argsfile.close()    
    os.system('edpykota --arguments arguments.list') 

def deleteUserPQuotas(usernames, printernames) :
    """Deletes all test user print quota entries."""
    number = len(usernames) * len(printernames)
    sys.stdout.write("Deleting user print quota entries...\n")
    argsfile = open("arguments.list", "w")
    argsfile.write('--delete\n--printer\n')
    argsfile.write("%s\n" % ",".join(printernames))
    for uname in usernames :
        argsfile.write("%s\n" % uname)
    argsfile.close()    
    os.system('edpykota --arguments arguments.list') 
    
def createGroupPQuotas(groupnames, printernames) :
    """Creates a number of group print quota entries."""
    number = len(groupnames) * len(printernames)
    sys.stdout.write("Adding %i group print quota entries...\n" % number)
    argsfile = open("arguments.list", "w")
    argsfile.write('--groups\n--add\n--softlimit\n100\n--hardlimit\n110\n--reset\n--hardreset\n--printer\n')
    argsfile.write("%s\n" % ",".join(printernames))
    for gname in groupnames :
        argsfile.write("%s\n" % gname)
    argsfile.close()    
    os.system('edpykota --arguments arguments.list') 

def deleteGroupPQuotas(groupnames, printernames) :
    """Deletes all test group print quota entries."""
    number = len(groupnames) * len(printernames)
    sys.stdout.write("Deleting group print quota entries...\n")
    argsfile = open("arguments.list", "w")
    argsfile.write('--groups\n--delete\n--printer\n')
    argsfile.write("%s\n" % ",".join(printernames))
    for gname in groupnames :
        argsfile.write("%s\n" % gname)
    argsfile.close()    
    os.system('edpykota --arguments arguments.list') 
    
if __name__ == "__main__" :    
    if len(sys.argv) == 1 :
        sys.stderr.write("usage :  %s  [--nodelete]  NbBillingCodes  NbPrinters  NbUsers  NbGroups\n" % sys.argv[0])
    else :    
        delete = True
        args = sys.argv[1:]
        if args[0] == "--nodelete" :
            args = args[1:]
            delete = False
        nbbillingcodes = int(args[0])
        nbprinters = int(args[1])
        nbusers = int(args[2])
        nbgroups = int(args[3])
        if nbbillingcodes :
            bcodes = createBillingCodes(nbbillingcodes)
        if nbprinters :
            printers = createPrinters(nbprinters)
        if nbusers :    
            users = createUsers(nbusers)
        if nbgroups :    
            groups = createGroups(nbgroups)
            
        if nbusers and nbprinters :    
            createUserPQuotas(users, printers)
            if delete :
                deleteUserPQuotas(users, printers)
            
        if nbgroups and nbprinters :    
            createGroupPQuotas(groups, printers)
            if delete :
                deleteGroupPQuotas(groups, printers)
            
        if delete :    
            if nbbillingcodes :    
                deleteBillingCodes(bcodes)
            if nbgroups :    
                deleteGroups(groups)
            if nbusers :    
                deleteUsers(users)
            if nbprinters :    
                deletePrinters(printers)
        os.remove("arguments.list")
        
