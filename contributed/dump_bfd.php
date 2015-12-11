#!/usr/bin/php -q

#
# dump_bfd : dumps usage totals per printer groups
#
# Contributed to this project by Jamuel P. Starkey on July 21st 2005
#
# (c) 2005 Jamuel P. Starkey <jamuel@my740il.com> 
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
# $Id: dump_bfd.php 2383 2005-07-22 19:03:42Z jerome $
#
#

<?php

global $debug, $groups_all, $group_search, $printer_search, $descriptorspec,
       $dumpykota_options, $out_format;
        
        $descriptorspec = array(
        0 => array("pipe", "r"),  // stdin is a pipe that the child will read from
        1 => array("pipe", "w"),  // stdout is a pipe that the child will write to
        2 => array("file", "/root/error-output.txt", "a") // stderr is a file to write to
        );
echo "\n";
$groups_all = "NULL";
$dumpykota_options = '';
$start = '';
$end = '';
$out_format = 'csv';

foreach ($argv as $args)
{
        if ($args == '--debug=false')
                $debug = FALSE;
        if ($args == '--debug=true')
                $debug = TRUE;
        if (preg_match ('/\-\-printer(\=*)([a-z0-9\-\_]*)/i', $args, $printers))
        {
                $printer_search = ($printers[2]);
                if ($printer_search == '')
                        $printer_search = "NULL";
        }
        if (preg_match ('/\-\-group(\=+)([a-z0-9\-\_]*)/i', $args, $groups))
        {
                $group_search = ($groups[2]);
                if ($group_search == '')
                        $group_search = "NULL";
        }
        if ($args == '--groups')
        {
                $groups_all = TRUE;
        }
        if (preg_match ('/start=[a-z0-9\-]+/i', $args, $start))
        {
                $dumpykota_options .= $start[0] . ' ';
        }
        if (preg_match ('/end=[a-z0-9\-]+/i', $args, $end))
        {
                $dumpykota_options .= $end[0] . ' ';
        }
        if ($args == '--format=ssv')
        {
                $out_format = 'ssv';
        }
}

if (!isset($debug))
        $debug = FALSE;

if ($debug)
        echo "Debugging ON\n\n";

function get_users ()
{
        global $debug, $printer_search, $descriptorspec;
        
        $users = array();
        $usernames = array();

        $cwd = '/root';
        $env = array('some_option' => 'aeiou');
        $in = "--data users";
        $process = proc_open('dumpykota --data users --format ssv', $descriptorspec, $pipes);
        if (is_resource($process)) 
        {
                fclose($pipes[0]);
   
                while (!feof($pipes[1])) 
                {
                        $out = fgets($pipes[1], 4096);
                        $users[] = split (";", $out); 
                }
                fclose($pipes[1]);

                $return_value = proc_close($process);
                array_shift ($users);
                array_pop ($users);
                if ($debug)
                        echo "Got for Users:\n";
                foreach ($users as $user)
                {
                        list ($id, $username, $email, $balance, $lifetimepaid, $limitby, $overcharge) = $user;
                        $username = trim ($username, '"');
                        $usernames[] = $username;
                        if ($debug)
                                echo "\t$username\n";
                }
        }
        return ($usernames);
}

