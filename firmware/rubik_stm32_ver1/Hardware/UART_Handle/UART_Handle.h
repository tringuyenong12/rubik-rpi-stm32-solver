#ifndef UART_HANDLE_UART_HANDLE_H_
#define UART_HANDLE_UART_HANDLE_H_

#include "stm32f4xx_hal.h"
#include "main.h"

#define UART_BUFFER_SIZE 64

void UART_Command_Init(UART_HandleTypeDef *huart);
void UART_Command_RxCallback(UART_HandleTypeDef *huart);
void UART_Command_Process(void);

#endif
