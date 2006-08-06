
// using custom extensions is not recommended, but it should work
#include "pref.hh"

#include <klocale.h>

#include <qlayout.h>
#include <qlabel.h>

test2Preferences::test2Preferences()
    : KDialogBase(TreeList, i18n("test2 Preferences"),
                  Help|Default|Ok|Apply|Cancel, Ok)
{
    // this is the base class for your preferences dialog.  it is now
    // a Treelist dialog.. but there are a number of other
    // possibilities (including Tab, Swallow, and just Plain)
    QFrame *frame;
    frame = addPage(i18n("First Page"), i18n("Page One Options"));
    m_pageOne = new test2PrefPageOne(frame);

    frame = addPage(i18n("Second Page"), i18n("Page Two Options"));
    m_pageTwo = new test2PrefPageTwo(frame);
}

test2PrefPageOne::test2PrefPageOne(QWidget *parent)
    : QFrame(parent)
{
    QHBoxLayout *layout = new QHBoxLayout(this);
    layout->setAutoAdd(true);

    new QLabel(i18n("Add something here"), this);
}

test2PrefPageTwo::test2PrefPageTwo(QWidget *parent)
    : QFrame(parent)
{
    QHBoxLayout *layout = new QHBoxLayout(this);
    layout->setAutoAdd(true);

    new QLabel(i18n("Add something here"), this);
}
#include "pref.moc"
