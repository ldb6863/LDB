#include "serialworker.h"
#include <QSerialPortInfo>

SerialWorker::SerialWorker(QObject *parent) : QObject(parent)
{
    m_serial = new QSerialPort(this);
    connect(m_serial, &QSerialPort::readyRead,    this, &SerialWorker::onReadyRead);
    connect(m_serial, &QSerialPort::errorOccurred,this, &SerialWorker::onErrorOccurred);
}

SerialWorker::~SerialWorker()
{
    disconnectPort();
}

QStringList SerialWorker::availablePorts()
{
    QStringList list;
    for (const QSerialPortInfo &info : QSerialPortInfo::availablePorts())
        list << info.portName();
    return list;
}

void SerialWorker::connectPort(const QString &portName, int baudRate)
{
    if (m_serial->isOpen()) m_serial->close();

    m_serial->setPortName(portName);
    m_serial->setBaudRate(baudRate);
    m_serial->setDataBits(QSerialPort::Data8);
    m_serial->setParity(QSerialPort::NoParity);
    m_serial->setStopBits(QSerialPort::OneStop);
    m_serial->setFlowControl(QSerialPort::NoFlowControl);

    if (m_serial->open(QIODevice::ReadWrite)) {
        emit connected(portName);
    } else {
        emit errorOccurred(m_serial->errorString());
    }
}

void SerialWorker::disconnectPort()
{
    if (m_serial && m_serial->isOpen()) {
        m_serial->close();
        emit disconnected();
    }
}

void SerialWorker::sendCommand(const QString &cmd)
{
    if (!m_serial || !m_serial->isOpen()) return;
    QString line = cmd.trimmed() + "\r\n";
    m_serial->write(line.toLatin1());
}

void SerialWorker::onReadyRead()
{
    QByteArray data = m_serial->readAll();
    if (!data.isEmpty())
        emit dataReceived(data);
}

void SerialWorker::onErrorOccurred(QSerialPort::SerialPortError error)
{
    if (error != QSerialPort::NoError)
        emit errorOccurred(m_serial->errorString());
}