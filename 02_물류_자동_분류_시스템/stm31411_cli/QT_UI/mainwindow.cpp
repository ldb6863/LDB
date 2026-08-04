#include "mainwindow.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QGroupBox>
#include <QFrame>
#include <QSplitter>
#include <QDateTime>
#include <QScrollBar>
#include <QSerialPortInfo>
#include <QFont>
#include <QFontDatabase>
#include <QRegularExpression>       // ← 추가

// ── 색상 상수 ───────────────────────────────────────────────
static const QString CLR_BG        = "#0d1117";
static const QString CLR_PANEL     = "#161b22";
static const QString CLR_BORDER    = "#30363d";
static const QString CLR_GREEN     = "#2ea043";
static const QString CLR_GREEN_LT  = "#3fb950";
static const QString CLR_RED       = "#da3633";
static const QString CLR_ORANGE    = "#e3b341";
static const QString CLR_BLUE      = "#1f6feb";
static const QString CLR_BLUE_LT   = "#388bfd";
static const QString CLR_TEXT      = "#e6edf3";
static const QString CLR_MUTED     = "#8b949e";
static const QString CLR_ACTIVE    = "#238636";
static const QString CLR_INACTIVE  = "#21262d";

static QLabel* makeSeparator()
{
    QLabel *l = new QLabel();
    l->setFixedHeight(1);
    l->setStyleSheet("background:#30363d;");
    return l;
}

MainWindow::MainWindow(QWidget *parent) : QMainWindow(parent)
{
    m_serial    = new SerialWorker(this);
    m_parser    = new PacketParser(this);
    m_portTimer = new QTimer(this);
    m_pirTimer  = new QTimer(this);
    m_pirTimer->setInterval(1000);

    setupUi();
    setupConnections();
    applyStyles();

    setWindowTitle("ROBOTIC WEIGHT SORTING SYSTEM CONTROLLER");
    resize(1200, 760);

    m_portTimer->start(2000);
    refreshPorts();
}

MainWindow::~MainWindow() {}

