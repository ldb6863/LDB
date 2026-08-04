//#include "ap.h"

//

//extern I2C_HandleTypeDef hi2c3;

//

//void apInit(void)

//{

//  LCD_init(&hi2c3);

//  printf("LCD init OK\r\n");

//

//  LCD_writeCmdData(0x01);  // clear

//  HAL_Delay(5);

//  LCD_writeStringXY(0, 0, "Smart Library");

//  LCD_writeStringXY(1, 0, "Hello!");

//  printf("LCD print OK\r\n");

//}

//

//void apMain(void)

//{

//  // 1단계: LCD 확인만

//}



#if 1

#include "ap.h"



extern I2C_HandleTypeDef hi2c3;



static Uid uid;

static char currentUserId[20] = {0};

static char currentBookId[20] = {0};

static char sendBuf[CMD_SIZE];



static uint32_t stateTimer = 0;



// 상태 머신

typedef enum {

  STATE_SCAN_MEMBER,

  STATE_MEMBER_FOUND,

  STATE_SCAN_BOOK,

  STATE_WAIT_RESP,

  STATE_RESULT_WAIT,

} KioskState;



static KioskState state = STATE_SCAN_MEMBER;



// 펜딩 커맨드

typedef enum {

  CMD_NONE,

  CMD_LOAN_OK,

  CMD_LOAN_FAIL_OVERDUE,

  CMD_LOAN_FAIL_NOTFOUND,

  CMD_LOAN_FAIL_ALREADYOUT,

  CMD_LOAN_FAIL

} PendingCmd;



static PendingCmd pendingCmd = CMD_NONE;



void apInit(void)

{

  LCD_init(&hi2c3);

  RC522_Init();



  // I2C 스캔

  for (uint8_t addr = 1; addr < 128; addr++)

  {

    if (HAL_I2C_IsDeviceReady(&hi2c3, addr << 1, 1, 10) == HAL_OK)

      printf("I2C device found: 0x%02X\r\n", addr);

  }



  apLcdPrint("Smart Library", "Initializing..");

  HAL_Delay(500);

  apLcdPrint("SCAN MEMBER", "CARD");

  printf("apInit OK\r\n");

}



void apMain(void)

