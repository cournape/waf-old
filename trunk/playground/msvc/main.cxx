#include "lib.h"
#include "dll.h"
#include <windows.h>

int WINAPI WinMain( HINSTANCE hInst,
                    HINSTANCE hPrevInstance,
                    LPSTR lpCmdLine,
                    int nCmdShow)
{
    printMessage(getMessage());
    return 0;
}
