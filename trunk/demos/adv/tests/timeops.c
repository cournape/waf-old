#include <sys/time.h>
struct timeval tv;

timerisset(&tv);
timerclear(&tv); 

timercmp(&tv, &tv, <);
timeradd(&tv, &tv, &tv); 
timersub(&tv, &tv, &tv);
