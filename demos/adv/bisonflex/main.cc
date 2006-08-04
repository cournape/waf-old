//#include <stdio.h>
//#include <stdlib.h>
#include <iostream>

using namespace std;
extern int yyparse();

int yyerror (char const *a)
{
  printf("yyerror: (%s)\n", a);
  return 1;
}

int main(int argc, char *argv[])
{
  int yy;
  yy = yyparse();
  if (yy != 0)
  {
	  printf("Syntax or parse error %i. Aborting.\n", yy);
	  return 1;
  }
  else{
	  printf("Success.\n");
  }
}
