# Add sources to executable/library
target_sources(${PROJECT_NAME} PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/App/UART_Handle/UART_Handle.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/App/rubik_protocol.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Core/Src/main.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Core/Src/stm32f4xx_hal_msp.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Core/Src/stm32f4xx_it.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Core/Src/syscalls.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Core/Src/sysmem.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Core/Src/system_stm32f4xx.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Core/Startup/startup_stm32f411ceux.s"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_cortex.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma_ex.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_exti.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_flash.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_flash_ex.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_flash_ramfunc.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_gpio.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_i2c.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_i2c_ex.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pwr.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pwr_ex.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc_ex.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_uart.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Hardware/PCA9685/PCA9685.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Hardware/Rubik_Control/Rubik_Control.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Hardware/Servo_Control/Servo_Control.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/Testing/Testing.c"
)

configure_file("${CMAKE_CURRENT_SOURCE_DIR}/STM32F411CEUX_FLASH.ld" "${CMAKE_CURRENT_BINARY_DIR}" COPYONLY)

set_target_properties(${PROJECT_NAME} PROPERTIES LINK_DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/STM32F411CEUX_FLASH.ld")
