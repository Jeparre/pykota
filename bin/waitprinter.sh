#! /bin/sh
#
# PyKota - Print Quotas for CUPS and LPRng
#
# (c) 2003, 2004, 2005, 2006, 2007 Jerome Alet <alet@librelogiciel.com>
# You're welcome to redistribute this software under the
# terms of the GNU General Public Licence version 2.0
# or, at your option, any higher version.
#
# You can read the complete GNU GPL in the file COPYING
# which should come along with this software, or visit
# the Free Software Foundation's WEB site http://www.fsf.org
#
# $Id: waitprinter.sh 3133 2007-01-17 22:19:42Z jerome $
#
# First version by Matt Hyclak & Jerome Alet
# Rewritten from scratch, and contributed to PyKota, by Christian Andreetta
# and Paolo Nobili

# If ending phase, after the job has been fully transmitted to the printer
# we have to wait for the printer being in printing mode before checking
# if it is idle, otherwise we could have problems with slow printers.
#--------------------------------------------------------------------------
PATH=$PATH:/bin:/usr/bin:/usr/local/bin:/opt/bin:/sbin:/usr/sbin
#--------------------------------------------------------------------------
LOG_FILE=/var/log/pykota-waitprinter-snmpread.log
LOG_DO_FLAG=""  #set different from null for file logging
IDLE_WAIT_NUM=3 #number of snmp reads to consider the printer _really_ idle
SNMP_DELAY=2    #seconds between snmp reads
#--------------------------------------------------------------------------
# END OF CONF
#--------------------------------------------------------------------------
function log_msg() {
        if [ -n "${LOG_DO_FLAG}" ]; then
                echo `date` "$*" >> ${LOG_FILE}
        fi
}
#--------------------------------------------------------------------------
function printer_status_get() {
        local printer="$1"
        local comm="$2"
        local version="$3"
        PRINTER_STATUS=`snmpget -v${version} -c ${comm} -Ov ${printer} HOST-RESOURCES-MIB::hrPrinterStatus.1`
}
#--------------------------------------------------------------------------
function printing_wait() {
        local printer="$1"
        local comm="$2"
        local version="$3"
        log_msg "CYCLE: printing_wait"
        while [ 1 ]; do
                printer_status_get "${printer}" "${comm}" "${version}"
                log_msg "${PRINTER_STATUS}"
                echo "${PRINTER_STATUS}" | grep -iE '(printing)|(idle)' >/dev/null && break
                sleep ${SNMP_DELAY}
        done
}
#--------------------------------------------------------------------------
function idle_wait() {
        local printer="$1" idle_num=0 idle_flag=0
        local comm="$2"
        local version="$3"
        log_msg "CYCLE: idle_wait"
        while [ ${idle_num} -lt ${IDLE_WAIT_NUM} ]; do
                printer_status_get "${printer}" "${comm}" "${version}"
                log_msg "${PRINTER_STATUS}"
                idle_flag=0
                echo "${PRINTER_STATUS}" | grep -iE '(idle)' >/dev/null && idle_flag=1
                if [ ${idle_flag} -gt 0 ]; then
                        idle_num=$((idle_num+1))
                else
                        idle_num=0
                fi
                sleep ${SNMP_DELAY}
        done
}
#--------------------------------------------------------------------------
function main() {
        local printer="$1"
        local comm="$2"
        local version="$3"
        if [ x${comm} == "x" ]; then
                comm="public"
        fi
        if [ x${version} == "x" ]; then
                version="1"
        fi
        log_msg "BEGIN"
        ##log_msg "`ls -la /var/spool/{cups,samba}`"
        log_msg "Pykota Phase: ${PYKOTAPHASE}"
        if [ x$PYKOTASTATUS != "xCANCELLED" ] && [ x$PYKOTAACTION = "xALLOW" ] && [ x$PYKOTAPHASE = "xAFTER" ] ; then
                printing_wait "${printer}" "${comm}" "${version}"
        fi
        idle_wait "${printer}" "${comm}" "${version}" #in any case
        ##log_msg "`ls -la /var/spool/{cups,samba}`"
        log_msg "END"
}
#==========================================================================
# MAIN
#==========================================================================
PRINTER_STATUS=""
main "$1" "$2" "$3"
exit $?
