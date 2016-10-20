#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Python binding of the BXI High Performance Logging Library
@namespace bxi.base.log
@authors Pierre Vignéras <pierre.vigneras@bull.net>
@copyright 2013  Bull S.A.S.  -  All rights reserved.\n
           This is not Free or Open Source software.\n
           Please contact Bull SAS for details about its license.\n
           Bull - Rue Jean Jaurès - B.P. 68 - 78340 Les Clayes-sous-Bois


This module exposes a simple Python binding over the BXI High Performance Logging Library.

Overview
=========

This module provides a much simpler API than the standard Python logging module but
with much better overall performances, and a similar API for basic usage.

Therefore, in most cases, the following code should just work:

~~~~~~~~~{.py}
import bxi.base.log as logging

logging.output('The BXI logging library %s', 'rocks')
~~~~~~~~~

Configuring the logging system is done using the set_config function.
However, a basicConfig function is provided to offer as far as
possible the same API than Python own's logging.basicConfig().

Differences with Python logging module
======================================

Initialization
---------------------------------

The main difference with the Python logging module is that the logging initialization
can be done only once in the whole process. The logging system is initialized as soon
as a log is performed. Therefore the following sequence of instructions will lead to
an exception:

~~~~~~~~{.py}
import bxi.base.log as logging

logging.output("This is a log")   # This actually initialize the logging system
                                  # (unless another log has already been emitted
                                  # from another module of course).

# This will raise a BXILogConfigError
logging.set_config(filename='/tmp/foo.bxilog') # Configure the logging system so all 
                                               # logs go to file '/tmp/foo.bxilog'
~~~~~~~~

The reason is that the first log, will initialize the logging system so all messages
must be displayed on the standard output (by default).

The second call, ask the logging system to change the configuration so all logs now
must be written to '/tmp/foo.bxilog'. This leads to a dynamic
change in the logging outputs which is usually undesired. Hence, an exception is raised.
If this is really the behavior expected, you must do the following:

~~~~~~~~~{.py}
try:
    logging.basicConfig(filename='/tmp/foo.bxilog')
except BXILogConfigError:
    logging.cleanup()
    logging.basicConfig(filename='/tmp/bar.bxilog')
    logging.output("Dynamic reconfiguration of the logging system")
~~~~~~~~~

Configuration
---------------

This module does not provide a hierarchy of loggers as per the Python logging API.
Each logger holds its own logging level and this has no relationship with any other
loggers. Therefore, setting the level of a given logger does not affect any other 
loggers.

However, the filtering in the logging system is based on prefix matching.


Log levels
------------

This API provides a much richer set of logging levels, inspired by the standard POSIX
syslog facility (from ::PANIC to ::NOTICE), and enhanced with
lower detailed levels (from ::OUT to ::LOWEST).
See the ::bxilog_level_e documentation of the underlying C API log.h
for details on those levels.

Uncaught Exception
-------------------

Uncaught exception are automatically reported by the logging system 
using bxi.base.log::exception

**Note however that there is an issue with the Python multiprocessing module and 
a simple workaround. See bxi.base.log::multiprocessing_target for details.**


Python Warning Systems
-----------------------

The Python warning systems can be captured by the  bxi logging system, 
see bxi.base.log::captureWarnings for details.

Automatic cleanup and flush
----------------------------

The BXI logging library must be cleaned up before exit to prevent messages lost.
This is automatically done in Python.

**Note however that there is an issue with the Python multiprocessing module and 
a simple workaround: See bxi.base.log::multiprocessing_target for details.**

