--
-- PyKota - Print Quotas for CUPS and LPRng
--
-- (c) 2003, 2004, 2005, 2006, 2007 Jerome Alet <alet@librelogiciel.com>
-- This program is free software; you can redistribute it and/or modify
-- it under the terms of the GNU General Public License as published by
-- the Free Software Foundation; either version 2 of the License, or
-- (at your option) any later version.
--
-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU General Public License for more details.
-- 
-- You should have received a copy of the GNU General Public License
-- along with this program; if not, write to the Free Software
-- Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
--
-- $Id: upgrade-to-1.16.sql 3133 2007-01-17 22:19:42Z jerome $
--
--
--
-- This script has to be used if you already
-- have a pre-1.16 version of PyKota to upgrade
-- your database schema. 
--
-- YOU DON'T NEED TO USE IT IF YOU'VE JUST INSTALLED PYKOTA
--
                        
--                         
-- WARNING : YOU NEED A RECENT VERSION OF POSTGRESQL FOR THE ALTER COLUMN STATEMENT TO WORK !
--

--                         
-- Modify the old database schema
--
ALTER TABLE jobhistory ADD COLUMN jobprice FLOAT;
ALTER TABLE jobhistory ADD COLUMN filename TEXT;
ALTER TABLE jobhistory ADD COLUMN title TEXT;
ALTER TABLE jobhistory ADD COLUMN copies INT4;
ALTER TABLE jobhistory ADD COLUMN options TEXT;

--
-- Remove bad integrity rules
-- and replace them with a new one
--
ALTER TABLE jobhistory DROP CONSTRAINT "$1";
ALTER TABLE jobhistory DROP CONSTRAINT "$2";
ALTER TABLE jobhistory ADD CONSTRAINT checkUserPQuota FOREIGN KEY (userid, printerid) REFERENCES userpquota (userid, printerid);

-- 
-- Add new tables
--
--                         
-- Create the printer groups relationship
--
CREATE TABLE printergroupsmembers(groupid INT4 REFERENCES printers(id),
                           printerid INT4 REFERENCES printers(id),
                           PRIMARY KEY (groupid, printerid));

--                         
-- Now add some indexes
--
CREATE UNIQUE INDEX userpquota_up_id_ix ON userpquota (userid, printerid);
CREATE INDEX jobhistory_p_id_ix ON jobhistory (printerid);
CREATE INDEX jobhistory_pd_id_ix ON jobhistory (printerid, jobdate);
CREATE UNIQUE INDEX grouppquota_up_id_ix ON grouppquota (groupid, printerid);

-- 
-- And now sets some ACLs
-- 
REVOKE ALL ON printergroupsmembers FROM public;                        
GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES ON printergroupsmembers TO pykotaadmin;
GRANT SELECT ON printergroupsmembers TO pykotauser;

