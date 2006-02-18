#ifndef _TEST2VIEW_H_
#define _TEST2VIEW_H_

#include <qwidget.h>
#include <kparts/part.h>
#include <test2iface.h>

class QPainter;
class KURL;

/**
 * This is the main view class for test2.  Most of the non-menu,
 * non-toolbar, and non-statusbar (e.g., non frame) GUI code should go
 * here.
 *
 * This test2 uses an HTML component as an example.
 *
 * @short Main view
 * @author ita <ita@localhost.localdomain>
 * @version 0.1
 */
class test2View : public QWidget, public test2Iface
{
    Q_OBJECT
public:
	/**
	 * Default constructor
	 */
    test2View(QWidget *parent);

	/**
	 * Destructor
	 */
    virtual ~test2View();

    /**
     * Random 'get' function
     */
    QString currentURL();

    /**
     * Random 'set' function accessed by DCOP
     */
    virtual void openURL(QString url);

    /**
     * Random 'set' function
     */
    virtual void openURL(const KURL& url);

    /**
     * Print this view to any medium -- paper or not
     */
    void print(QPainter *, int height, int width);

signals:
    /**
     * Use this signal to change the content of the statusbar
     */
    void signalChangeStatusbar(const QString& text);

    /**
     * Use this signal to change the content of the caption
     */
    void signalChangeCaption(const QString& text);

private slots:
    void slotOnURL(const QString& url);
    void slotSetTitle(const QString& title);

private:
    KParts::ReadOnlyPart *m_html;
};

#endif // _TEST2VIEW_H_