"""
from __future__ import print_function
# Try to find other BXI packages in other folders
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)


import atexit
import os
import sys
import warnings
import unittest
import tempfile
import traceback
import configobj
import cStringIO as StringIO

import bxi.ffi as bxiffi
import bxi.base as bxibase
import bxi.base.err as bxierr


# Find the C library
__FFI__ = bxiffi.get_ffi()
__BXIBASE_CAPI__ = bxibase.get_capi()


# WARNING, in the following, the formatting of the documentation should remain as it is
# in order to be correctly processed by doxygen. This is a doxygen bug.
# You can change it, if you have verified first that the new format (using docstrings
# normally, as other functions documentations) appears correctly in the doxygen generated
# documentation.

# # @see ::BXILOG_OFF
OFF = __BXIBASE_CAPI__.BXILOG_OFF

# # @see ::BXILOG_PANIC
PANIC = __BXIBASE_CAPI__.BXILOG_PANIC

# # @see ::BXILOG_ALERT
ALERT = __BXIBASE_CAPI__.BXILOG_ALERT  # #!< See foo.

# # @see ::BXILOG_CRITICAL
CRITICAL = __BXIBASE_CAPI__.BXILOG_CRITICAL

# # @see ::BXILOG_ERROR
ERROR = __BXIBASE_CAPI__.BXILOG_ERROR

# # @see ::BXILOG_WARNING
WARNING = __BXIBASE_CAPI__.BXILOG_WARNING

# # @see ::BXILOG_NOTICE
NOTICE = __BXIBASE_CAPI__.BXILOG_NOTICE

# # @see ::BXILOG_OUTPUT
OUTPUT = __BXIBASE_CAPI__.BXILOG_OUTPUT

# # @see ::BXILOG_INFO
INFO = __BXIBASE_CAPI__.BXILOG_INFO

# # @see ::BXILOG_DEBUG
DEBUG = __BXIBASE_CAPI__.BXILOG_DEBUG

# # @see ::BXILOG_FINE
FINE = __BXIBASE_CAPI__.BXILOG_FINE

# # @see ::BXILOG_TRACE
TRACE = __BXIBASE_CAPI__.BXILOG_TRACE

# # @see ::BXILOG_LOWEST
LOWEST = __BXIBASE_CAPI__.BXILOG_LOWEST

# The .h defines an alias but CFFI
# does understand it
ALL = __BXIBASE_CAPI__.BXILOG_LOWEST

LIB_PREFIX = __FFI__.string(__BXIBASE_CAPI__.bxilog_const.LIB_PREFIX)


# If True,  bxilog_init() has already been called
_INITIALIZED = False

# Set by set_config()
_CONFIG = None
_INIT_CALLER = None

DEFAULT_CONFIG = configobj.ConfigObj({'handlers': ['console'],
                                      'setsighandler': True,
                                      'console': {
                                                  'module': 'bxi.base.log.console_handler',
                                                  'filters': ':output',
                                                  'stderr_level': 'WARNING',
                                                  'colors': '216_dark',
                                                  }
                                      })

# The default logger.
_DEFAULT_LOGGER = None


def is_configured():
    """
    Check if the logs have already been configured.

    @return A boolean indicating the configuration state of the logs
    """
    global _INITIALIZED
    return _INITIALIZED


def get_level_from_str(level_str):
    """
    Return the ::bxilog_level_e related to the given string.
    """
    level_p = __FFI__.new('bxilog_level_e[1]')
    err = __BXIBASE_CAPI__.bxilog_get_level_from_str(level_str, level_p)

    bxierr.BXICError.raise_if_ko(err)
    return level_p[0]


def set_config(configobj):
    """
    Set the whole bxilog module from the given configobj
    """
    global _INITIALIZED
    if _INITIALIZED:
        raise bxierr.BXILogConfigError("The bxilog has already been initialized. "
                                       "Its configuration cannot be changed."
                                       "\nAvailable solutions:"
                                       "\n\t1. Do not perform a log at module level, "
                                       "and the configuration afterwards;"
                                       "\n\t2. Do no perform a log unless is_configured()"
                                       " returns True;"
                                       "\n\t3. Call cleanup() to reinitialize the whole "
                                       "bxilog library (Note: you might need a reconfiguration)."
                                       "\nFor your convenience, "
                                       "the following stacktrace might help finding out where "
                                       "the first _init() call  was made:\n %s" % _INIT_CALLER,
                                       configobj)

    global _CONFIG
    _CONFIG = configobj


def get_config():
    """
    Return the current bxilog configuration.
    """
    global _CONFIG
    return _CONFIG


def bxilog_excepthook(type_, value, traceback):
    """
    The exception hook called on uncaught exception.
    """
    global _INITIALIZED
    if not _INITIALIZED or not __BXIBASE_CAPI__.bxilog_is_ready():
        sys.__excepthook__(type_, value, traceback)
    else:
        get_default_logger()._report((type_, value, traceback),
                                     CRITICAL,
                                     'Uncaught Exception - exiting thread')


def multiprocessing_target(func):
    """
    Decorator for multiprocessing target function.

    This decorator works around two multiprocessing modules issues:

    - multiprocessing does not call defined except hook:
      see http://bugs.python.org/issue1230540

    - multiprocessing does not call atexit:
      see http://bugs.python.org/issue23489

    This decorator must be used as in the following code snippet to guarantee:

    - uncaught exception are correctly reported by bxilog
    - the bxi logging library is cleaned up on exit

