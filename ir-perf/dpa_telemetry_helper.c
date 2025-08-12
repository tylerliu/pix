#include <stdio.h>

#ifdef HAVE_DOCA_TELEMETRY_DPA
#include <doca_telemetry_dpa.h>
#endif

int main(int argc, char** argv) {
#ifdef HAVE_DOCA_TELEMETRY_DPA
    // Placeholder: In a DOCA-enabled environment, this would initialize a telemetry context
    // and dump brief process/thread counters. Keep it minimal to avoid build complexity.
    printf("DOCA Telemetry DPA helper: build ok. Implement data collection as needed.\n");
    return 0;
#else
    fprintf(stderr, "DOCA Telemetry DPA not available at build time.\n");
    return 1;
#endif
}
