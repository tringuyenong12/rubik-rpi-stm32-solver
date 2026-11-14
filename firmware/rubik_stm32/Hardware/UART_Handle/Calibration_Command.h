#ifndef CALIBRATION_COMMAND_H_
#define CALIBRATION_COMMAND_H_
#include "UART_Command.h"
void Calibration_CommandHandler(const UART_Command *command);
void Calibration_CommandInit(void);
bool Calibration_IsActive(void);
uint32_t Calibration_SettleMs(void);
#endif
