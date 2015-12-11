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
-- $Id: pykota-mysql.sql 3133 2007-01-17 22:19:42Z jerome $
--
--

--
-- PyKota Database creation script for MySQL
--
-- Launch this as MySQL administrator with \.
--


--
-- Create the print quota database
--
CREATE DATABASE pykota DEFAULT CHARACTER SET 'utf8';

--
-- Create the print quota database users
-- NOTE: Change the "IDENTIFIED BY" strings to the passwords you would like.
-- 
GRANT USAGE ON *.* TO 'pykotauser'@'localhost' IDENTIFIED BY 'readonlypw';
GRANT USAGE ON *.* TO 'pykotaadmin'@'localhost' IDENTIFIED BY 'readwritepw';

-- 
-- If necessary activate the lines below (and keep the preceding ones
-- activated at the same time)
--
-- GRANT USAGE ON *.* TO 'pykotauser'@'%' IDENTIFIED BY 'readonlypw';
-- GRANT USAGE ON *.* TO 'pykotaadmin'@'%' IDENTIFIED BY 'readwritepw';

-- 
-- Now connect to the new database
-- 
USE pykota;

--
-- Create the users table
--
CREATE TABLE users (id INT4 PRIMARY KEY NOT NULL AUTO_INCREMENT,
                   username VARCHAR(255) UNIQUE NOT NULL,
                   email TEXT, 
                   balance FLOAT DEFAULT 0.0,
                   lifetimepaid FLOAT DEFAULT 0.0,
                   limitby VARCHAR(30) DEFAULT 'quota',
                   description TEXT,
                   overcharge FLOAT NOT NULL DEFAULT 1.0) TYPE=INNODB;
                   
--
-- Create the groups table
--
CREATE TABLE groups (id INT4 PRIMARY KEY NOT NULL AUTO_INCREMENT,
                    groupname VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    limitby VARCHAR(30) DEFAULT 'quota') TYPE=INNODB;
                    
--
-- Create the printers table
--
CREATE TABLE printers (id INT4 PRIMARY KEY NOT NULL AUTO_INCREMENT,
                      printername VARCHAR(255) UNIQUE NOT NULL,
                      description TEXT,
                      priceperpage FLOAT DEFAULT 0.0,
                      priceperjob FLOAT DEFAULT 0.0,
                      passthrough ENUM('t','f') DEFAULT 'f',
                      maxjobsize INT4) TYPE=INNODB;
                    
--
-- Create the print quota table for users
--
CREATE TABLE userpquota (id INT8 PRIMARY KEY NOT NULL AUTO_INCREMENT,
                        userid INT4, 
                        printerid INT4, 
                        lifepagecounter INT4 DEFAULT 0,
                        pagecounter INT4 DEFAULT 0,
                        softlimit INT4,
                        hardlimit INT4,
                        datelimit DATETIME,
                        maxjobsize INT4,
                        warncount INT4 DEFAULT 0, 
                        INDEX (userid),
                        FOREIGN KEY (userid) REFERENCES users(id),
                        INDEX (printerid),
                        FOREIGN KEY (printerid) REFERENCES printers(id)) 
                        TYPE=INNODB;
CREATE UNIQUE INDEX userpquota_up_id_ix ON userpquota (userid, printerid);
                        
--
-- Create the job history table
--
CREATE TABLE jobhistory(id INT4 PRIMARY KEY NOT NULL AUTO_INCREMENT,
                        jobid TEXT,
                        userid INT4,
                        printerid INT4,
                        pagecounter INT4 DEFAULT 0,
                        jobsizebytes INT8,
                        jobsize INT4,
                        jobprice FLOAT,
                        action TEXT,
                        filename TEXT,
                        title TEXT,
                        copies INT4,
                        options TEXT,
                        hostname VARCHAR(255),
                        md5sum TEXT,
                        pages TEXT,
                        billingcode TEXT,
                        precomputedjobsize INT4,
                        precomputedjobprice FLOAT,
                        jobdate TIMESTAMP,
                        INDEX (userid, printerid),
                        CONSTRAINT checkUserPQuota FOREIGN KEY (userid, printerid) REFERENCES userpquota (userid, printerid)
                        ) TYPE=INNODB;
