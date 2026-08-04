/*
  스마트 도서관 - 무인 반납기 (아두이노)
  http://www.kccistc.net/
  작성일 : 2026.05.29
  작성자 : AIoT 임베디드
*/

#define DEBUG

#define AP_SSID      "KCCI601"
#define AP_PASS      "@kcci601@"
#define SERVER_NAME  "10.10.16.73"
#define SERVER_PORT  5000
#define LOGID        "ARD_01"
#define PASSWD       "PASSWD"

#define WIFIRX       6
#define WIFITX       7
#define RFID_SS_PIN  10
#define RFID_RST_PIN 9
#define SERVO_PIN    5
#define BTN_PIN         3   // 문 닫힘 버튼
#define MISSION_BTN_PIN 2   // 미션 버튼
#define BUZZER_PIN      8

#define CMD_SIZE 60
#define ARR_CNT  6

#define DOOR_OPEN_ANGLE   90
#define DOOR_CLOSE_ANGLE  0
#define SERVO_SETTLE_MS   500
#define DOOR_OPENING_MS   800
#define DOOR_TIMEOUT_MS   10000

#define MISSION_TIME_MS   20000   // 미션 제한 시간 20초
#define MISSION_BTN_COUNT 60      // 버튼 60번

#include "WiFiEsp.h"
#include "SoftwareSerial.h"
#include <SPI.h>
#include <MFRC522.h>
#include <Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

SoftwareSerial wifiSerial(WIFIRX, WIFITX);
WiFiEspClient client;
MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);
Servo doorServo;
LiquidCrystal_I2C lcd(0x27, 16, 2);

char sendBuf[CMD_SIZE];
char currentBookId[20] = {0};
char currentUserId[20] = {0};  // 연체 미션용 user_id

unsigned long lastSec = 0;
unsigned long secCount = 0;
unsigned long stateTimer = 0;
unsigned long servoCloseTimer = 0;
unsigned long servoOpenTimer = 0;
bool servoClosing = false;
bool servoOpening = false;

// 미션 관련
int missionBtnCount = 0;
bool btnPressed = false;
int overduedays = 0;

typedef enum {
  CMD_NONE,
  CMD_DOOR_OPEN,
  CMD_DOOR_OPEN_OVERDUE,  // 연체 반납 → 미션 필요
  CMD_FAIL_RETURNED,
  CMD_FAIL_NOTFOUND,
  CMD_FAIL
} PendingCmd;

PendingCmd pendingCmd = CMD_NONE;

typedef enum {
  STATE_IDLE,
  STATE_WAIT_RESP,
  STATE_DOOR_OPENING,
  STATE_DOOR_OPEN,
  STATE_BOOK_IN,
  STATE_BOOK_IN_WAIT,
  STATE_OVERDUE_WAIT,  // 연체 안내 후 미션 대기
  STATE_MISSION,       // 미션 진행 중
  STATE_MISSION_WAIT,  // 미션 결과 표시
} ReturnState;

ReturnState state = STATE_IDLE;
unsigned long doorOpenTime = 0;

void setup() {
  pinMode(BTN_PIN, INPUT_PULLUP);
  pinMode(MISSION_BTN_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);
  Serial.begin(115200);

  lcd.init();
  lcd.backlight();
  lcdPrint("Smart Library", "Initializing..");

  doorServo.attach(SERVO_PIN);
  doorServo.write(DOOR_CLOSE_ANGLE);
  delay(500);
  doorServo.detach();

  wifi_Setup();

  SPI.begin();
  rfid.PCD_Init();

  lcdPrint("SCAN BOOK RFID", "");
  Serial.println("준비 완료");
}

