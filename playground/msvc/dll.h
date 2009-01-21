#ifndef DLL_H_
#define DLL_H_

#include <string>

#ifndef BUILDING_DLL
# define EXPORT __declspec(dllimport)
#else
# define EXPORT __declspec(dllexport)
#endif

EXPORT void printMessage(const std::string& message);

#endif
