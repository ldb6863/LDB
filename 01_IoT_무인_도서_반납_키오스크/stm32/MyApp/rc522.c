#include "rc522.h"

// SPI 핀 제어
static void CS_Low(void)  { HAL_GPIO_WritePin(RC522_CS_PORT, RC522_CS_PIN, GPIO_PIN_RESET); }
static void CS_High(void) { HAL_GPIO_WritePin(RC522_CS_PORT, RC522_CS_PIN, GPIO_PIN_SET); }
static void RST_High(void){ HAL_GPIO_WritePin(RC522_RST_PORT, RC522_RST_PIN, GPIO_PIN_SET); }

// 레지스터 쓰기
static void PCD_WriteRegister(uint8_t reg, uint8_t value)
{
  uint8_t txData[2] = { (reg << 1) & 0x7E, value };
  CS_Low();
  HAL_SPI_Transmit(&hspi1, txData, 2, 100);
  CS_High();
}

// 레지스터 읽기
static uint8_t PCD_ReadRegister(uint8_t reg)
{
  uint8_t txData = ((reg << 1) & 0x7E) | 0x80;
  uint8_t rxData = 0;
  CS_Low();
  HAL_SPI_Transmit(&hspi1, &txData, 1, 100);
  HAL_SPI_Receive(&hspi1, &rxData, 1, 100);
  CS_High();
  return rxData;
}

// 비트 세트
static void PCD_SetRegisterBitMask(uint8_t reg, uint8_t mask)
{
  uint8_t tmp = PCD_ReadRegister(reg);
  PCD_WriteRegister(reg, tmp | mask);
}

// 비트 클리어
static void PCD_ClearRegisterBitMask(uint8_t reg, uint8_t mask)
{
  uint8_t tmp = PCD_ReadRegister(reg);
  PCD_WriteRegister(reg, tmp & (~mask));
}

// CRC 계산
static uint8_t PCD_CalculateCRC(uint8_t *data, uint8_t length, uint8_t *result)
{
  PCD_WriteRegister(CommandReg, PCD_Idle);
  PCD_WriteRegister(DivIrqReg, 0x04);
  PCD_WriteRegister(FIFOLevelReg, 0x80);
  for (uint8_t i = 0; i < length; i++)
    PCD_WriteRegister(FIFODataReg, data[i]);
  PCD_WriteRegister(CommandReg, PCD_CalcCRC);

  uint32_t deadline = HAL_GetTick() + 25;
  while (1)
  {
    uint8_t n = PCD_ReadRegister(DivIrqReg);
    if (n & 0x04) break;
    if (HAL_GetTick() > deadline) return STATUS_TIMEOUT;
  }
  PCD_WriteRegister(CommandReg, PCD_Idle);
  result[0] = PCD_ReadRegister(CRCResultRegL);
  result[1] = PCD_ReadRegister(CRCResultRegH);
  return STATUS_OK;
}

// 트랜시버
static uint8_t PCD_TransceiveData(uint8_t *sendData, uint8_t sendLen,
                                   uint8_t *backData, uint8_t *backLen,
                                   uint8_t *validBits, uint8_t rxAlign, uint8_t checkCRC)
{
  uint8_t waitIRq = 0x30;
  uint8_t txLastBits = validBits ? *validBits : 0;
  uint8_t bitFraming = (rxAlign << 4) + txLastBits;

  PCD_WriteRegister(CommandReg, PCD_Idle);
  PCD_WriteRegister(ComIrqReg, 0x7F);
  PCD_WriteRegister(FIFOLevelReg, 0x80);
  for (uint8_t i = 0; i < sendLen; i++)
    PCD_WriteRegister(FIFODataReg, sendData[i]);
  PCD_WriteRegister(BitFramingReg, bitFraming);
  PCD_WriteRegister(CommandReg, PCD_Transceive);
  PCD_SetRegisterBitMask(BitFramingReg, 0x80);

  uint32_t deadline = HAL_GetTick() + 25;
  while (1)
  {
    uint8_t n = PCD_ReadRegister(ComIrqReg);
    if (n & waitIRq) break;
    if (n & 0x01) return STATUS_TIMEOUT;
    if (HAL_GetTick() > deadline) return STATUS_TIMEOUT;
  }
  PCD_ClearRegisterBitMask(BitFramingReg, 0x80);

  uint8_t errorRegValue = PCD_ReadRegister(ErrorReg);
  if (errorRegValue & 0x13) return STATUS_ERROR;

  uint8_t _validBits = 0;
  if (backData && backLen)
  {
    uint8_t n = PCD_ReadRegister(FIFOLevelReg);
    if (n > *backLen) return STATUS_NO_ROOM;
    *backLen = n;
    for (uint8_t i = 0; i < n; i++)
      backData[i] = PCD_ReadRegister(FIFODataReg);
    _validBits = PCD_ReadRegister(ControlReg) & 0x07;
    if (validBits) *validBits = _validBits;
  }

  if (errorRegValue & 0x08) return STATUS_COLLISION;

  if (checkCRC && backData && backLen && *backLen > 0)
  {
    if (*backLen == 1 && _validBits == 4) return STATUS_CRC_WRONG;
    if (*backLen < 2 || _validBits != 0) return STATUS_CRC_WRONG;
    uint8_t controlBuffer[2];
    uint8_t status = PCD_CalculateCRC(&backData[0], *backLen - 2, controlBuffer);
    if (status != STATUS_OK) return status;
    if ((backData[*backLen - 2] != controlBuffer[0]) ||
        (backData[*backLen - 1] != controlBuffer[1]))
      return STATUS_CRC_WRONG;
  }
  return STATUS_OK;
}

