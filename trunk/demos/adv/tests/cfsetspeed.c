#include <termios.h>

struct termios t; 

cfsetspeed(&t, B9600);
