################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (13.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Hardware/Rubik_Control/Rubik_Control.c 

OBJS += \
./Hardware/Rubik_Control/Rubik_Control.o 

C_DEPS += \
./Hardware/Rubik_Control/Rubik_Control.d 


# Each subdirectory must supply rules for building sources it contributes
Hardware/Rubik_Control/%.o Hardware/Rubik_Control/%.su Hardware/Rubik_Control/%.cyclo: ../Hardware/Rubik_Control/%.c Hardware/Rubik_Control/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F411xE -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-Hardware-2f-Rubik_Control

clean-Hardware-2f-Rubik_Control:
	-$(RM) ./Hardware/Rubik_Control/Rubik_Control.cyclo ./Hardware/Rubik_Control/Rubik_Control.d ./Hardware/Rubik_Control/Rubik_Control.o ./Hardware/Rubik_Control/Rubik_Control.su

.PHONY: clean-Hardware-2f-Rubik_Control