// REQA 전송
static uint8_t PICC_RequestA(uint8_t *bufferATQA, uint8_t *bufferSize)
{
  if (bufferATQA == NULL || *bufferSize < 2) return STATUS_NO_ROOM;
  PCD_ClearRegisterBitMask(CollReg, 0x80);
  uint8_t validBits = 7;
  uint8_t command = PICC_CMD_REQA;
  uint8_t status = PCD_TransceiveData(&command, 1, bufferATQA, bufferSize, &validBits, 0, 0);
  if (status != STATUS_OK) return status;
  if (*bufferSize != 2 || validBits != 0) return STATUS_ERROR;
  return STATUS_OK;
}

// 안티콜리전 + 선택
static uint8_t PICC_Select(Uid *uid)
{
  uint8_t cascadeLevel = 1;
  uint8_t result;
  uint8_t count;
  uint8_t usedBits;
  uint8_t uidIndex;
  int32_t currentLevelKnownBits;
  uint8_t buffer[9];
  uint8_t bufferUsed;
  uint8_t rxAlign;
  uint8_t txLastBits;
  uint8_t *responseBuffer;
  uint8_t responseLength;

  uid->size = 0;

  while (1)
  {
    uint8_t selectCode;
    switch (cascadeLevel)
    {
      case 1: selectCode = PICC_CMD_SEL_CL1; uidIndex = 0; break;
      case 2: selectCode = PICC_CMD_SEL_CL2; uidIndex = 3; break;
      case 3: selectCode = PICC_CMD_SEL_CL3; uidIndex = 6; break;
      default: return STATUS_INTERNAL_ERROR;
    }

    currentLevelKnownBits = 0;
    while (1)
    {
      if (currentLevelKnownBits >= 32)
      {
        buffer[0] = selectCode;
        buffer[1] = 0x70;
        buffer[6] = buffer[2] ^ buffer[3] ^ buffer[4] ^ buffer[5];
        uint8_t crcBuffer[2];
        result = PCD_CalculateCRC(buffer, 7, crcBuffer);
        if (result != STATUS_OK) return result;
        buffer[7] = crcBuffer[0];
        buffer[8] = crcBuffer[1];
        txLastBits = 0;
        bufferUsed = 9;
        responseBuffer = &buffer[6];
        responseLength = 3;
      }
      else
      {
        txLastBits = currentLevelKnownBits % 8;
        count = currentLevelKnownBits / 8;
        usedBits = count + (txLastBits ? 1 : 0);
        buffer[0] = selectCode;
        buffer[1] = (2 + usedBits) << 4 | txLastBits;
        bufferUsed = 2 + usedBits;
        responseBuffer = &buffer[bufferUsed];
        responseLength = sizeof(buffer) - bufferUsed;
      }

      rxAlign = txLastBits;
      PCD_WriteRegister(BitFramingReg, (rxAlign << 4) | txLastBits);
      result = PCD_TransceiveData(buffer, bufferUsed, responseBuffer, &responseLength, &txLastBits, rxAlign, 0);

      if (result == STATUS_COLLISION)
      {
        uint8_t valueOfCollReg = PCD_ReadRegister(CollReg);
        if (valueOfCollReg & 0x20) return STATUS_COLLISION;
        uint8_t collisionPos = valueOfCollReg & 0x1F;
        if (collisionPos == 0) collisionPos = 32;
        if (collisionPos <= currentLevelKnownBits) return STATUS_INTERNAL_ERROR;
        currentLevelKnownBits = collisionPos;
        count = currentLevelKnownBits % 8;
        uint8_t index = 1 + (currentLevelKnownBits / 8) + (count ? 1 : 0);
        buffer[index] |= (1 << count);
      }
      else if (result != STATUS_OK)
      {
        return result;
      }
      else
      {
        if (currentLevelKnownBits >= 32)
        {
          // 선택 완료
          break;
        }
        else
        {
          currentLevelKnownBits = 32;
          // 전체 UID 수신
          for (uint8_t index = 0; index < responseLength; index++)
            buffer[2 + index] = responseBuffer[index];
        }
      }
    }

    // UID 저장
    uint8_t responseLength2 = (buffer[2] == PICC_CMD_CT) ? 3 : 4;
    uint8_t startIndex = (buffer[2] == PICC_CMD_CT) ? 1 : 0;
    for (uint8_t index = 0; index < responseLength2; index++)
      uid->uidByte[uidIndex + index] = buffer[2 + startIndex + index];

    uid->size += responseLength2;

    if (responseLength != 3 || txLastBits != 0) return STATUS_ERROR;
    uint8_t crcBuf[2];
    result = PCD_CalculateCRC(responseBuffer, 1, crcBuf);
    if (result != STATUS_OK) return result;
    if ((crcBuf[0] != responseBuffer[1]) || (crcBuf[1] != responseBuffer[2]))
      return STATUS_CRC_WRONG;

    if (responseBuffer[0] & 0x04)
      cascadeLevel++;
    else
    {
      uid->sak = responseBuffer[0];
      break;
    }
  }
  return STATUS_OK;
}

