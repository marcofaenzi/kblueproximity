"""Syslog / file logging."""
from __future__ import annotations

import syslog
import time

from kblueproximity.i18n import _


class Logger:
    def __init__(self):
        self.disable_syslogging()
        self.disable_filelogging()

    def getFacilityFromString(self, facility):
        log_dict = {
            'local0': syslog.LOG_LOCAL0,
            'local1': syslog.LOG_LOCAL1,
            'local2': syslog.LOG_LOCAL2,
            'local3': syslog.LOG_LOCAL3,
            'local4': syslog.LOG_LOCAL4,
            'local5': syslog.LOG_LOCAL5,
            'local6': syslog.LOG_LOCAL6,
            'local7': syslog.LOG_LOCAL7,
            'user': syslog.LOG_USER,
        }
        return log_dict[facility]

    def enable_syslogging(self, facility):
        self.syslog_facility = self.getFacilityFromString(facility)
        syslog.openlog('kblueproximity', syslog.LOG_PID)
        self.syslogging = True

    def disable_syslogging(self):
        self.syslogging = False
        self.syslog_facility = None

    def enable_filelogging(self, filename):
        self.filename = filename
        try:
            self.flog = open(filename, 'a')
            self.filelogging = True
        except OSError:
            try:
                self.flog = open(filename, 'w')
                self.filelogging = True
            except OSError:
                print(_("Could not open logfile '{}' for writing.").format(filename))
                self.disable_filelogging()

    def disable_filelogging(self):
        try:
            self.flog.close()
        except Exception:
            pass
        self.filelogging = False
        self.filename = ''

    def log_line(self, line):
        if self.syslogging:
            syslog.syslog(self.syslog_facility | syslog.LOG_NOTICE, line)
        if self.filelogging:
            try:
                self.flog.write(time.ctime() + ' kblueproximity: ' + line + '\n')
                self.flog.flush()
            except Exception:
                self.disable_filelogging()

    def debug_line(self, config, line):
        if config.get('debug_log', True):
            self.log_line('[debug] ' + line)

    def configureFromConfig(self, config):
        if config['log_to_syslog']:
            self.enable_syslogging(config['log_syslog_facility'])
        else:
            self.disable_syslogging()
        if config['log_to_file']:
            if self.filelogging and config['log_filelog_filename'] != self.filename:
                self.disable_filelogging()
                self.enable_filelogging(config['log_filelog_filename'])
            elif not self.filelogging:
                self.enable_filelogging(config['log_filelog_filename'])
