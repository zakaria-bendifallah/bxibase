/* -*- coding: utf-8 -*-
 ###############################################################################
 # Author: Pierre Vigneras <pierre.vigneras@bull.net>
 # Created on: May 24, 2013
 # Contributors:
 ###############################################################################
 # Copyright (C) 2013  Bull S. A. S.  -  All rights reserved
 # Bull, Rue Jean Jaures, B.P.68, 78340, Les Clayes-sous-Bois
 # This is not Free or Open Source software.
 # Please contact Bull S. A. S. for details about its license.
 ###############################################################################
 */

#include <stdlib.h>
#include <assert.h>
#include <string.h>

#include "bxi/base/mem.h"
#include "bxi/base/mem_base.h"
#include "bxi/base/err.h"
#include "bxi/base/log.h"

// *********************************************************************************
// ********************************** Defines **************************************
// *********************************************************************************


// *********************************************************************************
// ********************************** Types ****************************************
// *********************************************************************************

// *********************************************************************************
// **************************** Static function declaration ************************
// *********************************************************************************

// *********************************************************************************
// ********************************** Global Variables *****************************
// *********************************************************************************
SET_LOGGER(MINSTRU_LOGGER, "MINSTRU");


// *********************************************************************************
// ********************************** Implementation   *****************************
// *********************************************************************************

void * bximem_calloc(const size_t n) {
    void * ptr = _bximem_calloc(n);
    TRACE(MINSTRU_LOGGER, "A:%lu:%p", n, ptr);
    return(ptr);
}

/*
 * New realloc
 *
 * Note: If ptr is NULL, acts like bximem_calloc
 */
void * bximem_realloc(void* ptr, const size_t old_size, const size_t new_size) {
    char *new_ptr =  _bximem_realloc(ptr, old_size, new_size);
    if((new_ptr != NULL) && (new_ptr != ptr))
    {
        TRACE(MINSTRU_LOGGER, "F:%p", ptr);
        TRACE(MINSTRU_LOGGER, "A:%lu:%p", new_size, new_ptr);
    }
    return new_ptr;
}


void bximem_destroy(char ** pointer) {

    TRACE(MINSTRU_LOGGER, "F:%p", *pointer);
    _bximem_destroy(pointer);
}

// *********************************************************************************
// ********************************** Static Functions  ****************************
// *********************************************************************************

