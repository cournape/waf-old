#include "config.h"

#include <stdio.h>

int main(int atgc, char **argv)
{

#ifdef HAVE_STRCPY
	printf("HAVE_STRCPY\n");
#else
	printf("no HAVE_STRCPY\n");
#endif
}