// ═══════════════════════════════════════════════════════════
//  UI 레이아웃
// ═══════════════════════════════════════════════════════════
void MainWindow::setupUi()
{
    QWidget *central = new QWidget(this);
    setCentralWidget(central);

    // ── 타이틀 바 ─────────────────────────────────────────
    QLabel *title = new QLabel("⚙  ROBOTIC WEIGHT SORTING SYSTEM CONTROLLER");
    title->setObjectName("titleBar");

    // ══════════════════════════════════════════════════════
    //  ROW 1:  [SYSTEM CONTROL]  [OPERATION STATUS]
    // ══════════════════════════════════════════════════════
    QGroupBox *grpSysCtrl = new QGroupBox("⚙  SYSTEM CONTROL  ①");
    grpSysCtrl->setObjectName("panelGroup");

    m_btnSysOn    = new QPushButton("SYSTEM ON");
    m_btnSysOff   = new QPushButton("SYSTEM OFF");
    m_btnSysReset = new QPushButton("SYSTEM RESET");
    m_btnTare     = new QPushButton("TARE");

    m_btnSysOn->setObjectName("btnGreen");
    m_btnSysOff->setObjectName("btnRed");
    m_btnSysReset->setObjectName("btnBlue");
    m_btnTare->setObjectName("btnOrange");

    QGridLayout *sysCtrlLayout = new QGridLayout(grpSysCtrl);
    sysCtrlLayout->addWidget(m_btnSysOn,    0, 0);
    sysCtrlLayout->addWidget(m_btnTare,     0, 1, 2, 1);
    sysCtrlLayout->addWidget(m_btnSysOff,   1, 0);
    sysCtrlLayout->addWidget(m_btnSysReset, 2, 0);

    QLabel *tLabel = new QLabel("Zero calibration");
    tLabel->setObjectName("labelMuted");
    tLabel->setAlignment(Qt::AlignCenter);
    sysCtrlLayout->addWidget(tLabel, 3, 1);

    // ── 1-2: Operation Status Visualization ─────────────
    QGroupBox *grpOpStatus = new QGroupBox("▶  OPERATION STATUS VISUALIZATION  ②");
    grpOpStatus->setObjectName("panelGroup");

    m_lblState1 = new QLabel("1. WEIGHT\nDETECTION");
    m_lblState2 = new QLabel("2. ROBOT ARM\nACTION");
    m_lblState3 = new QLabel("3. CONVEYOR\nBELT MOTION");
    m_lblState4 = new QLabel("4. SORTING\nCOMPLETE");

    for (QLabel *l : {m_lblState1, m_lblState2, m_lblState3, m_lblState4}) {
        l->setObjectName("stateBox");
        l->setAlignment(Qt::AlignCenter);
        l->setFixedHeight(60);
    }

    QHBoxLayout *stateRow = new QHBoxLayout();
    stateRow->setSpacing(4);
    stateRow->setContentsMargins(4, 4, 4, 4);
    stateRow->addWidget(m_lblState1);
    stateRow->addWidget(new QLabel("→"), 0, Qt::AlignCenter);
    stateRow->addWidget(m_lblState2);
    stateRow->addWidget(new QLabel("→"), 0, Qt::AlignCenter);
    stateRow->addWidget(m_lblState3);
    stateRow->addWidget(new QLabel("→"), 0, Qt::AlignCenter);
    stateRow->addWidget(m_lblState4);

    QVBoxLayout *opLayout = new QVBoxLayout(grpOpStatus);
    opLayout->setSpacing(4);
    opLayout->addLayout(stateRow);

    QHBoxLayout *row1 = new QHBoxLayout();
    row1->addWidget(grpSysCtrl, 3);
    row1->addWidget(grpOpStatus, 7);

    // ── 1-3: PIR Sensor ─────────────────────────────────
    QGroupBox *grpPir = new QGroupBox("🚨  PIR SENSOR  ⑥");
    grpPir->setObjectName("panelGroup");

    m_lblPirStatus = new QLabel("● INACTIVE");
    m_lblPirStatus->setObjectName("pirInactive");
    m_lblPirStatus->setAlignment(Qt::AlignCenter);

    QVBoxLayout *pirLayout = new QVBoxLayout(grpPir);
    pirLayout->setSpacing(4);
    pirLayout->addWidget(m_lblPirStatus, 1, Qt::AlignCenter);

    row1->addWidget(grpPir, 3);

    // ══════════════════════════════════════════════════════
    //  ROW 2:  [SERIAL]  [WEIGHT]  [COUNTERS]
    // ══════════════════════════════════════════════════════
    QGroupBox *grpSerial = new QGroupBox("🔌  SERIAL CONNECTION STATUS");
    grpSerial->setObjectName("panelGroup");

    m_cbPort     = new QComboBox();
    m_btnConnect = new QPushButton("CONNECT");
    m_btnConnect->setObjectName("btnBlue");
    m_lblConnStatus = new QLabel("● DISCONNECTED");
    m_lblConnStatus->setObjectName("lblDisconnected");

    QVBoxLayout *serialLayout = new QVBoxLayout(grpSerial);
    serialLayout->addWidget(m_cbPort);
    serialLayout->addWidget(m_btnConnect);
    serialLayout->addWidget(makeSeparator());
    serialLayout->addWidget(m_lblConnStatus);
    serialLayout->addStretch();

    // ── 2-2: Weight & Sorting Result ────────────────────
    QGroupBox *grpWeight = new QGroupBox("⚖  WEIGHT MEASUREMENT & SORTING RESULT  ③");
    grpWeight->setObjectName("panelGroup");

    QLabel *wLabel = new QLabel("CURRENT WEIGHT:");
    wLabel->setObjectName("labelMuted");
    wLabel->setAlignment(Qt::AlignCenter);

    m_lblWeight = new QLabel("--- g");
    m_lblWeight->setObjectName("weightDisplay");
    m_lblWeight->setAlignment(Qt::AlignCenter);

    QLabel *srLabel = new QLabel("SORTING RESULT:");
    srLabel->setObjectName("labelMuted");
    srLabel->setAlignment(Qt::AlignCenter);

    m_lblSortResult = new QLabel("---");
    m_lblSortResult->setObjectName("sortResult");
    m_lblSortResult->setAlignment(Qt::AlignCenter);

    m_lblRefWeight = new QLabel("■  REF: 60 g");
    m_lblRefWeight->setObjectName("labelMuted");
    m_lblRefWeight->setAlignment(Qt::AlignCenter);

    QVBoxLayout *weightLayout = new QVBoxLayout(grpWeight);
    weightLayout->addWidget(wLabel);
    weightLayout->addWidget(m_lblWeight);
    weightLayout->addWidget(makeSeparator());
    weightLayout->addWidget(srLabel);
    weightLayout->addWidget(m_lblSortResult);
    weightLayout->addWidget(m_lblRefWeight);

    // ── 2-3: Sorting Counters ───────────────────────────
    QGroupBox *grpCounters = new QGroupBox("📊  SORTING COUNTERS  ④");
    grpCounters->setObjectName("panelGroup");

    QLabel *clLabel = new QLabel("CLASSIFIED ITEM TOTALS");
    clLabel->setObjectName("labelMuted");
    clLabel->setAlignment(Qt::AlignCenter);

    QLabel *hLabel = new QLabel("HEAVY");
    QLabel *lLabel = new QLabel("LIGHT");
    hLabel->setAlignment(Qt::AlignCenter);
    hLabel->setStyleSheet("color:#e3b341;font-weight:bold;");
    lLabel->setAlignment(Qt::AlignCenter);
    lLabel->setStyleSheet("color:#3fb950;font-weight:bold;");

    m_pbHeavy = new QProgressBar();
    m_pbLight = new QProgressBar();
    m_pbHeavy->setObjectName("pbHeavy");
    m_pbLight->setObjectName("pbLight");
    m_pbHeavy->setOrientation(Qt::Vertical);
    m_pbLight->setOrientation(Qt::Vertical);
    m_pbHeavy->setRange(0, 20);
    m_pbLight->setRange(0, 20);
    m_pbHeavy->setValue(0);
    m_pbLight->setValue(0);
    m_pbHeavy->setFixedWidth(50);
    m_pbLight->setFixedWidth(50);
    m_pbHeavy->setTextVisible(false);
    m_pbLight->setTextVisible(false);

    m_lblHeavyCount = new QLabel("0");
    m_lblLightCount = new QLabel("0");
    m_lblHeavyCount->setAlignment(Qt::AlignCenter);
    m_lblLightCount->setAlignment(Qt::AlignCenter);
    m_lblHeavyCount->setStyleSheet("font-size:28px;font-weight:bold;color:#e3b341;");
    m_lblLightCount->setStyleSheet("font-size:28px;font-weight:bold;color:#3fb950;");

    QHBoxLayout *barRow = new QHBoxLayout();
    QVBoxLayout *hCol = new QVBoxLayout();
    QVBoxLayout *lCol = new QVBoxLayout();
    hCol->addWidget(hLabel);
    hCol->addWidget(m_pbHeavy, 1, Qt::AlignHCenter);
    hCol->addWidget(m_lblHeavyCount);
    lCol->addWidget(lLabel);
    lCol->addWidget(m_pbLight, 1, Qt::AlignHCenter);
    lCol->addWidget(m_lblLightCount);
    barRow->addLayout(hCol);
    barRow->addLayout(lCol);

    QVBoxLayout *counterLayout = new QVBoxLayout(grpCounters);
    counterLayout->addWidget(clLabel);
    counterLayout->addLayout(barRow);

    QHBoxLayout *row2 = new QHBoxLayout();
    row2->addWidget(grpSerial, 2);
    row2->addWidget(grpWeight, 4);
    row2->addWidget(grpCounters, 2);

    // ══════════════════════════════════════════════════════
    //  ROW 3:  [PARAMETERS]  [LOG]  [CLI]
    //  수정 ③: MCU TEMP / LED 위젯 제거 → REF WEIGHT + SAVE만 유지
    // ══════════════════════════════════════════════════════
    QGroupBox *grpParams = new QGroupBox("⚙  PARAMETER SETTINGS  ⑤");
    grpParams->setObjectName("panelGroup");

    QLabel *refLabel  = new QLabel("REFERENCE WEIGHT (g)");
    m_edRefWeight     = new QLineEdit("60.0");
    m_btnSaveSettings = new QPushButton("SAVE SETTINGS");
    m_btnSaveSettings->setObjectName("btnGreen");

    QVBoxLayout *paramLayout = new QVBoxLayout(grpParams);
    paramLayout->addWidget(refLabel);
    paramLayout->addWidget(m_edRefWeight);
    paramLayout->addWidget(m_btnSaveSettings);
    paramLayout->addStretch();

    // ── 3-2: Log Output ─────────────────────────────────
    QGroupBox *grpLog = new QGroupBox("📋  SYSTEM LOG");
    grpLog->setObjectName("panelGroup");

    m_logEdit = new QTextEdit();
    m_logEdit->setReadOnly(true);
    m_logEdit->setObjectName("logEdit");
    m_logEdit->setPlaceholderText("Serial output will appear here...");

    QVBoxLayout *logLayout = new QVBoxLayout(grpLog);
    logLayout->addWidget(m_logEdit);

    // ── 3-3: CLI Input ──────────────────────────────────
    QGroupBox *grpCli = new QGroupBox("⌨  CLI COMMAND");
    grpCli->setObjectName("panelGroup");

    m_cliInput   = new QLineEdit();
    m_cliInput->setPlaceholderText("e.g. system on / loadcell tare / conv start");
    m_btnSendCli = new QPushButton("SEND");
    m_btnSendCli->setObjectName("btnBlue");

    auto makeQuick = [this](const QString &label, const QString &cmd) {
        QPushButton *b = new QPushButton(label);
        b->setObjectName("btnQuick");
        connect(b, &QPushButton::clicked, this, [this, cmd](){
            if (m_isConnected) m_serial->sendCommand(cmd);
        });
        return b;
    };

    QGridLayout *quickGrid = new QGridLayout();
    quickGrid->addWidget(makeQuick("system on",    "system on"),    0, 0);
    quickGrid->addWidget(makeQuick("system off",   "system off"),   0, 1);
    quickGrid->addWidget(makeQuick("conv start",   "conv start"),   1, 0);
    quickGrid->addWidget(makeQuick("conv stop",    "conv stop"),    1, 1);
    quickGrid->addWidget(makeQuick("loadcell tare","loadcell tare"),2, 0);
    quickGrid->addWidget(makeQuick("flag center",  "flag center"),  2, 1);
    quickGrid->addWidget(makeQuick("pir on",       "pir on"),       3, 0);
    quickGrid->addWidget(makeQuick("pir off",      "pir off"),      3, 1);
    quickGrid->addWidget(makeQuick("pir status",   "pir status"),   4, 0);
    quickGrid->addWidget(makeQuick("pir read",     "pir read"),     4, 1);

    QHBoxLayout *cliRow = new QHBoxLayout();
    cliRow->addWidget(m_cliInput);
    cliRow->addWidget(m_btnSendCli);

    QVBoxLayout *cliLayout = new QVBoxLayout(grpCli);
    cliLayout->addLayout(cliRow);
    cliLayout->addLayout(quickGrid);

    QHBoxLayout *row3 = new QHBoxLayout();
    row3->addWidget(grpParams, 2);
    row3->addWidget(grpLog,    4);
    row3->addWidget(grpCli,    3);

    // ══════════════════════════════════════════════════════
    //  전체 레이아웃 조립
    // ══════════════════════════════════════════════════════
    QVBoxLayout *mainLayout = new QVBoxLayout(central);
    mainLayout->setSpacing(8);
    mainLayout->setContentsMargins(10, 8, 10, 8);
    mainLayout->addWidget(title);
    mainLayout->addLayout(row1, 3);
    mainLayout->addLayout(row2, 4);
    mainLayout->addLayout(row3, 3);
}