CREATE INDEX jobhistory_u_id_ix ON jobhistory (userid);
CREATE INDEX jobhistory_p_id_ix ON jobhistory (printerid);
CREATE INDEX jobhistory_pd_id_ix ON jobhistory (printerid, jobdate);
CREATE INDEX jobhistory_hostname_ix ON jobhistory (hostname);
                        
--
-- Create the print quota table for groups
--
CREATE TABLE grouppquota(id INT8 PRIMARY KEY NOT NULL AUTO_INCREMENT,
                         groupid INT4, 
                         printerid INT4,
                         softlimit INT4,
                         hardlimit INT4,
                         maxjobsize INT4,
                         datelimit DATETIME,
                         INDEX (groupid),
                         FOREIGN KEY (groupid) REFERENCES groups(id),
                         INDEX (printerid),
                         FOREIGN KEY (printerid) REFERENCES printers(id))
                         TYPE=INNODB;
CREATE UNIQUE INDEX grouppquota_up_id_ix ON grouppquota (groupid, printerid);
                        
--                         
-- Create the groups/members relationship
--
CREATE TABLE groupsmembers(groupid INT4 NOT NULL,
                           userid INT4 NOT NULL,
                           INDEX (groupid),
                           FOREIGN KEY (groupid) REFERENCES groups(id),
                           INDEX (userid),
                           FOREIGN KEY (userid) REFERENCES users(id),
                           PRIMARY KEY (groupid, userid)) TYPE=INNODB;
                           
--                         
-- Create the printer groups relationship
--
CREATE TABLE printergroupsmembers(groupid INT4 NOT NULL,
                           printerid INT4 NOT NULL,
                           INDEX (groupid),
                           FOREIGN KEY (groupid) REFERENCES printers(id),
                           INDEX (printerid),
                           FOREIGN KEY (printerid) REFERENCES printers(id),
                           PRIMARY KEY (groupid, printerid)) TYPE=INNODB;
--
-- Create the table for payments
-- 
CREATE TABLE payments (id INT4 PRIMARY KEY NOT NULL AUTO_INCREMENT,
                       userid INT4,
                       amount FLOAT,
                       description TEXT,
                       date TIMESTAMP,
                       INDEX (userid),
                       FOREIGN KEY (userid) REFERENCES users(id)) TYPE=INNODB;
CREATE INDEX payments_date_ix ON payments (date);

--
-- Create the table for coefficients wrt paper sizes and the like
--
CREATE TABLE coefficients (id INT4 PRIMARY KEY NOT NULL AUTO_INCREMENT,
                           printerid INT4 NOT NULL,
                           label VARCHAR(255) NOT NULL,
                           coefficient FLOAT DEFAULT 1.0,
                           INDEX (printerid),
                           FOREIGN KEY (printerid) REFERENCES printers(id),
                           CONSTRAINT coeffconstraint UNIQUE (printerid, label)
                           ) TYPE=INNODB;

-- 
-- Create the table for the billing codes
--
CREATE TABLE billingcodes (id INT4 PRIMARY KEY NOT NULL AUTO_INCREMENT,
                           billingcode VARCHAR(255) UNIQUE NOT NULL,
                           description TEXT,
                           balance FLOAT DEFAULT 0.0,
                           pagecounter INT4 DEFAULT 0) TYPE=INNODB;
--                        
-- Set some ACLs                        
--
GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES ON `pykota`.* TO 'pykotaadmin'@'localhost';
GRANT SELECT ON `pykota`.* TO 'pykotauser'@'localhost';

-- 
-- If necessary activate the lines below (and keep the preceding ones
-- activated at the same time)
--
-- GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES ON `pykota`.* TO 'pykotaadmin'@'%';
-- GRANT SELECT ON `pykota`.* TO 'pykotauser'@'%';

