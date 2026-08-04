#ifndef __BT_H_
#define __BT_H_

#include "main.h"
#include <string.h>
#include <stdio.h>

#define CMD_SIZE  150
#define ARR_CNT   10

// 수신 플래그 (stm32f4xx_it.c 또는 main.c에서 인터럽트 처리)
extern volatile uint8_t  btFlag;
extern volatile char     btData[CMD_SIZE];

// UART 핸들
extern UART_HandleTypeDef huart2;  // 디버그 출력
extern UART_HandleTypeDef huart6;  // 블루투스

void btInit(void);
void btSend(const char* msg);  // 블루투스로 서버에 전송

#endif
