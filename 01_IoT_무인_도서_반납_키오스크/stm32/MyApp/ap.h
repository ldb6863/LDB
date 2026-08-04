//#ifndef __AP_H_

//#define __AP_H_

//

//#include "main.h"

//#include <clcd.h>

//#include <string.h>

//#include <stdio.h>

//

//#define CMD_SIZE 150

//#define ARR_CNT  10

//

//void apInit(void);

//void apMain(void);

//

//#endif



#ifndef __AP_H_

#define __AP_H_



#include "main.h"

#include "bt.h"

#include "rc522.h"

#include <clcd.h>

#include <string.h>

#include <stdio.h>



#define BUZZER_GPIO_Port  GPIOB

#define BUZZER_Pin        GPIO_PIN_5



#define LED_GREEN_GPIO_Port GPIOB

#define LED_GREEN_Pin       GPIO_PIN_13



void apInit(void);

void apMain(void);

void apParseServer(char* msg);

void apLcdPrint(const char* line1, const char* line2);



#endif
