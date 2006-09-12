#define  _XOPEN_SOURCE 500

#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

int main()
{
    char *name = NULL;
    int master, err;
    
    master = open("/dev/ptmx", O_RDWR | O_NOCTTY | O_NONBLOCK);
    
    if (master >= 0) {
	err = grantpt(master);
	err = err || unlockpt(master);	
	if (!err) {
	    name = ptsname(master);
	} else {
	    exit(-1);
	}
    } else {
	exit(-1);
    }
    
    close(master);
    exit(0);
}
													