// ═══════════════════════════════════════════════════════════
//  시그널/슬롯 연결
// ═══════════════════════════════════════════════════════════
void MainWindow::setupConnections()
{
    connect(m_serial, &SerialWorker::dataReceived, m_parser, &PacketParser::feed);
    connect(m_serial, &SerialWorker::connected,    this, &MainWindow::onConnected);
    connect(m_serial, &SerialWorker::disconnected, this, &MainWindow::onDisconnected);
    connect(m_serial, &SerialWorker::errorOccurred,this, &MainWindow::onSerialError);

    connect(m_parser, &PacketParser::packetParsed, this, &MainWindow::onPacketParsed);
    connect(m_parser, &PacketParser::logLine,       this, &MainWindow::onLogLine);

    connect(m_btnConnect,     &QPushButton::clicked, this, &MainWindow::onBtnConnect);
    connect(m_btnSysOn,       &QPushButton::clicked, this, &MainWindow::onBtnSystemOn);
    connect(m_btnSysOff,      &QPushButton::clicked, this, &MainWindow::onBtnSystemOff);
    connect(m_btnSysReset,    &QPushButton::clicked, this, &MainWindow::onBtnSystemReset);
    connect(m_btnTare,        &QPushButton::clicked, this, &MainWindow::onBtnTare);
    connect(m_btnSendCli,     &QPushButton::clicked, this, &MainWindow::onBtnSendCli);
    connect(m_btnSaveSettings,&QPushButton::clicked, this, &MainWindow::onBtnSaveSettings);
    connect(m_cliInput, &QLineEdit::returnPressed,   this, &MainWindow::onBtnSendCli);

    connect(m_portTimer, &QTimer::timeout, this, &MainWindow::refreshPorts);

    connect(m_pirTimer,   &QTimer::timeout,      this, &MainWindow::onPirTimerTick);
}

