
#include "config.h"
#include "another_config.h"

int hmmm = TEST_DEFINE;

#ifndef boo
  #error "boo is not defined"
#endif

#ifndef bidule
  #error "bidule is not defined"
#endif

#if bidule != 34
  #error "bidule is not 34"
#endif

int main()
{
	return 0;
}