function get_printer_groups ()
{
        global $debug, $descriptorspec, $printer_groups;
        if ($debug)
                echo "\n";
        $process = proc_open('dumpykota --data pmembers --format ssv', $descriptorspec, $pipes);
        if (is_resource($process)) 
        {
 
                fclose($pipes[0]);

                $pgroups = array();
                $printers = array();
                $printer_groups = array();
                $group_names = array();

                while (!feof($pipes[1])) 
                {
                        $out = fgets($pipes[1], 4096);
                        $pgroups[] = split (";", $out);
                        if ($debug)
                                echo "$out\n"; 
                }
                fclose($pipes[1]);

                $return_value = proc_close($process);
                array_shift ($pgroups);
                array_pop ($pgroups);
                foreach ($pgroups as $pgroup)
                {
                        //list ($id, $printername ,$description, $priceperpage, $priceperjob) = $user;
                        list ($pgroupname, $printername, $groupid, $printerid) = $pgroup;

                        $pgroupname = trim ($pgroupname, '"');
                        $printername = trim ($printername, '"');

                        if (!in_array ($pgroupname, $group_names))
                        {
                                $printer_groups[$pgroupname][] = $printername;
                                $group_names[] = $pgroupname;
                        }
                        else
                        {
                                $printer_groups[$pgroupname][] = $printername;
                        }
                        if (!in_array ($printername, $printers))
                        {
                                $printers[] = $printername;
                        }
                }
        }


        if ($debug)
        {        
                echo "\n";

                foreach ($printer_groups as $group_name => $group)
                {
                        echo "$group_name:";
                        foreach ($group as $printer)
                        {
                                echo "\t" . $printer . "\n";
                        }
                        echo "\n";
                }
        }
        
        $my_groups = array();
        //$printer_search = "None";
        if (isset ($printer_search))
        {
                if ($printer_search == "NULL")
                {
                        echo "\nSyntax error check your --printer\n";
                }
                elseif ( !in_array ($printer_search, $printers))
                {
                        echo "\n$printer_search not found.  Check your printer name. (You didn't specify a printer group here did you?)\n";
                }
                else
                {
                        echo "\n$printer_search belongs to: ";
                        foreach ($printer_groups as $group_name => $group)
                        {
                                foreach ($group as $printer)
                                {
                                        if ($printer == $printer_search)
                                        {
                                                $my_groups[] = $group_name;
                                        }
                                }
                        } 
                        if (count ($my_groups) == 0)
                        {
                                echo "NONE, 0, Zilch, Nada!\n";
                        }
                        else
                        {
                                foreach ($my_groups as $group)
                                {       
                                        echo "$group ";
                                }
                        }
                }
        
        }
        return ($printer_groups);
}
function dump_by_group ($printer_groups, $group_search)
{
        global $debug, $descriptorspec;
        global $dumpykota_options, $out_format;
        if ($out_format == 'ssv' )
        {
                $delim = ';';
        }
        else
        {
                $delim = ',';
        }
        if ($debug)
                echo "\n";
        $history = array();
        $entry = array();

        $process = proc_open('dumpykota --data history --format ssv ' . $dumpykota_options, $descriptorspec, $pipes);
        if (is_resource($process)) 
        {       
                fclose($pipes[0]);
                while (!feof($pipes[1])) 
                {
                        $out = fgets($pipes[1], 4096);
        //              if ($debug)
        //                      echo "$out\n";
                        $history[] = split (";", $out);
                }
                fclose($pipes[1]);

                $return_value = proc_close($process);
        }

        array_shift ($history);
        array_pop ($history);

        foreach ($history as $key => $value)
        {
                list ($username, $printername, $id, $jobid, $userid, $printerid, $pagecounter, $jobsizebytes, $jobsize, $jobprice, $action, $filename, $title, $copies,$options, $hostname, $md5sum, $pages,$billingcode, $jobdate) = $value;

        $entry[]= array( "username" => trim($username, '"'),
        "printername" => trim($printername, '"'),
        "id" => trim($id, '"'),
        "jobid" => trim($jobid, '"'),
        "userid" => trim($userid, '"'),
        "printerid" => trim($printerid, '"'),
        "pagecounter" => trim($pagecounter, '"'),
        "jobsizebytes" => trim($jobsizebytes, '"'),
        "jobsize" => trim($jobsize, '"'),
        "jobprice" => trim($jobprice, '"'),
        "action" => trim($action, '"'),
        "filename" => trim($filename, '"'),
        "title" => trim($title, '"'),
        "copies" => trim($copies, '"'),
        "options" => trim($options, '"'),
        "hostname" => trim($hostname, '"'),
        "md5sum" => trim($md5sum, '"'),
        "pages" => trim($pages, '"'),
        "billingcode" => trim($billingcode, '"'),
        "jobdate" => trim($jobdate, '"' . "\n")
                );
        }
        
        if (isset ($group_search))
        {               
                if ($group_search == "NULL" )
                {
                        echo "\nSyntax error check your --group or --groups (you can't do both!)\n";
                }
                elseif ( !array_key_exists ($group_search, $printer_groups))
                {
                        echo "\n$group_search not found.  Check your group name. (You didn't specify a printer name here did you?)\n";
                }
                else
                {
                        $user_pages = array();
                        $usernames = get_users();
                        
                        foreach ($usernames as $user)
                        {
                                $user_pages[$user] = 0;
                        }
                        foreach ($printer_groups[$group_search] as $printer)
                        {
                                foreach ($usernames as $user)
                                {
                                        foreach ($entry as $value)
                                        {
                                                if ($value['printername'] == $printer && $value['username'] == $user)
                                                {       
                                                        $user_pages[$user ]=  $user_pages[$user] + $value['jobsize'];
                                                }               
                                        }
                                }
                        }
                        
                        foreach ($user_pages as $key => $value)
                                echo '"' . $group_search . '"' . $delim . '"' . $key . '"' . $delim . '"' . $value . '"' . "\n";
                }
        }
}

