#include <termios.h>
struct termios t; 

cfsetispeed(&t, B9600);
cfsetospeed(&t, B9600);

