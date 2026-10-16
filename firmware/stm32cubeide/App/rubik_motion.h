#ifndef RUBIK_MOTION_H
#define RUBIK_MOTION_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Command bytes sent by the Raspberry Pi.  They exactly match the move map
 * from the original one-byte UART callback. */
typedef enum {
    RUBIK_CMD_PING = 0x00,
    RUBIK_CMD_F_CW = 1,
    RUBIK_CMD_F_CCW = 2,
    RUBIK_CMD_F_2 = 3,
    RUBIK_CMD_B_CW = 4,
    RUBIK_CMD_B_CCW = 5,
    RUBIK_CMD_B_2 = 6,
    RUBIK_CMD_L_CW = 7,
    RUBIK_CMD_L_CCW = 8,
    RUBIK_CMD_L_2 = 9,
    RUBIK_CMD_R_CW = 10,
    RUBIK_CMD_R_CCW = 11,
    RUBIK_CMD_R_2 = 12,
    RUBIK_CMD_U_CW = 13,
    RUBIK_CMD_U_CCW = 14,
    RUBIK_CMD_U_2 = 15,
    RUBIK_CMD_D_CW = 16,
    RUBIK_CMD_D_CCW = 17,
    RUBIK_CMD_D_2 = 18,
    RUBIK_CMD_STOP = 0xFD,
    RUBIK_CMD_HOME = 0xFE,
    RUBIK_CMD_FINISH = 0xFF,
} RubikMotionCommand;

/* Reuse the servoAngle() function already supplied by the CubeIDE project.
 * The driver must map servo indexes 0..7 to PWM channels or a PCA9685. */
typedef void (*RubikServoWriteFn)(int servo_index, int angle_deg);

void RubikMotion_Init(RubikServoWriteFn write_servo);
bool RubikMotion_IsSupported(uint8_t command);
bool RubikMotion_Home(void);
bool RubikMotion_Execute(uint8_t command);

/* Override this weak function in main.c if a buzzer or completion LED exists. */
void RubikMotion_OnFinished(void);

#ifdef __cplusplus
}
#endif

#endif