// ═══════════════════════════════════════════════════════════
//  스타일시트
// ═══════════════════════════════════════════════════════════
void MainWindow::applyStyles()
{
    setStyleSheet(QString(R"(
        QMainWindow, QWidget {
            background-color: %1;
            color: %2;
            font-family: 'Consolas', 'Malgun Gothic', '맑은 고딕', 'Courier New', monospace;
            font-size: 13px;
        }
        QLabel#titleBar {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #1f2937, stop:1 #111827);
            color: #e6edf3;
            font-size: 16px;
            font-weight: bold;
            padding: 10px 16px;
            border: 1px solid #30363d;
            border-radius: 4px;
            letter-spacing: 1px;
        }
        QGroupBox {
            background-color: %3;
            border: 1px solid %4;
            border-radius: 6px;
            margin-top: 20px;
            padding: 8px;
            font-size: 11px;
            font-weight: bold;
            color: #8b949e;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 2px 8px;
            color: #8b949e;
        }
        QPushButton {
            border: 1px solid #30363d;
            border-radius: 4px;
            padding: 8px 12px;
            font-weight: bold;
            font-size: 12px;
            min-height: 32px;
        }
        QPushButton#btnGreen  { background-color:#238636; color:#fff; border-color:#2ea043; }
        QPushButton#btnGreen:hover   { background-color:#2ea043; }
        QPushButton#btnGreen:pressed { background-color:#196127; }
        QPushButton#btnRed    { background-color:#b91c1c; color:#fff; border-color:#da3633; }
        QPushButton#btnRed:hover     { background-color:#da3633; }
        QPushButton#btnRed:pressed   { background-color:#7f1d1d; }
        QPushButton#btnBlue   { background-color:#1d4ed8; color:#fff; border-color:#1f6feb; }
        QPushButton#btnBlue:hover    { background-color:#1f6feb; }
        QPushButton#btnBlue:pressed  { background-color:#1e3a8a; }
        QPushButton#btnOrange {
            background-color:#92400e; color:#e3b341; border-color:#e3b341;
            font-size:16px; min-height:52px;
        }
        QPushButton#btnOrange:hover  { background-color:#b45309; }
        QPushButton#btnQuick {
            background-color:#21262d; color:#8b949e; border-color:#30363d;
            padding:5px 8px; font-size:11px; min-height:26px;
        }
        QPushButton#btnQuick:hover   { background-color:#30363d; color:#e6edf3; }
        QComboBox {
            background-color:#21262d; border:1px solid #30363d; border-radius:4px;
            padding:5px 8px; color:#e6edf3; min-height:30px;
        }
        QComboBox::drop-down { border:none; }
        QComboBox QAbstractItemView {
            background:#1c2128; border:1px solid #30363d; color:#e6edf3;
            selection-background-color:#1f6feb;
        }
        QLineEdit {
            background-color:#21262d; border:1px solid #30363d; border-radius:4px;
            padding:5px 8px; color:#e6edf3; min-height:28px;
        }
        QLineEdit:focus { border-color:#1f6feb; }
        QTextEdit#logEdit {
            background-color:#0d1117; border:1px solid #21262d; border-radius:4px;
            color:#3fb950; font-family:'Consolas','Malgun Gothic','맑은 고딕',monospace; font-size:12px; padding:4px;
        }
        QLabel#weightDisplay {
            color:#60a5fa; font-size:48px; font-weight:bold;
            font-family:'Consolas',monospace;
        }
        QLabel#sortResult     { font-size:32px; font-weight:bold; }
        QLabel#stateBox {
            background-color:#21262d; border:1px solid #30363d; border-radius:4px;
            color:#8b949e; font-size:11px; font-weight:bold;
        }
        QLabel#stateBoxActive {
            background-color:#1a3a2a; border:1px solid #2ea043; border-radius:4px;
            color:#3fb950; font-size:11px; font-weight:bold;
        }
        QLabel#lblConnected    { color:#3fb950; font-weight:bold; }
        QLabel#lblDisconnected { color:#8b949e; font-weight:bold; }
        QLabel#labelMuted      { color:#8b949e; font-size:11px; }
        QProgressBar {
            background-color:#21262d; border:1px solid #30363d; border-radius:3px;
        }
        QProgressBar#pbHeavy::chunk { background-color:#e3b341; border-radius:2px; }
        QProgressBar#pbLight::chunk { background-color:#3fb950; border-radius:2px; }
        QScrollBar:vertical  { background:#161b22; width:8px; }
        QScrollBar::handle:vertical { background:#30363d; border-radius:4px; }

        QLabel#pirDisabled {
            background-color:#21262d; border:1px solid #30363d; border-radius:3px;
            color:#8b949e; font-size:11px; font-weight:bold; padding:2px 6px;
        }
        QLabel#pirEnabled {
            background-color:#1a3a1a; border:1px solid #2ea043; border-radius:3px;
            color:#3fb950; font-size:11px; font-weight:bold; padding:2px 6px;
        }
        QLabel#pirInactive {
            background-color:#21262d; border:1px solid #30363d; border-radius:4px;
            color:#8b949e; font-size:28px; font-weight:bold;
            min-height:80px;
        }
        QLabel#pirActive {
            background-color:#1a3a1a; border:1px solid #2ea043; border-radius:4px;
            color:#3fb950; font-size:28px; font-weight:bold;
            min-height:80px;
        }
        QLabel#pirDetecting {
            background-color:#3a0a0a; border:2px solid #da3633; border-radius:4px;
            color:#ff6b6b; font-size:22px; font-weight:bold;
            min-height:80px;
        }
    )")
                      .arg(CLR_BG, CLR_TEXT, CLR_PANEL, CLR_BORDER));
}

