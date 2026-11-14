#ifndef CONFIG_COMMAND_H_
#define CONFIG_COMMAND_H_
#include "UART_Command.h"
void Config_CommandHandler(const UART_Command *command);
void Config_CommandInit(void);
uint32_t Config_UartTimeoutMs(void);
#endif
