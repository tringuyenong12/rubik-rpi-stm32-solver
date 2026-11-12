/*
 * Servo_Control.c
 *
 *  Created on: Oct 27, 2026
 *      Author: phaplun
 */

#include "Servo_Control.h"
#include "../PCA9685/PCA9685.h"
#include <math.h>

/*
 * Anh xa kenh mac dinh: rotate 0..3, move 4..7. Doi .channel theo day thuc te.
 * Chi sua state.rotate voi ID ROTATE va state.move voi ID MOVE.
 * Khai bao mang khong gui PWM; current_angle = -1 den lenh dau tien.
 */
Servo_t servo[SERVO_COUNT ] =
{
	[SERVO_ROTATE_FRONT] = {
		.channel = 0,
		.state.rotate = {
			.current_angle = -1.0f, .target_angle = -1.0f,
			.home_angle = 90.0f, .offset_calib_home_angle = 0.0f,
			.clockwise_angle = 180.0f, .offset_calib_clockwise_angle = 0.0f,
			.anticlockwise_angle = 0.0f, .offset_calib_anticlockwise_angle = 0.0f
		}
	},
	[SERVO_ROTATE_RIGHT] = {
		.channel = 1,
		.state.rotate = {
			.current_angle = -1.0f, .target_angle = -1.0f,
			.home_angle = 90.0f, .offset_calib_home_angle = 0.0f,
			.clockwise_angle = 180.0f, .offset_calib_clockwise_angle = 0.0f,
			.anticlockwise_angle = 0.0f, .offset_calib_anticlockwise_angle = 0.0f
		}
	},
	[SERVO_ROTATE_BACK] = {
		.channel = 2,
		.state.rotate = {
			.current_angle = -1.0f, .target_angle = -1.0f,
			.home_angle = 90.0f, .offset_calib_home_angle = 0.0f,
			.clockwise_angle = 180.0f, .offset_calib_clockwise_angle = 0.0f,
			.anticlockwise_angle = 0.0f, .offset_calib_anticlockwise_angle = 0.0f
		}
	},
	[SERVO_ROTATE_LEFT] = {
		.channel = 3,
		.state.rotate = {
			.current_angle = -1.0f, .target_angle = -1.0f,
			.home_angle = 90.0f, .offset_calib_home_angle = 0.0f,
			.clockwise_angle = 180.0f, .offset_calib_clockwise_angle = 0.0f,
			.anticlockwise_angle = 0.0f, .offset_calib_anticlockwise_angle = 0.0f
		}
	},
	[SERVO_MOVE_FRONT] = {
		.channel = 4,
		.state.move = {
			.current_angle = -1.0f, .target_angle = -1.0f,
			.full_release_angle = 180.0f, .offset_calib_full_release_angle = 0.0f,
			.half_release_angle = 90.0f, .offset_calib_half_release_angle = 0.0f,
			.clamp_angle = 10.0f, .offset_calib_clamp_angle = 0.0f,
			.tight_clamp_angle = 0.0f, .offset_calib_tight_clamp_angle = 0.0f
		}
	},
	[SERVO_MOVE_RIGHT] = {
		.channel = 5,
		.state.move = {
			.current_angle = -1.0f, .target_angle = -1.0f,
			.full_release_angle = 180.0f, .offset_calib_full_release_angle = 0.0f,
			.half_release_angle = 90.0f, .offset_calib_half_release_angle = 0.0f,
			.clamp_angle = 10.0f, .offset_calib_clamp_angle = 0.0f,
			.tight_clamp_angle = 0.0f, .offset_calib_tight_clamp_angle = 0.0f
		}
	},
	[SERVO_MOVE_BACK] = {
		.channel = 6,
		.state.move = {
			.current_angle = -1.0f, .target_angle = -1.0f,
			.full_release_angle = 180.0f, .offset_calib_full_release_angle = 0.0f,
			.half_release_angle = 90.0f, .offset_calib_half_release_angle = 0.0f,
			.clamp_angle = 10.0f, .offset_calib_clamp_angle = 0.0f,
			.tight_clamp_angle = 0.0f, .offset_calib_tight_clamp_angle = 0.0f
		}
	},
	[SERVO_MOVE_LEFT] = {
		.channel = 7,
		.state.move = {
			.current_angle = -1.0f, .target_angle = -1.0f,
			.full_release_angle = 180.0f, .offset_calib_full_release_angle = 0.0f,
			.half_release_angle = 90.0f, .offset_calib_half_release_angle = 0.0f,
			.clamp_angle = 10.0f, .offset_calib_clamp_angle = 0.0f,
			.tight_clamp_angle = 0.0f, .offset_calib_tight_clamp_angle = 0.0f
		}
	}
};

void Servo_Init(){

}



void Servo_Start_Position(){
	
	for (int i = 4; i < 8; i++)
	{
		Servo_Move((Servo_ID_t)i, SERVO_MOVE_FULL_RELEASE);
	}

	for (int i = 0; i < 4; i++)
	{
		Servo_Rotate((Servo_ID_t)i, SERVO_ROTATE_HOME);
	}

	waitUntilServosDone();
}