void loop() {
  while (client.available())
    recvMsg();

  if (servoClosing && millis() - servoCloseTimer >= SERVO_SETTLE_MS) {
    doorServo.detach();
    servoClosing = false;
  }

  if (servoOpening && millis() - servoOpenTimer >= DOOR_OPENING_MS) {
    doorServo.detach();
    servoOpening = false;
  }

  if (millis() - lastSec >= 1000) {
    lastSec = millis();
    secCount++;
    if (!(secCount % 5)) {
      if (!client.connected())
        server_Connect();
    }
  }

  switch (state) {

    case STATE_IDLE:
      if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
        rfidToString(rfid.uid.uidByte, rfid.uid.size, currentBookId);
        rfid.PICC_HaltA();
#ifdef DEBUG
        Serial.print("RFID 인식: ");
        Serial.println(currentBookId);
#endif
        lcdPrint("Scanning...", currentBookId);
        beepNonBlock(100);

        sprintf(sendBuf, "[SQL]RETURN@%s\n", currentBookId);
        client.write(sendBuf, strlen(sendBuf));

        pendingCmd = CMD_NONE;
        stateTimer = millis();
        state = STATE_WAIT_RESP;
      }
      break;

    case STATE_WAIT_RESP:
      if (pendingCmd == CMD_DOOR_OPEN) {
        pendingCmd = CMD_NONE;
        doorOpen();
        sprintf(sendBuf, "[SQL]STATUS@DOOR@OPEN\n");
        client.write(sendBuf, strlen(sendBuf));
        stateTimer = millis();
        state = STATE_DOOR_OPENING;
      } else if (pendingCmd == CMD_DOOR_OPEN_OVERDUE) {
        pendingCmd = CMD_NONE;
        doorOpen();
        sprintf(sendBuf, "[SQL]STATUS@DOOR@OPEN\n");
        client.write(sendBuf, strlen(sendBuf));
        stateTimer = millis();
        state = STATE_DOOR_OPENING;
        // 문 열린 후 미션 상태로 전환 (DOOR_OPEN에서 BOOK_IN 후 MISSION으로)
      } else if (pendingCmd == CMD_FAIL_RETURNED) {
        pendingCmd = CMD_NONE;
        lcdPrint("Already returned", "");
        beepNonBlock(300);
        memset(currentBookId, 0, sizeof(currentBookId));
        stateTimer = millis();
        state = STATE_BOOK_IN_WAIT;
      } else if (pendingCmd == CMD_FAIL_NOTFOUND) {
        pendingCmd = CMD_NONE;
        lcdPrint("Not registered!", "");
        beepNonBlock(300);
        memset(currentBookId, 0, sizeof(currentBookId));
        stateTimer = millis();
        state = STATE_BOOK_IN_WAIT;
      } else if (pendingCmd == CMD_FAIL) {
        pendingCmd = CMD_NONE;
        lcdPrint("Return FAIL", "");
        beepNonBlock(300);
        memset(currentBookId, 0, sizeof(currentBookId));
        stateTimer = millis();
        state = STATE_BOOK_IN_WAIT;
      }
      if (millis() - stateTimer >= 5000) {
        pendingCmd = CMD_NONE;
        memset(currentBookId, 0, sizeof(currentBookId));
        lcdPrint("SCAN BOOK RFID", "");
        state = STATE_IDLE;
      }
      break;

    case STATE_DOOR_OPENING:
      if (millis() - stateTimer >= DOOR_OPENING_MS) {
        doorOpenTime = millis();
        lcdPrint("Insert book &", "press button");
        state = STATE_DOOR_OPEN;
      }
      break;

    case STATE_DOOR_OPEN:
      if (digitalRead(BTN_PIN) == LOW) {
        state = STATE_BOOK_IN;
      } else if (millis() - doorOpenTime > DOOR_TIMEOUT_MS) {
        Serial.println("자동 닫힘");
        state = STATE_BOOK_IN;
      }
      break;

    case STATE_BOOK_IN:
      if (overduedays > 0) {
        // 연체 시 문 안 닫음
        missionBtnCount = 0;
        btnPressed = false;
        char overdueStr[8];
        sprintf(overdueStr, "%d days", overduedays);
        lcdPrint("OVERDUE!", overdueStr);
        beepNonBlock(500);
        stateTimer = millis();
        state = STATE_OVERDUE_WAIT;
      } else {
        // 일반 반납 시 문 닫음
        doorClose();
        sprintf(sendBuf, "[SQL]STATUS@DOOR@CLOSE\n");
        client.write(sendBuf, strlen(sendBuf));
        lcdPrint("Return OK!", currentBookId);
        beepNonBlock(100);
        stateTimer = millis();
        state = STATE_BOOK_IN_WAIT;
      }
      break;

    case STATE_OVERDUE_WAIT:
      if (millis() - stateTimer >= 1000) {
        lcdPrint("Press 60 times", "in 20 seconds!");
        stateTimer = millis();
        state = STATE_MISSION;
      }
      break;

    case STATE_MISSION: {
      unsigned long elapsed = millis() - stateTimer;
      unsigned long remaining = (MISSION_TIME_MS - elapsed) / 1000;

      // 버튼 카운트 (디바운싱)
      if (digitalRead(MISSION_BTN_PIN) == LOW && !btnPressed) {
        btnPressed = true;
        missionBtnCount++;
        beepNonBlock(30);
        char buf1[16], buf2[16];
        sprintf(buf1, "%d/60", missionBtnCount);
        sprintf(buf2, "%lus left", remaining);
        lcdPrint(buf1, buf2);
#ifdef DEBUG
        Serial.print("버튼: ");
        Serial.println(missionBtnCount);
#endif
      }
      if (digitalRead(MISSION_BTN_PIN) == HIGH) {
        btnPressed = false;
      }

      // 미션 성공
      if (missionBtnCount >= MISSION_BTN_COUNT) {
        sprintf(sendBuf, "[SQL]SETDB@OVERDUE@CLEAR@%s@%s\n", currentUserId, currentBookId);
        client.write(sendBuf, strlen(sendBuf));
        doorClose();
        sprintf(sendBuf, "[SQL]STATUS@DOOR@CLOSE\n");
        client.write(sendBuf, strlen(sendBuf));
        sprintf(sendBuf, "[SQL]STATUS@DOOR@CLOSE\n");
        client.write(sendBuf, strlen(sendBuf));
        lcdPrint("Mission Clear!", "Overdue removed");
        beepNonBlock(200);
        overduedays = 0;
        stateTimer = millis();
        state = STATE_MISSION_WAIT;
#ifdef DEBUG
        Serial.println("미션 성공!");
#endif
      }
      // 타임아웃 → 재시도
      else if (elapsed >= MISSION_TIME_MS) {
        lcdPrint("Mission FAIL!", "Try again!");
        beepNonBlock(500);
#ifdef DEBUG
        Serial.println("미션 실패 - 재시도");
#endif
        missionBtnCount = 0;
        btnPressed = false;
        stateTimer = millis();
        // 1초 후 다시 미션 시작
        state = STATE_OVERDUE_WAIT;
      }
      break;
    }

    case STATE_MISSION_WAIT:
      if (millis() - stateTimer >= 2000) {
        memset(currentBookId, 0, sizeof(currentBookId));
        memset(currentUserId, 0, sizeof(currentUserId));
        lcdPrint("SCAN BOOK RFID", "");
        state = STATE_IDLE;
      }
      break;

    case STATE_BOOK_IN_WAIT:
      if (millis() - stateTimer >= 2000) {
        memset(currentBookId, 0, sizeof(currentBookId));
        memset(currentUserId, 0, sizeof(currentUserId));
        lcdPrint("SCAN BOOK RFID", "");
        state = STATE_IDLE;
      }
      break;
  }
}