### @snippet bxilog_multiprocessing.py BXI Log and Python multiprocessing module
    """
    def wrapped(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            exception('Uncaught Exception: %s', e.__class__.__name__)
        finally:
            cleanup()
    return wrapped


def _init():
    """
    Initialize the underlying C library

    @return
    """
    global _INITIALIZED
    global _CONFIG
    global _INIT_CALLER

    if _CONFIG is None:
        _CONFIG = DEFAULT_CONFIG

    from . import config as bxilogconfig
    from . import filter as bxilogfilter

    c_config = __BXIBASE_CAPI__.bxilog_config_new(sys.argv[0])

    handlers = _CONFIG['handlers']
    for section in handlers:
        try:
            bxilogconfig.add_handler(_CONFIG, section, c_config)
        except KeyError as ke:
            raise bxierr.BXIError("Bad bxilog configuration in handler '%s' of %s,"
                                  " can't find %s" % (section, _CONFIG, ke))
        except Exception as e:
            raise bxierr.BXIError("Bad bxilog configuration in handler "
                                  "'%s' of %s." % (section, _CONFIG), cause=e)

    err_p = __BXIBASE_CAPI__.bxilog_init(c_config)
    bxierr.BXICError.raise_if_ko(err_p)
    sys.excepthook = bxilog_excepthook
    atexit.register(cleanup)
    # Make sure _INITIALIZED is True before raising the exception in order to ensure
    # bxilog_init is not call recursively.
    _INITIALIZED = True
    sio = StringIO.StringIO()
    traceback.print_stack(file=sio)
    _INIT_CALLER = sio.getvalue()
    sio.close()

    if _CONFIG.get('setsighandler', True):
        err_p = __BXIBASE_CAPI__.bxilog_install_sighandler()
        bxierr.BXICError.raise_if_ko(err_p)

    debug("BXI logging configuration: %s", _CONFIG)


def get_logger(name):
    """
    Return the BXILogger instance with the given name.

    If such a logger instance does not exist yet, it is created,
    registered to the underlying C library and returned.

    @param[in] name the logger name

    @return the BXILogger instance with the given name
    """
    for logger in get_all_loggers_iter():
        if __FFI__.string(logger.clogger.name) == name:
            return logger

    logger_p = __FFI__.new('bxilog_logger_p[1]')
    err_p = __BXIBASE_CAPI__.bxilog_registry_get(name, logger_p)
    bxierr.BXICError.raise_if_ko(err_p)

    from . import logger as bxilogger
    return bxilogger.BXILogger(logger_p[0])


def cleanup(flush=True):
    """
    Called at exit time to cleanup the underlying BXI C library.

    @param[in] flush if true, do a flush before releasing all resources.
    @return
    """
    global _INITIALIZED
    global _CONFIG
    global _DEFAULT_LOGGER
    if _INITIALIZED:
        err_p = __BXIBASE_CAPI__.bxilog_finalize(flush)
        bxierr.BXICError.raise_if_ko(err_p)
    _INITIALIZED = False
    _DEFAULT_LOGGER = None
    _CONFIG = None


def flush():
    """
    Flush all pending logs.

    @return
    """
    err_p = __BXIBASE_CAPI__.bxilog_flush()
    bxierr.BXICError.raise_if_ko(err_p)


def get_all_level_names_iter():
    """
    Return an iterator over all level names.

    @return
    """
    names = __FFI__.new("char ***")
    nb = __BXIBASE_CAPI__.bxilog_get_all_level_names(names)
    for i in xrange(nb):
        yield __FFI__.string(names[0][i])


def get_all_loggers_iter():
    """
    Return an iterator over all loggers.

    @return
    """
    loggers = __FFI__.new("bxilog_logger_p **")
    nb = __BXIBASE_CAPI__.bxilog_registry_getall(loggers)
    from . import logger as bxilogger
    for i in xrange(nb):
        yield bxilogger.BXILogger(loggers[0][i])


def get_default_logger():
    """
    Return the root logger.

    @return
    """
    global _DEFAULT_LOGGER
    
    if _DEFAULT_LOGGER is None:
        _DEFAULT_LOGGER = getLogger(os.path.basename(sys.argv[0]))
    return _DEFAULT_LOGGER


def off(msg, *args, **kwargs):
    """
    Do not log given message!

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().off(msg, *args, **kwargs)


