################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../MyApp/ap.c \
../MyApp/bt.c \
../MyApp/rc522.c 

OBJS += \
./MyApp/ap.o \
./MyApp/bt.o \
./MyApp/rc522.o 

C_DEPS += \
./MyApp/ap.d \
./MyApp/bt.d \
./MyApp/rc522.d 


# Each subdirectory must supply rules for building sources it contributes
MyApp/%.o MyApp/%.su MyApp/%.cyclo: ../MyApp/%.c MyApp/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F411xE -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -I"C:/Users/IOT23/Desktop/nucleo_f411re_uart2_printf_uart6_bt_clcd_dht11/MyApp" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-MyApp

clean-MyApp:
	-$(RM) ./MyApp/ap.cyclo ./MyApp/ap.d ./MyApp/ap.o ./MyApp/ap.su ./MyApp/bt.cyclo ./MyApp/bt.d ./MyApp/bt.o ./MyApp/bt.su ./MyApp/rc522.cyclo ./MyApp/rc522.d ./MyApp/rc522.o ./MyApp/rc522.su

.PHONY: clean-MyApp

