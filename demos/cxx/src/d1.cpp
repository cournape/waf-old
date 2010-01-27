#ifdef _MSC_VER
#	define shlib1_EXPORT __declspec(dllexport)
#else
#	define shlib1_EXPORT
#endif

extern shlib1_EXPORT void foo_d1() { }
static const float pi = 3.14F;
