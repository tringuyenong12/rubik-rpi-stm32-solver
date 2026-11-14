################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (13.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Hardware/UART_Handle/Calibration_Command.c \
../Hardware/UART_Handle/Config_Command.c \
../Hardware/UART_Handle/Control_Command.c \
../Hardware/UART_Handle/Rubik_Command.c \
../Hardware/UART_Handle/System_Command.c \
../Hardware/UART_Handle/UART_Command.c \
../Hardware/UART_Handle/UART_Handle.c 

OBJS += \
./Hardware/UART_Handle/Calibration_Command.o \
./Hardware/UART_Handle/Config_Command.o \
./Hardware/UART_Handle/Control_Command.o \
./Hardware/UART_Handle/Rubik_Command.o \
./Hardware/UART_Handle/System_Command.o \
./Hardware/UART_Handle/UART_Command.o \
./Hardware/UART_Handle/UART_Handle.o 

C_DEPS += \
./Hardware/UART_Handle/Calibration_Command.d \
./Hardware/UART_Handle/Config_Command.d \
./Hardware/UART_Handle/Control_Command.d \
./Hardware/UART_Handle/Rubik_Command.d \
./Hardware/UART_Handle/System_Command.d \
./Hardware/UART_Handle/UART_Command.d \
./Hardware/UART_Handle/UART_Handle.d 


# Each subdirectory must supply rules for building sources it contributes
Hardware/UART_Handle/%.o Hardware/UART_Handle/%.su Hardware/UART_Handle/%.cyclo: ../Hardware/UART_Handle/%.c Hardware/UART_Handle/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F411xE -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-Hardware-2f-UART_Handle

clean-Hardware-2f-UART_Handle:
	-$(RM) ./Hardware/UART_Handle/Calibration_Command.cyclo ./Hardware/UART_Handle/Calibration_Command.d ./Hardware/UART_Handle/Calibration_Command.o ./Hardware/UART_Handle/Calibration_Command.su ./Hardware/UART_Handle/Config_Command.cyclo ./Hardware/UART_Handle/Config_Command.d ./Hardware/UART_Handle/Config_Command.o ./Hardware/UART_Handle/Config_Command.su ./Hardware/UART_Handle/Control_Command.cyclo ./Hardware/UART_Handle/Control_Command.d ./Hardware/UART_Handle/Control_Command.o ./Hardware/UART_Handle/Control_Command.su ./Hardware/UART_Handle/Rubik_Command.cyclo ./Hardware/UART_Handle/Rubik_Command.d ./Hardware/UART_Handle/Rubik_Command.o ./Hardware/UART_Handle/Rubik_Command.su ./Hardware/UART_Handle/System_Command.cyclo ./Hardware/UART_Handle/System_Command.d ./Hardware/UART_Handle/System_Command.o ./Hardware/UART_Handle/System_Command.su ./Hardware/UART_Handle/UART_Command.cyclo ./Hardware/UART_Handle/UART_Command.d ./Hardware/UART_Handle/UART_Command.o ./Hardware/UART_Handle/UART_Command.su ./Hardware/UART_Handle/UART_Handle.cyclo ./Hardware/UART_Handle/UART_Handle.d ./Hardware/UART_Handle/UART_Handle.o ./Hardware/UART_Handle/UART_Handle.su

.PHONY: clean-Hardware-2f-UART_Handle

