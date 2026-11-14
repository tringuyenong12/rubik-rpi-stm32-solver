#ifndef UART_HANDLE_UART_HANDLE_H_
#define UART_HANDLE_UART_HANDLE_H_

#include "stm32f4xx_hal.h"

#define UART_BUFFER_SIZE 64
#define UART_COMMAND_TRACE 1 /* Temporary UART reception/parser diagnostics. */

void UART_Command_Init(UART_HandleTypeDef *huart);
void UART_Command_RxCallback(UART_HandleTypeDef *huart);
void UART_Command_ErrorCallback(UART_HandleTypeDef *huart);
void UART_Command_Process(void);
void UART_Handle_Process(void);

#endif