// ═══════════════════════════════════════════════════════════
//  무게 표시 공통 함수  (수정 ①②)
// ═══════════════════════════════════════════════════════════
void MainWindow::updateWeightDisplay(float w)
{
    m_lastWeight = w;
    m_lblWeight->setText(QString("%1 g").arg(w, 0, 'f', 1));

    if (w < 5.0f) {
        m_lblSortResult->setText("---");
        m_lblSortResult->setStyleSheet(
            "font-size:32px;font-weight:bold;color:#8b949e;");
    } else if (w >= m_refWeight) {
        m_lblSortResult->setText("HEAVY");
        m_lblSortResult->setStyleSheet(
            "font-size:32px;font-weight:bold;color:#e3b341;");
    } else {
        m_lblSortResult->setText("LIGHT");
        m_lblSortResult->setStyleSheet(
            "font-size:32px;font-weight:bold;color:#3fb950;");
    }
}

// ═══════════════════════════════════════════════════════════
//  패킷 파싱 (수정 ①)
//  - ID_LOADCELL_WEIGHT(20) 케이스를 명시적으로 추가
//  - default 케이스도 유지 (fallback)
// ═══════════════════════════════════════════════════════════
void MainWindow::onPacketParsed(QMap<int, SensorNode> nodes)
{
    for (auto it = nodes.begin(); it != nodes.end(); ++it) {
        int id         = it.key();
        SensorNode &n  = it.value();

        switch (id) {
        // ── MCU 내부 온도 (표시 위젯 제거됐으므로 로그만) ──
        case ID_SYS_TEMP:
        case ID_ENV_TEMP:
            // UI 위젯 제거됨 → 아무것도 안 함 (로그는 onLogLine이 처리)
            break;

        // ── LED ─────────────────────────────────────────
        case ID_OUT_LED_STATE:
            // TEMP/LED UI 제거했으므로 무시
            break;

        // ── Uptime ──────────────────────────────────────
        case ID_SYS_UPTIME:
            break;

        // ── 로드셀 무게 (ID=20, ap.c에서 사용하는 실제 ID로 조정) ──
        // STM32 ap.c 에서 monitorUpdateValue(20, TYPE_FLOAT, &weight) 처럼
        // 보내는 ID를 확인 후 아래 숫자를 맞춰주세요.
        case 11:   // ID_LOADCELL_WEIGHT — ap.c의 실제 ID로 변경하세요
        {
            float w = n.value.toFloat();
            updateWeightDisplay(w);
            break;
        }

        default:
        {
            // 알 수 없는 ID: FLOAT 또는 INT32이면 무게 후보로 해석
            // (ap.c의 weight ID가 위 case에 없을 경우를 대비한 fallback)
            if (n.type == TYPE_FLOAT || n.type == TYPE_INT32) {
                float w = n.value.toFloat();
                if (w >= 0.0f && w < 5000.0f) {
                    updateWeightDisplay(w);
                }
            }
            break;
        }
        }
    }
}

