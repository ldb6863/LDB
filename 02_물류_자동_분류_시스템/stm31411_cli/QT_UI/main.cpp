#include <QApplication>
#include "mainwindow.h"

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    app.setApplicationName("STM32 Sorting Monitor");
    app.setOrganizationName("KoLongLong");

    MainWindow w;
    w.show();

    return app.exec();
}