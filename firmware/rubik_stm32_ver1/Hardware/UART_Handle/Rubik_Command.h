/*
 * Rubik_Command.h
 *
 *  Created on: Nov 15, 2026
 *      Author: Dell
 */

#ifndef RUBIK_COMMAND_H_
#define RUBIK_COMMAND_H_
#include "UART_Handle.h"
void Rubik_CommandHandler(uint8_t argc, char *argv[], uint16_t command_id);
#endif