def panic(msg, *args, **kwargs):
    """
    Log the given message at the ::PANIC logging level using the default logger.

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().panic(msg, *args, **kwargs)


def alert(msg, *args, **kwargs):
    """
    Log the given message at the ::ALERT logging level using the default logger.

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().alert(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    """
    Log the given message at the ::CRITICAL logging level using the default logger.

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().critical(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    """
    Log the given message at the ::ERROR logging level using the default logger.

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().error(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    """
    Log the given message at the ::WARNING logging level using the default logger.

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().warning(msg, *args, **kwargs)


def notice(msg, *args, **kwargs):
    """
    Log the given message at the ::NOTICE logging level using the default logger.

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().notice(msg, *args, **kwargs)


def output(msg, *args, **kwargs):
    """
    Log the given message at the ::OUT logging level using the default logger.

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().output(msg, *args, **kwargs)

out = output


def info(msg, *args, **kwargs):
    """
    Log the given message at the ::INFO logging level using the default logger.

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().info(msg, *args, **kwargs)


def debug(msg, *args, **kwargs):
    """
    Log the given message at the ::DEBUG logging level using the default logger.

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().debug(msg, *args, **kwargs)


def fine(msg, *args, **kwargs):
    """
    Log the given message at the ::FINE logging level using the default logger.

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().fine(msg, *args, **kwargs)


def trace(msg, *args, **kwargs):
    """
    Log the given message at the ::TRACE logging level using the default logger.

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().trace(msg, *args, **kwargs)


def lowest(msg, *args, **kwargs):
    """
    Log the given message at the ::LOWEST logging level using the default logger.

    @param[in] msg the message to log
    @param[in] args the message arguments if any
    @param[in] kwargs the message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().lowest(msg, *args, **kwargs)


def exception(msg="", *args, **kwargs):
    """
    Log the current exception.

    @param[in] msg a message to display before the exception itself
    @param[in] args message arguments if any
    @param[in] kwargs message arguments if any

    @return
    @see get_default_logger
    """
    get_default_logger().exception(msg, *args, **kwargs)


def report_bxierr(bxierr, msg="", *args, **kwargs):
    """
    Report the given bxierr_p.

    @param[in] bxierr the bxierr_p to report
    @param[in] msg the message to display along with the error report
    @param[in] args message arguments if any
    @param[in] kwargs message arguments if any
 
    @return
 
    @see get_default_logger
    """
    get_default_logger().report_bxierr(bxierr, msg=msg, *args, **kwargs)


# Provide a compatible API with the standard Python logging module
getLogger = get_logger
shutdown = cleanup
warn = warning


def basicConfig(**kwargs):
    """
    Convenient function for backward compatibility with python logging module.

    Parameter kwargs can contain following parameters:
        - `'filename'`: Specifies that a File Handler be created, using the specified 
                        filename, rather than a Console Handler.
        - `'filemode'`: Specifies the mode to open the file, if filename is specified 
            (if filemode is unspecified, it defaults to ‘a’).
        - `'level'`: set the root logger level to the specified level

    @param[in] kwargs named parameters as described above

    @return
    @exception bxi.base.err.BXILogConfigError if the logging system as
               already been initialized
    """
    config = configobj.ConfigObj()
    config['setsighandler'] = True

    if 'filename' in kwargs:
        config['handlers'] = ['filehandler']
        section = dict()
        import bxi.base.log.file_handler as bxilog_filehandler
        section['module'] = bxilog_filehandler.__name__
        section['filters'] = ':%s' % kwargs.get('level', OUTPUT)
        section['path'] = kwargs['filename']
        mode = kwargs.get('filemode', 'a')
        section['append'] = mode == 'a'
        config['filehandler'] = section
    else:
        config['handlers'] = ['consolehandler']
        section = dict()
        import bxi.base.log.console_handler as bxilog_consolehandler
        section['module'] = bxilog_consolehandler.__name__
        section['filters'] = ':%s' % kwargs.get('level', OUTPUT)
        section['stderr_level'] = 'WARNING'
        section['colors'] = '216_dark'
        config['consolehandler'] = section

    set_config(config)

# Warnings integration - taken from the standard Python logging module
_warnings_showwarning = None


def _showwarning(message, category, filename, lineno, _file=None, line=None):
    """
    Implementation of showwarnings which redirects to logging, which will first
    check to see if the file parameter is None. If a file is specified, it will
    delegate to the original warnings implementation of showwarning. Otherwise,
    it will call warnings.formatwarning and will log the resulting string to a
    warnings logger named "py.warnings" with level logging.WARNING.
    """
    if _file is not None:
        if _warnings_showwarning is not None:
            _warnings_showwarning(message, category, filename, lineno, _file, line)
    else:
        warning_msg = warnings.formatwarning(message, category, filename, lineno, line)
        getLogger("py.warnings").warning("%s", warning_msg)


def captureWarnings(capture):
    """
    If capture is False, ensure that warnings are not redirected to bxi logging
    but to their original destinations.

    @param[in] capture if true, redirect all warnings to the bxi logging package
    """
    global _warnings_showwarning
    if capture:
        if _warnings_showwarning is None:
            _warnings_showwarning = warnings.showwarning
            warnings.showwarning = _showwarning
    else:
        if _warnings_showwarning is not None:
            warnings.showwarning = _warnings_showwarning
            _warnings_showwarning = None


class FileLike(object):
    """
    A file like object that can be used for writing backed by the logging api.
    """
    def __init__(self, logger, level=OUTPUT):
        self.logger = logger
        self.level = level
        self.buf = None

    def close(self):
        self._newline()
        self.flush()

    def _newline(self):
        if self.buf is not None:
            self.logger.log(self.level, self.buf)
            self.buf = None

    def flush(self):
        self.logger.flush()

    def write(self, s):
        if self.buf is None:
            self.buf = s
        else:
            # Yes, we use '+' instead of StringIO, format or other tuning
            # since:
            #        1. we do not expect *lots* of write() call without '\n' and
            #           for such few number of operations, the difference is
            #           between various technics is meaningless
            #        2. benchmark shows quite good performance of the '+' operator
            #           nowadays, except with Pypy. See the string_concat.py bench
            #           for details
            self.buf += s
        if self.buf[-1] == '\n':
            self.buf = self.buf[:-1]
            self._newline()

    def writelines(self, sequence):
        for line in sequence:
            self.write(line)


class TestCase(unittest.TestCase):
    """
    Base class for unit testing with the logging system.

    This class defines the filename where logs are produced according 
    to the basename of the unit program launched and the directory returned
    by tempfile.gettempdir().

    Files are overwritten by default.
    """
    # Do not initialize here as it can lead to exception such as:
    # IOError: [Errno 2] No usable temporary directory found 
    #                                      in ['/tmp', '/var/tmp', '/usr/tmp', '/root']
    # This look strange when the end-user is just importing the bxi.base.log module
    # and when there is no free storage space. 
    # Therefore, the initialization is done only in the setUpClass().
    BXILOG_FILENAME = None 

    FILEMODE = 'w'

    @classmethod
    def setUpClass(cls):
        if TestCase.BXILOG_FILENAME is None:
            name = "%s.bxilog" % os.path.basename(sys.argv[0])
            TestCase.BXILOG_FILENAME = os.path.join(tempfile.gettempdir(), name)

        basicConfig(filename=cls.BXILOG_FILENAME,
                    level=LOWEST,
                    filemode=TestCase.FILEMODE)

    @classmethod
    def tearDownClass(cls):
        cleanup()


##
# @example bxilog_multiprocessing.py
# Using bxilog with the Python multiprocessing module
#