{

  if (btFlag)

  {

    char localMsg[CMD_SIZE] = {0};

    __disable_irq();

    strncpy(localMsg, (const char*)btData, CMD_SIZE - 1);

    btFlag = 0;

    memset((void*)btData, 0, CMD_SIZE);

    __enable_irq();

    printf("recv : %s\r\n", localMsg);

    apParseServer(localMsg);

  }



  switch (state)

  {

    case STATE_SCAN_MEMBER:

      if (RC522_IsNewCardPresent() && RC522_ReadCardSerial(&uid))

      {

        RC522_UidToString(&uid, currentUserId);

        RC522_HaltA();

        printf("회원증 인식: %s\r\n", currentUserId);

        apLcdPrint("Member found:", currentUserId);



        //부저 추가

        HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_SET);

                HAL_GPIO_WritePin(LED_GREEN_GPIO_Port, LED_GREEN_Pin, GPIO_PIN_SET); // LED 켜기

                HAL_Delay(80);

                HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_RESET);

                HAL_GPIO_WritePin(LED_GREEN_GPIO_Port, LED_GREEN_Pin, GPIO_PIN_RESET); // LED 끄기

                HAL_Delay(50);

                HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_SET);

                HAL_GPIO_WritePin(LED_GREEN_GPIO_Port, LED_GREEN_Pin, GPIO_PIN_SET); // LED 켜기

                HAL_Delay(80);

                HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_RESET);

                HAL_GPIO_WritePin(LED_GREEN_GPIO_Port, LED_GREEN_Pin, GPIO_PIN_RESET);



        stateTimer = HAL_GetTick();

        state = STATE_MEMBER_FOUND;

      }

      break;



    case STATE_MEMBER_FOUND:

      if (HAL_GetTick() - stateTimer >= 1000)

      {

        apLcdPrint("SCAN BOOK", "RFID");

        state = STATE_SCAN_BOOK;

      }

      break;



    case STATE_SCAN_BOOK:

      if (RC522_IsNewCardPresent() && RC522_ReadCardSerial(&uid))

      {

        RC522_UidToString(&uid, currentBookId);

        RC522_HaltA();

        printf("도서 인식: %s\r\n", currentBookId);

        apLcdPrint("Scanning...", currentBookId);



        //부저 추가

        HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_SET);

                HAL_GPIO_WritePin(LED_GREEN_GPIO_Port, LED_GREEN_Pin, GPIO_PIN_SET); // LED 켜기

                HAL_Delay(80);

                HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_RESET);

                HAL_GPIO_WritePin(LED_GREEN_GPIO_Port, LED_GREEN_Pin, GPIO_PIN_RESET); // LED 끄기

                HAL_Delay(50);

                HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_SET);

                HAL_GPIO_WritePin(LED_GREEN_GPIO_Port, LED_GREEN_Pin, GPIO_PIN_SET); // LED 켜기

                HAL_Delay(80);

                HAL_GPIO_WritePin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_PIN_RESET);

                HAL_GPIO_WritePin(LED_GREEN_GPIO_Port, LED_GREEN_Pin, GPIO_PIN_RESET);



        sprintf(sendBuf, "[SQL]SETDB@LOAN@%s@%s\n", currentUserId, currentBookId);

        btSend(sendBuf);



        pendingCmd = CMD_NONE;

        stateTimer = HAL_GetTick();

        state = STATE_WAIT_RESP;

      }

      break;



    case STATE_WAIT_RESP:

      if (pendingCmd == CMD_LOAN_OK)

      {

        pendingCmd = CMD_NONE;

        apLcdPrint("Loan OK!", currentBookId);

        stateTimer = HAL_GetTick();

        state = STATE_RESULT_WAIT;

      }

      else if (pendingCmd == CMD_LOAN_FAIL_OVERDUE)

      {

        pendingCmd = CMD_NONE;

        apLcdPrint("FAIL: Overdue!", "");

        stateTimer = HAL_GetTick();

        state = STATE_RESULT_WAIT;

      }

      else if (pendingCmd == CMD_LOAN_FAIL_NOTFOUND)

      {

        pendingCmd = CMD_NONE;

        apLcdPrint("FAIL: Not found", "");

        stateTimer = HAL_GetTick();

        state = STATE_RESULT_WAIT;

      }

      else if (pendingCmd == CMD_LOAN_FAIL_ALREADYOUT)

      {

        pendingCmd = CMD_NONE;

        apLcdPrint("FAIL: Already", "loaned");

        stateTimer = HAL_GetTick();

        state = STATE_RESULT_WAIT;

      }

      else if (pendingCmd == CMD_LOAN_FAIL)

      {

        pendingCmd = CMD_NONE;

        apLcdPrint("FAIL: Error", "");

        stateTimer = HAL_GetTick();

        state = STATE_RESULT_WAIT;

      }

      // 5초 타임아웃

      else if (HAL_GetTick() - stateTimer >= 5000)

      {

        printf("응답 타임아웃\r\n");

        apLcdPrint("Timeout!", "Try again");

        pendingCmd = CMD_NONE;

        stateTimer = HAL_GetTick();

        state = STATE_RESULT_WAIT;

      }

      break;



    case STATE_RESULT_WAIT:

      if (HAL_GetTick() - stateTimer >= 2000)

      {

        memset(currentUserId, 0, sizeof(currentUserId));

        memset(currentBookId, 0, sizeof(currentBookId));

        apLcdPrint("SCAN MEMBER", "CARD");

        state = STATE_SCAN_MEMBER;

      }

      break;

  }

}



void apParseServer(char* msg)

{

  int i = 0;

  char* pToken;

  char* pArray[ARR_CNT] = {0};

  char recvBuf[CMD_SIZE] = {0};



  if (msg == NULL || strlen(msg) == 0) return;

  strncpy(recvBuf, msg, CMD_SIZE - 1);



  pToken = strtok(recvBuf, "[@]");

  while (pToken != NULL)

  {

    pArray[i] = pToken;

    if (++i >= ARR_CNT) break;

    pToken = strtok(NULL, "[@]");

  }



  if (i < 2) return;



  if (!strncmp(pArray[1], " New", 4) || !strncmp(pArray[1], " Alr", 4))

    return;



  if (!strcmp(pArray[1], "LOAN"))

  {

    if (!strcmp(pArray[2], "OK"))

      pendingCmd = CMD_LOAN_OK;

    else if (!strcmp(pArray[2], "FAIL"))

    {

      if (i >= 4 && !strcmp(pArray[3], "OVERDUE"))

        pendingCmd = CMD_LOAN_FAIL_OVERDUE;

      else if (i >= 4 && !strcmp(pArray[3], "NOTFOUND"))

        pendingCmd = CMD_LOAN_FAIL_NOTFOUND;

      else if (i >= 4 && !strcmp(pArray[3], "ALREADYOUT"))

        pendingCmd = CMD_LOAN_FAIL_ALREADYOUT;

      else

        pendingCmd = CMD_LOAN_FAIL;

    }

  }

}



void apLcdPrint(const char* line1, const char* line2)

{

  LCD_writeCmdData(0x01);

  HAL_Delay(5);

  LCD_writeStringXY(0, 0, (char*)line1);

  LCD_writeStringXY(1, 0, (char*)line2);

}

#endif