static bool Servo_WriteAngle(uint8_t channel, float angle,
		float *current_angle, float *target_angle)
{
	if (channel > 15 || !isfinite(angle))
	{
		return false;
	}

	if (angle < 0.0f)
	{
		angle = 0.0f;
	}
	else if (angle > 180.0f)
	{
		angle = 180.0f;
	}

	PCA9685_SetServoAngle(channel, angle);
	*target_angle = angle;
	*current_angle = angle;
	return true;
}

bool Servo_Move(Servo_ID_t id, Servo_Move_Position_t position)
{
	Servo_Move_t *move;
	float angle;

	if (id < SERVO_MOVE_FRONT || id > SERVO_MOVE_LEFT)
	{
		return false;
	}

	move = &servo[id].state.move;
	switch (position)
	{
	case SERVO_MOVE_FULL_RELEASE:
		angle = move->full_release_angle + move->offset_calib_full_release_angle;
		break;
	case SERVO_MOVE_HALF_RELEASE:
		angle = move->half_release_angle + move->offset_calib_half_release_angle;
		break;
	case SERVO_MOVE_CLAMP:
		angle = move->clamp_angle + move->offset_calib_clamp_angle;
		break;
	case SERVO_MOVE_TIGHT_CLAMP:
		angle = move->tight_clamp_angle + move->offset_calib_tight_clamp_angle;
		break;

	default:
		return false;
	}

	return Servo_WriteAngle(servo[id].channel, angle,
			&move->current_angle, &move->target_angle);
}

bool Servo_Rotate(Servo_ID_t id, Servo_Rotate_Position_t position)
{
	Servo_Rotate_t *rotate;
	float angle;

	if (id < SERVO_ROTATE_FRONT || id > SERVO_ROTATE_LEFT)
	{
		return false;
	}

	rotate = &servo[id].state.rotate;
	switch (position)
	{
	case SERVO_ROTATE_HOME:
		angle = rotate->home_angle + rotate->offset_calib_home_angle;
		break;
	case SERVO_ROTATE_CLOCKWISE:
		angle = rotate->clockwise_angle + rotate->offset_calib_clockwise_angle;
		break;
	case SERVO_ROTATE_ANTICLOCKWISE:
		angle = rotate->anticlockwise_angle + rotate->offset_calib_anticlockwise_angle;
		break;
	default:
		return false;
	}

	return Servo_WriteAngle(servo[id].channel, angle,
			&rotate->current_angle, &rotate->target_angle);
}

bool Servo_SetRotateCalibration(Servo_ID_t id, Servo_Rotate_Position_t position, float angle_deg)
{
    if (id < SERVO_ROTATE_FRONT || id > SERVO_ROTATE_LEFT ||
        !isfinite(angle_deg) || angle_deg < 0.0f || angle_deg > 180.0f) {
        return false;
    }
    Servo_Rotate_t *rotate = &servo[id].state.rotate;
    float base;
    float *offset;
    switch (position) {
    case SERVO_ROTATE_HOME:
        base = rotate->home_angle;
        offset = &rotate->offset_calib_home_angle;
        break;
    case SERVO_ROTATE_CLOCKWISE:
        base = rotate->clockwise_angle;
        offset = &rotate->offset_calib_clockwise_angle;
        break;
    case SERVO_ROTATE_ANTICLOCKWISE:
        base = rotate->anticlockwise_angle;
        offset = &rotate->offset_calib_anticlockwise_angle;
        break;
    default:
        return false;
    }
    if (!isfinite(base)) {
        return false;
    }
    *offset = angle_deg - base;
    return true;
}

bool Servo_SetMoveCalibration(Servo_ID_t id, Servo_Move_Position_t position, float angle_deg)
{
    if (id < SERVO_MOVE_FRONT || id > SERVO_MOVE_LEFT ||
        !isfinite(angle_deg) || angle_deg < 0.0f || angle_deg > 180.0f) {
        return false;
    }
    Servo_Move_t *move = &servo[id].state.move;
    float base;
    float *offset;
    switch (position) {
    case SERVO_MOVE_FULL_RELEASE:
        base = move->full_release_angle;
        offset = &move->offset_calib_full_release_angle;
        break;
    case SERVO_MOVE_HALF_RELEASE:
        base = move->half_release_angle;
        offset = &move->offset_calib_half_release_angle;
        break;
    case SERVO_MOVE_CLAMP:
        base = move->clamp_angle;
        offset = &move->offset_calib_clamp_angle;
        break;
    case SERVO_MOVE_TIGHT_CLAMP:
        base = move->tight_clamp_angle;
        offset = &move->offset_calib_tight_clamp_angle;
        break;
    default:
        return false;
    }
    if (!isfinite(base)) {
        return false;
    }
    *offset = angle_deg - base;
    return true;
}

bool waitUntilServosDone(){
	HAL_Delay(Delay_Servo_Move);
	return true;
}
