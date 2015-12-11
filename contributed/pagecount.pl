#!/usr/bin/perl -U
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
#
############################################################
#                                                          #
# This script is 100% copyright (c) 2003 René Lund Jensen  #
#                                                          #
# He contributed it to the PyKota project on Dec. 4th 2003 #
# and licensed it under the terms of the GNU GPL.          #
#                                                          #
# MANY THANKS TO HIM                                       #
#                                                          #
############################################################
#
#
# $Id: pagecount.pl 3133 2007-01-17 22:19:42Z jerome $
#
#

use Socket;
use IO::Socket;

if (@ARGV < 2){
    print "usage: pagecount.pl servername port\n";
}

$printer = @ARGV[0];
$port    = @ARGV[1];

$ssh = osocket($printer, $port);
if ($ssh){
    $page = pagecount($ssh);
    print $page."\n";
    $ssh-close();
    exit(0);
}else {
    exit(1);
}

sub pagecount {
    my $sh = @_[0];    # Get sockethandle
    # send pagequery to sockethandle
    send($sh, "\033%-12345X\@PJL INFO PAGECOUNT\r\n",0);
    # Read response from sockethandle
    recv($sh,$RESPONSE,0xFFFFF,0);
    (my $junk,$pc) = split (/\r\n/s,$RESPONSE); # Find the pagecount
    $pc =~ s/(PAGECOUNT=)?([0-9]+)/$2/g;
    return $pc;                                 # Return pagecount
}


sub osocket {

 # Connecting to @_[0] = @arg[1] = $printer
 # On port @_[1] = 9100 JetDirect port
 # Using TCP protocol
    my $sh= new IO::Socket::INET(PeerAddr => @_[0],
                                 PeerPort => @_[1], 
                                 Proto => 'tcp');
    if (!defined($sh)) {        # Did we open the socket?
        return undef;           # No! return undef
    } else {                    # Yes!
        $sh->sockopt(SO_KEEPALIVE,1);   # Set socket option SO_KEEPALIVE
        return $sh;             # return sockethandle
    }
}