// RC522 초기화
void RC522_Init(void)
{
  RST_High();
  HAL_Delay(50);

  // 소프트 리셋
  PCD_WriteRegister(CommandReg, PCD_SoftReset);
  HAL_Delay(50);

  // 타이머 설정
  PCD_WriteRegister(TModeReg, 0x80);
  PCD_WriteRegister(TPrescalerReg, 0xA9);
  PCD_WriteRegister(TReloadRegH, 0x03);
  PCD_WriteRegister(TReloadRegL, 0xE8);
  PCD_WriteRegister(TxASKReg, 0x40);
  PCD_WriteRegister(ModeReg, 0x3D);

  // 안테나 ON
  PCD_SetRegisterBitMask(TxControlReg, 0x03);

  printf("RC522 Init OK, Version: 0x%02X\r\n", PCD_ReadRegister(VersionReg));
}

// 새 카드 감지
uint8_t RC522_IsNewCardPresent(void)
{
  uint8_t bufferATQA[2];
  uint8_t bufferSize = sizeof(bufferATQA);
  PCD_WriteRegister(TxModeReg, 0x00);
  PCD_WriteRegister(RxModeReg, 0x00);
  PCD_WriteRegister(ModWidthReg, 0x26);
  return (PICC_RequestA(bufferATQA, &bufferSize) == STATUS_OK);
}

// 카드 UID 읽기
uint8_t RC522_ReadCardSerial(Uid *uid)
{
  return (PICC_Select(uid) == STATUS_OK);
}

// 카드 정지
void RC522_HaltA(void)
{
  uint8_t buffer[4];
  buffer[0] = PICC_CMD_HLTA;
  buffer[1] = 0;
  PCD_CalculateCRC(buffer, 2, &buffer[2]);
  PCD_TransceiveData(buffer, sizeof(buffer), NULL, NULL, NULL, 0, 0);
}

// UID를 문자열로 변환
void RC522_UidToString(Uid *uid, char *output)
{
  output[0] = '\0';
  char tmp[4];
  for (uint8_t i = 0; i < uid->size; i++)
  {
    sprintf(tmp, "%02X", uid->uidByte[i]);
    strcat(output, tmp);
  }
}
