#include "dll.h"
#include <windows.h>

void printMessage(const std::string& str)
{
    MessageBoxA(0, str.c_str(), "message", MB_OK);
}
