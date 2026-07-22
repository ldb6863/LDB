#pragma once
#include <QMainWindow>
#include <QTimer>
#include <QLabel>
#include <QPushButton>
#include <QComboBox>
#include <QLineEdit>
#include <QTextEdit>
#include <QProgressBar>
#include "serialworker.h"
#include "packetparser.h"

class MainWindow : public QMainWindow
{
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private:
    void setupUi();
    void setupConnections();
    void applyStyles();
    void updateStateLabel(const QString &state);
    void setConnectedState(bool connected);
    void updateWeightDisplay(float w);          // ← 추가: 무게 공통 업데이트

    // ── 시리얼 / 파서 ────────────────────────────────────
    SerialWorker  *m_serial   = nullptr;
    PacketParser  *m_parser   = nullptr;
    QTimer        *m_portTimer = nullptr;

    // ── Row 1: System Control ────────────────────────────
    QPushButton *m_btnSysOn    = nullptr;
    QPushButton *m_btnSysOff   = nullptr;
    QPushButton *m_btnSysReset = nullptr;
    QPushButton *m_btnTare     = nullptr;

    // ── PIR Sensor Control ───────────────────────────────
    QLabel      *m_lblPirStatus  = nullptr;   // "● INACTIVE" / "⚠ DETECTED"
    QTimer      *m_pirTimer      = nullptr;   // 감지 경과 시간 업데이트용
    int          m_pirElapsedSec = 0;

    // ── Row 1: Operation Status ──────────────────────────
    QLabel *m_lblState1 = nullptr;
    QLabel *m_lblState2 = nullptr;
    QLabel *m_lblState3 = nullptr;
    QLabel *m_lblState4 = nullptr;

    // ── Row 2: Serial ────────────────────────────────────
    QComboBox   *m_cbPort       = nullptr;
    QPushButton *m_btnConnect   = nullptr;
    QLabel      *m_lblConnStatus = nullptr;

    // ── Row 2: Weight ────────────────────────────────────
    QLabel *m_lblWeight     = nullptr;
    QLabel *m_lblSortResult = nullptr;
    QLabel *m_lblRefWeight  = nullptr;

    // ── Row 2: Counters ──────────────────────────────────
    QProgressBar *m_pbHeavy      = nullptr;
    QProgressBar *m_pbLight      = nullptr;
    QLabel       *m_lblHeavyCount = nullptr;
    QLabel       *m_lblLightCount = nullptr;

    // ── Row 3: Parameters ────────────────────────────────
    QLineEdit   *m_edRefWeight     = nullptr;
    QPushButton *m_btnSaveSettings = nullptr;
    // 수정 ③: m_lblTemp, m_lblLed 제거

    // ── Row 3: Log / CLI ────────────────────────────────
    QTextEdit   *m_logEdit   = nullptr;
    QLineEdit   *m_cliInput  = nullptr;
    QPushButton *m_btnSendCli = nullptr;

    // ── 상태 변수 ────────────────────────────────────────
    bool    m_isConnected = false;
    bool    m_pirEnabled  = false;    // PIR 활성화 상태
    bool    m_pirDetecting = false;   // 현재 감지 중 여부
    float   m_lastWeight  = 0.0f;
    float   m_refWeight   = 60.0f;
    int     m_heavyCount  = 0;
    int     m_lightCount  = 0;
    QString m_currentState;

private slots:
    void onPacketParsed(QMap<int, SensorNode> nodes);
    void onLogLine(const QString &line);
    void onConnected(const QString &portName);
    void onDisconnected();
    void onSerialError(const QString &msg);
    void onBtnConnect();
    void onBtnSystemOn();
    void onBtnSystemOff();
    void onBtnSystemReset();
    void onBtnTare();
    void onBtnSendCli();
    void onBtnSaveSettings();
    void refreshPorts();

    void onPirTimerTick();
    void updatePirStatus(bool enabled, bool detecting);
};