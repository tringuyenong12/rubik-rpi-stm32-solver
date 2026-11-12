#ifndef SERVO_CONTROLLER_H
#define SERVO_CONTROLLER_H

#include "main.h"
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SERVO_CHANNEL_COUNT 4

typedef struct {
    TIM_HandleTypeDef *htim;
    uint32_t tim_channels[SERVO_CHANNEL_COUNT];
    uint16_t home_us[SERVO_CHANNEL_COUNT];
    uint16_t min_us[SERVO_CHANNEL_COUNT];
    uint16_t max_us[SERVO_CHANNEL_COUNT];
    bool stopped;
} ServoController;

void ServoController_Init(ServoController *controller, TIM_HandleTypeDef *htim);
void ServoController_Start(ServoController *controller);
bool ServoController_WriteUs(ServoController *controller, uint32_t channel, uint16_t pulse_us);
void ServoController_Home(ServoController *controller);
void ServoController_Stop(ServoController *controller);
bool ServoController_MoveFace(ServoController *controller, char face, int turns, uint32_t duration_ms);

#ifdef __cplusplus
}
#endif

#endif

