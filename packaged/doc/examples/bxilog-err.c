#include <sys/types.h>
#include <unistd.h>
#include <string.h>
#include <libgen.h>
#include <sysexits.h>

#include <bxi/base/mem.h>
#include <bxi/base/str.h>
#include <bxi/base/err.h>
#include <bxi/base/time.h>
#include <bxi/base/log.h>

// Create a logger for my module/main
SET_LOGGER(MY_LOGGER, "my.logger");

// This function does not raise an error
// It deals with error itself, internally
// using BXILOG_REPORT()
void foo_noraise(void) {
    struct timespec start;
    bxierr_p err = bxitime_get(CLOCK_MONOTONIC, &start);
    BXILOG_REPORT(MY_LOGGER,
                  BXILOG_ERROR,
                  err,
                  "Calling bxitime_gettime() failed");
    DEBUG(MY_LOGGER, "Producing a log");
    double duration;
    err = bxitime_duration(CLOCK_MONOTONIC, start, &duration);
    BXILOG_REPORT(MY_LOGGER,
                  BXILOG_ERROR,
                  err,
                  "Calling bxitime_duration() failed");
    OUT(MY_LOGGER, "Duration: %lf", duration);
}

// This function is the equivalent but it does raise errors
// It uses BXIERR_CHAIN() for this purpose.
bxierr_p bar_raise(void) {
    struct timespec start;
    bxierr_p err = BXIERR_OK, err2;
    err2 = bxitime_get(CLOCK_MONOTONIC, &start);
    BXIERR_CHAIN(err, err2); // This makes err2->cause = err, err=err2 on error
    // We choose to continue here, despite the error.
    // We might have returned sooner with:
    // if (bxierr_isko(err)) return err;
    DEBUG(MY_LOGGER, "Producing a log");
    double duration = 0;
    err = bxitime_duration(CLOCK_MONOTONIC, start, &duration);
    BXIERR_CHAIN(err, err2);
    OUT(MY_LOGGER, "Duration: %lf", duration);
    return err;
}

int main(int argc, char** argv) {

    if (argc != 1) exit(EX_SOFTWARE);

    // Produce logs on stdout, and '/dev/null'
    bxilog_config_p config = bxilog_basic_config(argv[0],
                                                 "/dev/null",
                                                 O_CREAT | O_TRUNC,
                                                 BXILOG_FILTERS_ALL_OUTPUT);
    bxierr_p err = bxilog_init(config);
    // Use BXILOG_REPORT for error reporting, the error is destroyed.
    // If the logging library raises an error,
    // it has not been initialized. In such a case, the implementation takes care of that
    // and display a message on stderr.
    BXILOG_REPORT(MY_LOGGER, BXILOG_CRITICAL, err,
                  "Can't initialize the BXI logging library");

    DEBUG(MY_LOGGER, "Calling noraise");
    foo_noraise();
    DEBUG(MY_LOGGER, "Calling raise");
    err = bar_raise();
    if (bxierr_isko(err)) {
        // Exit the program
        BXIEXIT(EX_SOFTWARE, err, MY_LOGGER, BXILOG_CRITICAL);
        // The following statement must never be reached
        BXIUNREACHABLE_STATEMENT(MY_LOGGER);
    }

    err = bxilog_finalize(true);
    BXILOG_REPORT(MY_LOGGER, BXILOG_CRITICAL, err,
                  "Can't finalize the BXI logging library");
    exit(EXIT_SUCCESS);
}
