#ifndef _INCLUDES_H_
#define _INCLUDES_H_
#include "includes.h"
#endif

static IRAM_ATTR int64_t get_systime_us(void){
    struct timeval tv;
    int ret = gettimeofday(&tv, NULL);
    
    assert(ret == 0);

    return (int64_t)tv.tv_sec * 1000000L + (int64_t)tv.tv_usec;
}

static IRAM_ATTR void reset_systime(void){
    struct timeval tv;
    tv.tv_sec = 0;
    tv.tv_usec = 0;
    
    int ret = settimeofday(&tv, NULL);
    
    assert(ret == 0);
}