void recvMsg() {
  char recvBuf[CMD_SIZE] = {0};
  int idx = 0;
  unsigned long timeout = millis();

  while (millis() - timeout < 200) {
    if (client.available()) {
      char c = client.read();
      if (c == '\n') break;
      if (idx < CMD_SIZE - 1)
        recvBuf[idx++] = c;
      timeout = millis();
    }
  }

  recvBuf[idx] = '\0';
  if (idx == 0) return;

#ifdef DEBUG
  Serial.print("recv : ");
  Serial.println(recvBuf);
#endif

  char parseBuf[CMD_SIZE] = {0};
  strncpy(parseBuf, recvBuf, CMD_SIZE - 1);

  char* pArray[ARR_CNT] = {0};
  char* pToken = strtok(parseBuf, "[@]");
  int i = 0;

  while (pToken != NULL) {
    pArray[i] = pToken;
    if (++i >= ARR_CNT) break;
    pToken = strtok(NULL, "[@]");
  }

  if (i < 2) return;

  if (!strncmp(pArray[1], " Alr", 4)) {
    client.stop();
    delay(300);
    server_Connect();
    return;
  }
  if (!strncmp(pArray[1], " New", 4)) return;

  if (!strcmp(pArray[1], "RETURN")) {
    if (!strcmp(pArray[2], "OK")) {
      if (i >= 4 && !strcmp(pArray[3], "OVERDUE")) {
        // 연체 반납
        overduedays = atoi(pArray[4]);
        if (i >= 6) strncpy(currentUserId, pArray[5], sizeof(currentUserId) - 1);
        pendingCmd = CMD_DOOR_OPEN_OVERDUE;
      } else {
        overduedays = 0;
        pendingCmd = CMD_DOOR_OPEN;
      }
    } else if (!strcmp(pArray[2], "FAIL")) {
      if (i >= 4 && !strcmp(pArray[3], "RETURNED"))
        pendingCmd = CMD_FAIL_RETURNED;
      else if (i >= 4 && !strcmp(pArray[3], "NOTFOUND"))
        pendingCmd = CMD_FAIL_NOTFOUND;
      else
        pendingCmd = CMD_FAIL;
    }
  }
}

