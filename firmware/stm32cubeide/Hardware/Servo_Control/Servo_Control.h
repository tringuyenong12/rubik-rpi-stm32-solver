/*
 * Servo_Control.h
 *
 *  Created on: Oct 27, 2026
 *      Author: phaplun
 */

#ifndef SERVO_CONTROL_SERVO_CONTROL_H_
#define SERVO_CONTROL_SERVO_CONTROL_H_

#include <stdint.h>
#include <stdbool.h>

#define SERVO_COUNT 8
#define Delay_Servo_Move 1000	// ms, thoi gian servo di chuyen xong truoc khi gui lenh tiep theo

typedef enum
{
	SERVO_ROTATE_FRONT = 0,		// truc xoay mat FRONT cua Rubik
	SERVO_ROTATE_RIGHT = 1,
	SERVO_ROTATE_BACK = 2,
	SERVO_ROTATE_LEFT = 3,

	SERVO_MOVE_FRONT = 4,	// Di chuyen tien, lui cua truc FRONT cua Rubik
	SERVO_MOVE_RIGHT = 5,
	SERVO_MOVE_BACK = 6,
	SERVO_MOVE_LEFT = 7,

} Servo_ID_t;



typedef struct
{
	/* Goc lenh gan nhat, khong phai phan hoi vi tri; -1 khi chua gui lenh. */
	float current_angle;
	/* Goc PWM sau khi cong offset va gioi han trong 0..180 do. */
	float target_angle;

	float  home_angle;	// goc mac dinh cua moi servo arm, la 90 neu khong calib
	float  offset_calib_home_angle;

	float clockwise_angle;	// quay chieu kim dong ho sang phai, la 180 neu khong calib
	float offset_calib_clockwise_angle;

	float anticlockwise_angle;	// quay nguoc chieu kim dong ho sang phai, la 0 neu khong calib
	float offset_calib_anticlockwise_angle;

} Servo_Rotate_t;



typedef struct
{
	/* Goc lenh gan nhat, khong phai phan hoi vi tri; -1 khi chua gui lenh. */
	float current_angle;
	/* Goc PWM sau khi cong offset va gioi han trong 0..180 do. */
	float target_angle;

	float full_release_angle; 	// goc nha cua truot la 180 do, mac dinh
	float offset_calib_full_release_angle;

	float half_release_angle; 	// goc nha mot nua cua truot la 90 do, mac dinh
	float offset_calib_half_release_angle;

	float clamp_angle; 	// goc kep cua truot la 10 do, mac dinh
	float offset_calib_clamp_angle;

	float tight_clamp_angle; 	// goc kep mat cua truot la 0 do, mac dinh, kep chat hon de giu
	float offset_calib_tight_clamp_angle;

} Servo_Move_t;

typedef enum
{
	SERVO_ROTATE_HOME = 0,
	SERVO_ROTATE_CLOCKWISE,
	SERVO_ROTATE_ANTICLOCKWISE
} Servo_Rotate_Position_t;

typedef enum
{
	SERVO_MOVE_FULL_RELEASE = 0,
	SERVO_MOVE_HALF_RELEASE,
	SERVO_MOVE_CLAMP,
	SERVO_MOVE_TIGHT_CLAMP
} Servo_Move_Position_t;

typedef struct
{
	uint8_t channel; /* Kenh PCA9685: 0..15, doc lap voi Servo_ID_t. */
	union
	{
		Servo_Rotate_t rotate;
		Servo_Move_t move;
	} state;
} Servo_t;


extern Servo_t servo[SERVO_COUNT];

/*
 * Goi sau PCA9685_Init(50). Moi lenh gui ngay goc tuyet doi, khong cho
 * servo di chuyen xong. Offset tinh bang do, duoc cong vao goc vi tri.
 * true: da goi driver; false: sai ID/loai, vi tri, kenh hoac goc khong huu han.
 * Driver PCA9685 hien tai khong tra loi I2C, nen true khong xac nhan phan cung.
 * Khong tu dong phoi hop kep/nha giua cac truc.
 * Vi du:
 *   Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
 *   Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_CLOCKWISE);
 */
void Servo_Init(void);
void Servo_Start_Position(void);
bool Servo_Move(Servo_ID_t id, Servo_Move_Position_t position);
bool Servo_Rotate(Servo_ID_t id, Servo_Rotate_Position_t position);
/* Set the final angle for a named position by updating its offset in RAM. */
bool Servo_SetRotateCalibration(Servo_ID_t id, Servo_Rotate_Position_t position, float angle_deg);
bool Servo_SetMoveCalibration(Servo_ID_t id, Servo_Move_Position_t position, float angle_deg);
bool waitUntilServosDone();

#endif /* SERVO_CONTROL_SERVO_CONTROL_H_ */
