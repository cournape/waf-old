#include <termios.h>

struct termios t; 

t.c_iflag = B9600; 
t.c_oflag = B9600;
