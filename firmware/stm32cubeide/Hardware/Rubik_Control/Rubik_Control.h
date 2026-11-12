/*
 * Rubik_Control.h
 *
 *  Created on: Oct 27, 2026
 *      Author: Dell
 */

#ifndef RUBIK_CONTROL_RUBIK_CONTROL_H_
#define RUBIK_CONTROL_RUBIK_CONTROL_H_

#include "../Servo_Control/Servo_Control.h"

/* Cac ham blocking; ban dau rotate o HOME, move o CLAMP. */

void Rubik_Hold_Start_Position(void);	// Dua Rubik ve trang thai ban dau truoc khi bat dau nhan lenh

void Rubik_Left(void);
void Rubik_Left_(void);
void Rubik_Right(void);
void Rubik_Right_(void);
void Rubik_Front(void);
void Rubik_Front_(void);
void Rubik_Back(void);
void Rubik_Back_(void);
void Rubik_UpToFront(void);
void Rubik_Up_ToFront(void);
void Rubik_DownToFront(void);
void Rubik_Down_ToFront(void);
void Rubik_Front_Back_Move_Full_Release(void);
void Rubik_Left_Right_Move_Full_Release(void);

#endif /* RUBIK_CONTROL_RUBIK_CONTROL_H_ */