// ═══════════════════════════════════════════════════════════
//  로그 수신 (수정 ①: 로그 텍스트에서 무게 파싱 추가)
// ═══════════════════════════════════════════════════════════
void MainWindow::onLogLine(const QString &rawLine)
{
    // ── ANSI 이스케이프 코드 및 깨지는 제어문자 제거 ─────
    // 1) \e[...m  형태의 ANSI 컬러/스타일 코드
    static QRegularExpression reAnsi(R"(\x1B[\[\(][0-9;]*[A-Za-z])");
    // 2) 단독 ESC 바이트 잔재
    static QRegularExpression reEsc(R"(\x1B)");
    // 3) 출력 불가 제어문자 (탭/개행 제외)
    static QRegularExpression reCtrl(R"([\x00-\x08\x0B\x0C\x0E-\x1F\x7F])");

    QString line = rawLine;
    line.replace(reAnsi, "");
    line.replace(reEsc,  "");
    line.replace(reCtrl, "");
    line = line.trimmed();

    // ── 로그에서 무게 파싱 ──────────────────────────────
    // STM32 cliPrintf 형식 예:
    //   "weight: 50.4"  /  "Weight=50.40g"  /  "loadcell: 50.4 g"
    // 아래 정규식은 대부분의 형식을 커버합니다.
    static QRegularExpression reWeight(
        R"(weight=(-?[0-9]+\.?[0-9]*))",
        QRegularExpression::CaseInsensitiveOption);

    QRegularExpressionMatch m = reWeight.match(line);
    if (m.hasMatch() && !line.contains("[SETTINGS]")) {
        float w = m.captured(1).toFloat();
        if (w >= 0.0f && w < 5000.0f)
            updateWeightDisplay(w);
    }

    // ── PIR 상태 파싱 ─────────────────────────────────────
    // pir.c output strings (English):
    //   pirCheck  → "[PIR] Motion detected! Emergency stop"
    //   pirCheck  → "[PIR] Detecting... Xs"
    //   pirCheck  → "[PIR] Cleared (total Xs) -- run 'system on' to restart"
    //   pir on    → "[PIR] Enabled"
    //   pir off   → "[PIR] Disabled"
    //   pir read  → "[PIR] State: Detected"  or  "None"
    //   pir status→ "[PIR] enabled=ON  detecting=Detecting"  or  "None"
    if (line.contains("[PIR]")) {
        if (line.contains("Motion detected!") || line.contains("Detecting...")) {
            if (!m_pirDetecting) {
                m_pirElapsedSec = 0;
                m_pirTimer->start();
            }
            updatePirStatus(true, true);

        } else if (line.contains("Cleared")) {
            m_pirTimer->stop();
            updatePirStatus(true, false);

        } else if (line.contains("Enabled")) {
            updatePirStatus(true, false);

        } else if (line.contains("Disabled")) {
            m_pirTimer->stop();
            updatePirStatus(false, false);

        } else if (line.contains("State:")) {
            bool detected = line.contains("Detected");
            if (detected && !m_pirDetecting) {
                m_pirElapsedSec = 0;
                m_pirTimer->start();
            } else if (!detected) {
                m_pirTimer->stop();
            }
            updatePirStatus(m_pirEnabled, detected);

        } else if (line.contains("enabled=")) {
            bool en  = line.contains("enabled=ON");
            bool det = line.contains("detecting=Detecting");
            if (det && !m_pirDetecting) {
                m_pirElapsedSec = 0;
                m_pirTimer->start();
            } else if (!det) {
                m_pirTimer->stop();
            }
            updatePirStatus(en, det);
        }
    }

    // system on → PIR auto-enable (ap.c calls pirEnable(true))
    if (line.contains("[SYS]") && line.contains("PIR")) {
        updatePirStatus(true, false);
    }

    // ── 시스템 상태 파악 ────────────────────────────────
    if      (line.contains("WAIT_OBJECT"))      updateStateLabel("WAIT_OBJECT");
    else if (line.contains("MEASURING"))        updateStateLabel("MEASURING");
    else if (line.contains("ARM_MOVING"))       updateStateLabel("ARM_MOVING");
    else if (line.contains("CONVEYOR_RUNNING")) updateStateLabel("CONVEYOR_RUNNING");
    else if (line.contains("DONE"))             updateStateLabel("DONE");
    else if (line.contains("IDLE"))             updateStateLabel("IDLE");

    // ── 분류 카운트 ─────────────────────────────────────
    if (line.contains("Heavy object") || line.contains("FLAG LEFT")) {
        m_heavyCount++;
        m_lblHeavyCount->setText(QString::number(m_heavyCount));
        m_pbHeavy->setValue(qMin(m_heavyCount, 20));
    } else if (line.contains("Light object") || line.contains("FLAG RIGHT")) {
        m_lightCount++;
        m_lblLightCount->setText(QString::number(m_lightCount));
        m_pbLight->setValue(qMin(m_lightCount, 20));
    }

    // ── 타임스탬프 붙여서 로그에 추가 ──────────────────
    QString ts = QDateTime::currentDateTime().toString("hh:mm:ss.zzz");
    m_logEdit->append(QString("[%1] %2").arg(ts, line));

    QScrollBar *sb = m_logEdit->verticalScrollBar();
    sb->setValue(sb->maximum());
}

