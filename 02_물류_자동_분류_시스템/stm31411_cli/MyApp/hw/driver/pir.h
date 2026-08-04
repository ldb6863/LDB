#ifndef _HW_DRIVER_PIR_H_
#define _HW_DRIVER_PIR_H


#include <stdbool.h>
#include <stdint.h>

void pirInit(void);
void pirEnable(bool enable);
bool pirRead(void);
void pirCheck(void);
void cliPir(uint8_t argc, char **argv);

#endif