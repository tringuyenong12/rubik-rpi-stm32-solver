/*
 * Calibration_Command.h
 *
 *  Created on: Nov 15, 2026
 *      Author: Dell
 */

#ifndef UART_HANDLE_CALIBRATION_COMMAND_H_
#define UART_HANDLE_CALIBRATION_COMMAND_H_

#include "UART_Handle.h"

/* CALIB SERVO SET <id> <position> <target_degree>: dat goc qua offset.
 * CALIB SERVO ADD/SUB <id> <position> <offset_degree>: tang/giam offset.
 * Ghi truc tiep servo[], goi Servo_Rotate/Servo_Move de ap dung ngay.
 * CALIB SERVO GET <id> <position>: doc goc vi tri + offset.
 * CALIB SERVO GET <id> <position> REAL_ANGLE: doc tong goc vi tri va offset,
 * khong phai goc do tu cam bien, khong gioi han tong ve 0..180.
 * CALIB SERVO GET <id> <field_name>: doc truong dung ten trong Servo_Control.h,
 * vi du target_angle, current_angle, offset_calib_home_angle, channel.
 * GET tra OK, VALUE voi 3 chu so thap phan, roi DONE.
 * SET/ADD/SUB tra OK, cap nhat servo xong thi DONE; lenh loi tra ERR.
 * Khong can START/SAVE/EXIT/RESET.
 */
void Calibration_CommandHandler(uint8_t argc, char *argv[], uint16_t command_id);

#endif /* UART_HANDLE_CALIBRATION_COMMAND_H_ */