void MainWindow::updateStateLabel(const QString &state)
{
    m_currentState = state;
    auto setActive = [](QLabel *l, bool active) {
        l->setObjectName(active ? "stateBoxActive" : "stateBox");
        l->style()->unpolish(l);
        l->style()->polish(l);
    };
    setActive(m_lblState1, state == "WAIT_OBJECT" || state == "MEASURING");
    setActive(m_lblState2, state == "ARM_MOVING");
    setActive(m_lblState3, state == "CONVEYOR_RUNNING");
    setActive(m_lblState4, state == "DONE");
}

void MainWindow::setConnectedState(bool connected)
{
    m_isConnected = connected;
    m_btnConnect->setText(connected ? "DISCONNECT" : "CONNECT");
    m_btnConnect->setObjectName(connected ? "btnRed" : "btnBlue");
    m_btnConnect->style()->unpolish(m_btnConnect);
    m_btnConnect->style()->polish(m_btnConnect);
    m_lblConnStatus->setObjectName(connected ? "lblConnected" : "lblDisconnected");
    m_lblConnStatus->style()->unpolish(m_lblConnStatus);
    m_lblConnStatus->style()->polish(m_lblConnStatus);
}

void MainWindow::onConnected(const QString &portName)
{
    setConnectedState(true);
    m_lblConnStatus->setText(QString("● CONNECTED\n%1, 9600 bps").arg(portName));
    onLogLine(QString("[SYSTEM] Connected to %1").arg(portName));
}

