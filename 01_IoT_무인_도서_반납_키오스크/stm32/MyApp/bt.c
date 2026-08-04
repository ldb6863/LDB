#include "bt.h"

// 수신 버퍼 및 플래그 정의
volatile uint8_t btFlag = 0;
volatile char    btData[CMD_SIZE] = {0};

// 디버그 출력용 (printf → USART2)
#ifdef __GNUC__
int __io_putchar(int ch)
#else
int fputc(int ch, FILE *f)
#endif
{
  HAL_UART_Transmit(&huart2, (uint8_t *)&ch, 1, 0xFFFF);
  return ch;
}

void btInit(void)
{
  // 블루투스 수신 인터럽트 시작
  extern uint8_t btchar;
  HAL_UART_Receive_IT(&huart6, &btchar, 1);
  printf("BT Init OK\r\n");
}

void btSend(const char* msg)
{
  HAL_UART_Transmit(&huart6, (uint8_t*)msg, strlen(msg), 0xFFFF);
  printf("BT send: %s", msg);
}
