#ifndef __AP_AP_H_
#define __AP_AP_H_

#include "def.h"
#include "hw_def.h"
#include "bsp.h"
#include "hw.h"
#include "monitor.h"
#include "pca9685.h"
#include "conveyor_belt.h"
#include "hx711.h"

void apInit(void);
void apMain(void);
void apStopAutoTask(void);
void armSystemTask(void *argument);
void loadCellSystemTask(void *argument);
void systemTask(void *argument);

/* PIR 비상 정지용 extern 선언 */
extern volatile bool g_system_enabled;
extern volatile bool arm_running;
extern volatile bool arm_init_running;

#endif //__AP_AP_H_

// #ifndef __AP_AP_H_
// #define __AP_AP_H_

// #include "def.h"
// #include "hw_def.h"
// #include "bsp.h"
// #include "hw.h"
// #include "monitor.h"
// #include "pca9685.h"
// #include "conveyor_belt.h"
// #include "hx711.h"

// void apInit(void);
// void apMain(void);
// void apStopAutoTask(void);
// void armSystemTask(void *argument);
// void loadCellSystemTask(void *argument);
// void systemTask(void *argument);

// /* PIR 비상 정지용 extern 선언 */
// extern volatile bool g_system_enabled;
// extern volatile bool arm_running;

// #endif //__AP_AP_H_