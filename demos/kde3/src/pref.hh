#ifndef _TEST2PREF_H_
#define _TEST2PREF_H_

#include <kdialogbase.h>
#include <qframe.h>

class test2PrefPageOne;
class test2PrefPageTwo;

class test2Preferences : public KDialogBase
{
    Q_OBJECT
public:
    test2Preferences();

private:
    test2PrefPageOne *m_pageOne;
    test2PrefPageTwo *m_pageTwo;
};

class test2PrefPageOne : public QFrame
{
    Q_OBJECT
public:
    test2PrefPageOne(QWidget *parent = 0);
};

class test2PrefPageTwo : public QFrame
{
    Q_OBJECT
public:
    test2PrefPageTwo(QWidget *parent = 0);
};

#endif // _TEST2PREF_H_