void lcdPrint(const char* line1, const char* line2) {
  lcd.setCursor(0, 0);
  lcd.print("                ");
  lcd.setCursor(0, 1);
  lcd.print("                ");
  lcd.setCursor(0, 0);
  lcd.print(line1);
  lcd.setCursor(0, 1);
  lcd.print(line2);
}

void beepNonBlock(int ms) {
  tone(BUZZER_PIN, 1000, ms);
}

void doorOpen() {
  if (!doorServo.attached())
    doorServo.attach(SERVO_PIN);
  doorServo.write(DOOR_OPEN_ANGLE);
  servoOpenTimer = millis();
  servoOpening = true;
  servoClosing = false;
#ifdef DEBUG
  Serial.println("문 열림");
#endif
}

void doorClose() {
  if (!doorServo.attached())
    doorServo.attach(SERVO_PIN);
  doorServo.write(DOOR_CLOSE_ANGLE);
  servoCloseTimer = millis();
  servoClosing = true;
  servoOpening = false;
#ifdef DEBUG
  Serial.println("문 닫힘");
#endif
}

void rfidToString(byte* buf, byte bufSize, char* output) {
  output[0] = '\0';
  char tmp[4];
  for (byte i = 0; i < bufSize; i++) {
    sprintf(tmp, "%02X", buf[i]);
    strcat(output, tmp);
  }
}

void wifi_Setup() {
  wifiSerial.begin(38400);
  wifi_Init();
  server_Connect();
}

void wifi_Init() {
  do {
    WiFi.init(&wifiSerial);
    if (WiFi.status() == WL_NO_SHIELD) {
    } else
      break;
  } while (1);

  while (WiFi.begin(AP_SSID, AP_PASS) != WL_CONNECTED) {}

  Serial.println("WiFi 연결됨");
}

void server_Connect() {
  if (client.connect(SERVER_NAME, SERVER_PORT)) {
    client.print("[" LOGID ":" PASSWD "]");
    Serial.println("서버 연결됨");
  }
}