void MainWindow::onDisconnected()
{
    setConnectedState(false);
    m_lblConnStatus->setText("● DISCONNECTED");
    onLogLine("[SYSTEM] Disconnected");
}

void MainWindow::onSerialError(const QString &msg)
{
    onLogLine(QString("[ERROR] %1").arg(msg));
}

void MainWindow::onBtnConnect()
{
    if (m_isConnected) {
        m_serial->disconnectPort();
    } else {
        QString port = m_cbPort->currentText();
        if (port.isEmpty()) { onLogLine("[ERROR] No port selected"); return; }
        m_serial->connectPort(port, 9600);
    }
}

void MainWindow::onBtnSystemOn()
{
    if (!m_isConnected) { onLogLine("[WARN] Not connected"); return; }
    m_serial->sendCommand("system on");
    onLogLine("[CMD] system on");
}

void MainWindow::onBtnSystemOff()
{
    if (!m_isConnected) { onLogLine("[WARN] Not connected"); return; }
    m_serial->sendCommand("system off");
    onLogLine("[CMD] system off");
    updateStateLabel("IDLE");
}

// 수정 ④: SYSTEM RESET → HEAVY/LIGHT 카운터 초기화
void MainWindow::onBtnSystemReset()
{
    if (!m_isConnected) { onLogLine("[WARN] Not connected"); return; }
    m_serial->sendCommand("sys reset");
    onLogLine("[CMD] sys reset");

    // 카운터 초기화
    m_heavyCount = 0;
    m_lightCount = 0;
    m_lblHeavyCount->setText("0");
    m_lblLightCount->setText("0");
    m_pbHeavy->setValue(0);
    m_pbLight->setValue(0);

    // 무게/정렬 결과도 초기화
    m_lblWeight->setText("--- g");
    m_lblSortResult->setText("---");
    m_lblSortResult->setStyleSheet("font-size:32px;font-weight:bold;color:#8b949e;");

    onLogLine("[SYSTEM] Counters and weight display reset");
}

void MainWindow::onBtnTare()
{
    if (!m_isConnected) { onLogLine("[WARN] Not connected"); return; }
    m_serial->sendCommand("loadcell tare");
    onLogLine("[CMD] loadcell tare");
}

void MainWindow::onBtnSendCli()
{
    QString cmd = m_cliInput->text().trimmed();
    if (cmd.isEmpty()) return;
    if (!m_isConnected) { onLogLine("[WARN] Not connected"); return; }
    m_serial->sendCommand(cmd);
    onLogLine(QString("[CMD] %1").arg(cmd));
    m_cliInput->clear();
}

void MainWindow::onBtnSaveSettings()
{
    bool ok;
    float ref = m_edRefWeight->text().toFloat(&ok);
    if (!ok || ref <= 0) { onLogLine("[WARN] Invalid reference weight"); return; }
    m_refWeight = ref;
    m_lblRefWeight->setText(QString("■  REF: %1 g").arg(ref, 0, 'f', 0));
    onLogLine(QString("[SETTINGS] Reference weight set to %1 g").arg(ref));
}

void MainWindow::refreshPorts()
{
    QString current = m_cbPort->currentText();
    m_cbPort->clear();
    for (const QString &p : SerialWorker::availablePorts())
        m_cbPort->addItem(p);
    int idx = m_cbPort->findText(current);
    if (idx >= 0) m_cbPort->setCurrentIndex(idx);
}

// ═══════════════════════════════════════════════════════════
//  PIR 슬롯
// ═══════════════════════════════════════════════════════════
void MainWindow::onPirTimerTick()
{
    m_pirElapsedSec++;
    // 감지 중이면 경과 시간 표시 갱신
    if (m_pirDetecting) {
        m_lblPirStatus->setText(
            QString("⚠ DETECTED  %1s").arg(m_pirElapsedSec));
    }
}

void MainWindow::updatePirStatus(bool enabled, bool detecting)
{
    m_pirEnabled   = enabled;
    m_pirDetecting = detecting;

    // ── 감지 상태 표시 ────────────────────────────────
    if (detecting) {
        m_lblPirStatus->setText(
            QString("⚠ DETECTED  %1s").arg(m_pirElapsedSec));
        m_lblPirStatus->setObjectName("pirDetecting");
        if (!m_pirTimer->isActive()) {
            m_pirElapsedSec = 0;
            m_pirTimer->start();
        }
    } else {
        m_pirElapsedSec = 0;
        m_pirTimer->stop();
        if (enabled) {
            m_lblPirStatus->setText("● ACTIVE");
            m_lblPirStatus->setObjectName("pirActive");
        } else {
            m_lblPirStatus->setText("● INACTIVE");
            m_lblPirStatus->setObjectName("pirInactive");
        }
    }
    m_lblPirStatus->style()->unpolish(m_lblPirStatus);
    m_lblPirStatus->style()->polish(m_lblPirStatus);
}