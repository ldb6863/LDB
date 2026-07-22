#pragma once
#include <QObject>
#include <QSerialPort>
#include <QStringList>

class SerialWorker : public QObject
{
    Q_OBJECT
public:
    explicit SerialWorker(QObject *parent = nullptr);
    ~SerialWorker();

    static QStringList availablePorts();

public slots:
    void connectPort(const QString &portName, int baudRate = 9600);
    void disconnectPort();
    void sendCommand(const QString &cmd);

signals:
    void dataReceived(const QByteArray &data);
    void connected(const QString &portName);
    void disconnected();
    void errorOccurred(const QString &msg);

private slots:
    void onReadyRead();
    void onErrorOccurred(QSerialPort::SerialPortError error);

private:
    QSerialPort *m_serial = nullptr;
};