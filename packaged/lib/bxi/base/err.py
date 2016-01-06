#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@file err.py Defines all Python exceptions classes for all BXI modules
@authors Pierre Vignéras <pierre.vigneras@bull.net>
@copyright 2013  Bull S.A.S.  -  All rights reserved.\n
           This is not Free or Open Source software.\n
           Please contact Bull SAS for details about its license.\n
           Bull - Rue Jean Jaurès - B.P. 68 - 78340 Les Clayes-sous-Bois
@namespace bxi.base.err Python BXI Exceptions

This module exposes all BXI Exception classes.

"""

import bxi.ffi as bxiffi
import bxi.base as bxibase

# Find the C library
__FFI__ = bxiffi.get_ffi()
__BXIBASE_CAPI__ = bxibase.get_capi()


class BXIError(Exception):
    """
    The root class of all BXI exceptions
    """
    def __init__(self, msg):
        """
        Create a new BXIError instance.

        @param[in] msg a message
        """
        super(BXIError, self).__init__(msg)
        self.msg = msg


class BXICError(BXIError):
    """
    Wrap a ::bxierr_p into a Python exception
    """
    def __init__(self, bxierr_p):
        """
        Create a new instance for the given ::bxierr_p

        @param[in] bxierr_p a ::bxierr_p C pointer
        """
        #errstr = __FFI__.string(__BXIBASE_CAPI__.bxierr_str(bxierr_p))
        err_msg = __FFI__.string(bxierr_p.msg)
        super(BXICError, self).__init__(err_msg)
        self.bxierr_pp = __FFI__.new('bxierr_p[1]')
        self.bxierr_pp[0] = bxierr_p
        self.bxierr_pp = __FFI__.gc(self.bxierr_pp, __BXIBASE_CAPI__.bxierr_destroy)


    def __str__(self):
        return self.message

    @staticmethod
    def chain(cause, err):
        """
        Chain the err with the cause and change cause for the global err

        @param[inout] cause the original error
        @param[in]    err the last error generated
        @return
        """
        err_p = __FFI__.new('bxierr_p[1]')
        err_p[0] = err
        cause_p = __FFI__.new('bxierr_p[1]')
        cause_p[0] = cause
        __BXIBASE_CAPI__.bxierr_chain(cause_p, err_p)
        cause = cause_p[0]

    @staticmethod
    def is_ko(bxierr_p):
        """
        Test if the given ::bxierr_p is ko.

        @param[in] bxierr_p the ::bxierr_p
        @return boolean
        """
        return __BXIBASE_CAPI__.bxierr_isko(bxierr_p)

    @staticmethod
    def is_ok(bxierr_p):
        """
        Test if the given ::bxierr_p is ok.

        @param[in] bxierr_p the ::bxierr_p
        @return boolean
        """
        return __BXIBASE_CAPI__.bxierr_isok(bxierr_p)

    @staticmethod
    def raise_if_ko(bxierr_p):
        """
        Raise a BXICError if the given ::bxierr_p is ko.

        @param[in] bxierr_p the ::bxierr_p
        @return
        @exception BXICError the corresponding BXICError if the given ::bxierr_p is ko.
        """
        if __BXIBASE_CAPI__.bxierr_isko(bxierr_p):
            raise BXICError(bxierr_p)

    @staticmethod
    def errno2bxierr(msg):
        return __BXIBASE_CAPI__.bxierr_fromidx(__BXIBASE_CAPI__.errno,
                                               __FFI__.NULL, "%s", msg)


class BXILogConfigError(BXIError):
    """
    Raised on error during bxilog configuration.
    """
    def __init__(self, msg, cfg):
        """
        Create a new instance with the given message.

        @param[in] msg the exception message
        @param[in] cfg the bxi log configuration as a dictionnary.
        """
        super(BXILogConfigError, self).__init__(msg)
        self.config = cfg

    def get_config(self):
        """
        Return the configuration

        @return the configuration
        """
        return self.config
