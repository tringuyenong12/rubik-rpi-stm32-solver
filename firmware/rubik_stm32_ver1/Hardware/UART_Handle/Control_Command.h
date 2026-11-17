/*
 * Control_Command.h
 *
 *  Created on: Nov 15, 2026
 *      Author: Dell
 */

#ifndef UART_HANDLE_CONTROL_COMMAND_H_
#define UART_HANDLE_CONTROL_COMMAND_H_

#include "UART_Handle.h"
/* CONTROL SERVO <0..7|02|13|46|57> <position> [second_position].
 * Hai vi tri ap dung lan luot theo thu tu ID trong cap.
 * Mot vi tri ap dung chung cho ca cap; ID don chi nhan mot vi tri.
 * Cap 02/13 dung HOME/CLOCK/ANTI; cap 46/57 dung cac vi tri MOVE.
 * Gui ca hai servo truoc khi cho mot lan va tra DONE.
 */
void Control_CommandHandler(uint8_t argc, char *argv[], uint16_t command_id);

#endif /* UART_HANDLE_CONTROL_COMMAND_H_ */
