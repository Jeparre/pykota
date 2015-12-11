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
-- $Id: upgrade-to-1.19.sql 3133 2007-01-17 22:19:42Z jerome $
--
--
--
-- This script has to be used if you already
-- have a pre-1.19 version of PyKota to upgrade
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
ALTER TABLE printers ADD COLUMN description TEXT;
ALTER TABLE jobhistory ADD COLUMN jobsizebytes INT8;
ALTER TABLE jobhistory ADD COLUMN hostname TEXT;
CREATE INDEX jobhistory_hostname_ix ON jobhistory (hostname);

CREATE TABLE payments (id SERIAL PRIMARY KEY NOT NULL,
                       userid INT4 REFERENCES users(id),
                       amount FLOAT,
                       date TIMESTAMP DEFAULT now());
CREATE INDEX payments_date_ix ON payments (date);

REVOKE ALL ON payments FROM public;                        
REVOKE ALL ON payments_id_seq FROM public;
GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES ON payments TO pykotaadmin;
GRANT SELECT, UPDATE ON payments_id_seq TO pykotaadmin;
GRANT SELECT ON payments TO pykotauser;
