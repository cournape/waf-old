
#ifndef _TEST2IFACE_H_
#define _TEST2IFACE_H_

#include <dcopobject.h>

class test2Iface : virtual public DCOPObject
{
  K_DCOP
public:

k_dcop:
  virtual void openURL(QString url) = 0;
};

#endif // _TEST2IFACE_H_
