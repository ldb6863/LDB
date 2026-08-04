#ifndef __RC522_H_
#define __RC522_H_

#include "main.h"
#include <string.h>
#include <stdio.h>

// RC522 레지스터 정의
#define CommandReg          0x01
#define ComIEnReg           0x02
#define DivIEnReg           0x03
#define ComIrqReg           0x04
#define DivIrqReg           0x05
#define ErrorReg            0x06
#define Status1Reg          0x07
#define Status2Reg          0x08
#define FIFODataReg         0x09
#define FIFOLevelReg        0x0A
#define WaterLevelReg       0x0B
#define ControlReg          0x0C
#define BitFramingReg       0x0D
#define CollReg             0x0E
#define ModeReg             0x11
#define TxModeReg           0x12
#define RxModeReg           0x13
#define TxControlReg        0x14
#define TxASKReg            0x15
#define CRCResultRegH       0x21
#define CRCResultRegL       0x22
#define ModWidthReg         0x24
#define TModeReg            0x2A
#define TPrescalerReg       0x2B
#define TReloadRegH         0x2C
#define TReloadRegL         0x2D
#define TCounterValRegH     0x2E
#define TCounterValRegL     0x2F
#define TestSel1Reg         0x31
#define TestSel2Reg         0x32
#define TestPinEnReg        0x33
#define TestPinValueReg     0x34
#define TestBusReg          0x35
#define AutoTestReg         0x36
#define VersionReg          0x37

// RC522 명령어
#define PCD_Idle            0x00
#define PCD_Mem             0x01
#define PCD_GenerateRandomID 0x02
#define PCD_CalcCRC         0x03
#define PCD_Transmit        0x04
#define PCD_NoCmdChange     0x07
#define PCD_Receive         0x08
#define PCD_Transceive      0x0C
#define PCD_MFAuthent       0x0E
#define PCD_SoftReset       0x0F

// PICC 명령어
#define PICC_CMD_REQA       0x26
#define PICC_CMD_WUPA       0x52
#define PICC_CMD_CT         0x88
#define PICC_CMD_SEL_CL1    0x93
#define PICC_CMD_SEL_CL2    0x95
#define PICC_CMD_SEL_CL3    0x97
#define PICC_CMD_HLTA       0x50
#define PICC_CMD_MF_AUTH_KEY_A 0x60
#define PICC_CMD_MF_AUTH_KEY_B 0x61
#define PICC_CMD_MF_READ    0x30
#define PICC_CMD_MF_WRITE   0xA0

// 상태 코드
#define STATUS_OK           0
#define STATUS_ERROR        1
#define STATUS_COLLISION    2
#define STATUS_TIMEOUT      3
#define STATUS_NO_ROOM      4
#define STATUS_INTERNAL_ERROR 5
#define STATUS_INVALID      6
#define STATUS_CRC_WRONG    7

// SPI 핀 (Nucleo F411RE 기준)
// SDA(CS) → PB6 (D10)
// RST     → PA9 (D8)
#define RC522_CS_PORT       GPIOB
#define RC522_CS_PIN        GPIO_PIN_6
#define RC522_RST_PORT      GPIOA
#define RC522_RST_PIN       GPIO_PIN_9

extern SPI_HandleTypeDef hspi1;

// UID 구조체
typedef struct {
  uint8_t size;
  uint8_t uidByte[10];
  uint8_t sak;
} Uid;

// 함수 선언
void     RC522_Init(void);
uint8_t  RC522_IsNewCardPresent(void);
uint8_t  RC522_ReadCardSerial(Uid *uid);
void     RC522_HaltA(void);
void     RC522_UidToString(Uid *uid, char *output);

#endif
