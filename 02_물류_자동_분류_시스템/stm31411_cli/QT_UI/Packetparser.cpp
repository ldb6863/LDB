#include "packetparser.h"
#include <QStringList>

PacketParser::PacketParser(QObject *parent) : QObject(parent) {}

void PacketParser::feed(const QByteArray &data)
{
    m_buf += QString::fromUtf8(data);

    // 완성된 패킷($...#)을 모두 추출
    while (true) {
        int start = m_buf.indexOf('$');
        int end   = m_buf.indexOf('#', start);
        if (start == -1 || end == -1) break;

        QString pkt = m_buf.mid(start + 1, end - start - 1);
        m_buf = m_buf.mid(end + 1); // 소비

        parsePacket(pkt);
    }

    // $ 이전의 일반 텍스트(cliPrintf 출력)는 \n 단위로 잘라서 방출
    // \n 없이 중간에 끊긴 데이터는 m_buf에 남겨두고 다음 feed()를 기다림
    int dollar = m_buf.indexOf('$');
    QString plain = (dollar == -1) ? m_buf : m_buf.left(dollar);

    while (true) {
        int nl = plain.indexOf('\n');
        if (nl == -1) break;  // 아직 줄 완성 안 됨 → 대기

        QString line = plain.left(nl).trimmed();
        plain = plain.mid(nl + 1);

        if (!line.isEmpty())
            emit logLine(line);
    }

    // 소비된 만큼 버퍼에서 제거, 미완성 줄은 유지
    if (dollar == -1)
        m_buf = plain;
    else
        m_buf = plain + m_buf.mid(dollar);
}

void PacketParser::parsePacket(const QString &pkt)
{
    // 포맷: N,id:type:value,id:type:value,...
    QStringList parts = pkt.split(',');
    if (parts.isEmpty()) return;

    // 첫 토큰은 count
    bool ok;
    int count = parts[0].toInt(&ok);
    if (!ok || count <= 0) return;

    QMap<int, SensorNode> nodes;

    for (int i = 1; i <= count && i < parts.size(); i++) {
        QStringList fields = parts[i].split(':');
        if (fields.size() < 3) continue;

        SensorNode node;
        node.id   = fields[0].toInt();
        node.type = fields[1].toInt();

        switch (node.type) {
        case TYPE_FLOAT:
            node.value = fields[2].toFloat();
            break;
        case TYPE_INT32:
            node.value = fields[2].toInt();
            break;
        case TYPE_UINT8:
        case TYPE_BOOL:
            node.value = fields[2].toUInt();
            break;
        default:
            node.value = fields[2];
            break;
        }

        nodes[node.id] = node;
    }

    if (!nodes.isEmpty())
        emit packetParsed(nodes);
}