$printer_groups = get_printer_groups();
if ($group_search == "NULL" and !$groups_all)
{
        echo "\nSyntax error check your --group or --groups (you can't do both!)\n";
}
elseif ($group_search && $groups_all == "NULL")
{
        dump_by_group ($printer_groups, $group_search);
}
elseif ($groups_all === TRUE) 
{
        foreach ($printer_groups as $group_name => $pgroup)
        {
                dump_by_group ($printer_groups, $group_name);
        }
}
elseif ($groups_all === "NULL")
{
        echo "dump_bfd v0.2  Pykota Printer Group Dumper (c) 2005 GCI Systems\n";
        echo "===============================================================\n";
        echo "\nSYNOPSIS: dump_bfd [--groups || --group=<pykota_pgroup>] [start=<pykota_date_value> end=<pykota_date_value>]";
        echo "\t [--format=<csv || ssv>][--debug=<true> || <false>]\n";
        
        echo "\nDESCRIPTION:\n";
        echo "\tDump pykota pgroup usage for all users by pgroup. Currently this utility dumps in CSV format only.\n" ;
        echo "\tThe column headings are PGroup Username, Pages Printed\n\n";
        
        echo "\nOPTIONS:\n";
        echo "\t--groups dumps all users usage by Pykota printer group.\n";
        echo "\t--group=<pykota_pgroup> dumps all users usage for a single Pykota printer group.\n\n";
        echo "\tstart=<pykota_date_value> sets the start date for the date filter using the same syntax as dumpykota.\n";
        echo "\tend=<pykota_date_value> sets the end date for the date filter using the same syntax as dumpykota.\n";
        echo "\t--format=<csv||ssv> sets the output of the command to comma or semicolon delimited format.\n";
        echo "\nEX: \tdump-bfd --groups start=today-30 end=today --format=ssv\n";
        echo "\tRetrieves results for all groups over the past 30 days and displays them in semicolon delimited format.\n\n";
        
        echo "This program is free software; you can redistribute it and/or modify\n";
        echo "it under the terms of the GNU General Public License as published by\n";
        echo "the Free Software Foundation; either version 2 of the License, or\n";
        echo "(at your option) any later version.\n";
        echo "\n";
        echo "This program is distributed in the hope that it will be useful,\n";
        echo "but WITHOUT ANY WARRANTY; without even the implied warranty of\n";
        echo "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n";
        echo "GNU General Public License for more details.\n";
        echo "\n";
        echo "You can view the most recent GNU General Public License\n";
        echo "by visiting http://www.gnu.org/licenses/gpl.txt or you can write to the \n";
        echo "Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA\n";
        
        echo "\nSend support requests to jamuel@my740il.com\n\n"; 
}
?>
