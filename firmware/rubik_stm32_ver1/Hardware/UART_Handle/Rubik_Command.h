/*
 * Rubik_Command.h
 *
 *  Created on: Nov 15, 2026
 *      Author: Dell
 */

#ifndef RUBIK_COMMAND_H_
#define RUBIK_COMMAND_H_
#include "UART_Handle.h"
/* MOVE LR = L + R; L_R = L_ + R; FB = F + B; F_B = F_ + B.
 * Moi cap xoay/nha/HOME/kep duoc gui lien tiep truoc khi cho hoan tat.
 */
void Rubik_CommandHandler(uint8_t argc, char *argv[], uint16_t command_id);
#endif
