################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (13.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Hardware/PCA9685/PCA9685.c 

OBJS += \
./Hardware/PCA9685/PCA9685.o 

C_DEPS += \
./Hardware/PCA9685/PCA9685.d 


# Each subdirectory must supply rules for building sources it contributes
Hardware/PCA9685/%.o Hardware/PCA9685/%.su Hardware/PCA9685/%.cyclo: ../Hardware/PCA9685/%.c Hardware/PCA9685/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F411xE -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-Hardware-2f-PCA9685

clean-Hardware-2f-PCA9685:
	-$(RM) ./Hardware/PCA9685/PCA9685.cyclo ./Hardware/PCA9685/PCA9685.d ./Hardware/PCA9685/PCA9685.o ./Hardware/PCA9685/PCA9685.su

.PHONY: clean-Hardware-2f-PCA9685

