#pragma once
#include <QObject>
#include <QMap>
#include <QVariant>
#include <QString>

// monitor.h의 SensorID와 DataType을 Qt 측에서 미러링
enum SensorID {
    ID_SYS_HEARTBEAT  = 0,
    ID_SYS_UPTIME     = 1,
    ID_SYS_TEMP       = 2,
    ID_SYS_VREF       = 3,
    ID_ENV_TEMP       = 10,
    ID_ENV_HUMI       = 11,
    ID_IN_BUTTON_1    = 30,
    ID_OUT_LED_STATE  = 50,
    ID_OUT_MOTOR_SPEED= 51,
    ID_IMU_ACCEL_X    = 70,
    ID_IMU_ACCEL_Y    = 71,
    ID_IMU_ACCEL_Z    = 72,
      // 무게 데이터로 임시 활용
};

enum DataType {
    TYPE_UINT8  = 0,
    TYPE_INT32  = 1,
    TYPE_FLOAT  = 2,
    TYPE_BOOL   = 3,
    TYPE_STRING = 4
};

struct SensorNode {
    int     id;
    int     type;
    QVariant value;
};

class PacketParser : public QObject
{
    Q_OBJECT
public:
    explicit PacketParser(QObject *parent = nullptr);

    // 수신 버퍼에 데이터를 누적, 완성된 패킷마다 파싱
    void feed(const QByteArray &data);

signals:
    // 파싱 완료된 센서 맵 전달 (key=SensorID, value=SensorNode)
    void packetParsed(QMap<int, SensorNode> nodes);

    // 로그 라인 (일반 텍스트 출력용)
    void logLine(const QString &line);

private:
    QString m_buf;
    void parsePacket(const QString &pkt);
};