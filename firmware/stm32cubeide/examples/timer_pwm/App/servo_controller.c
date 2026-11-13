#include "servo_controller.h"

static bool is_valid_face(char face);

void ServoController_Init(ServoController *controller, TIM_HandleTypeDef *htim)
{
    controller->htim = htim;
    controller->tim_channels[0] = TIM_CHANNEL_1;
    controller->tim_channels[1] = TIM_CHANNEL_2;
    controller->tim_channels[2] = TIM_CHANNEL_3;
    controller->tim_channels[3] = TIM_CHANNEL_4;

    for (uint32_t i = 0; i < SERVO_CHANNEL_COUNT; i++) {
        controller->home_us[i] = 1500;
        controller->min_us[i] = 500;
        controller->max_us[i] = 2500;
    }

    controller->stopped = false;
}

void ServoController_Start(ServoController *controller)
{
    for (uint32_t i = 0; i < SERVO_CHANNEL_COUNT; i++) {
        HAL_TIM_PWM_Start(controller->htim, controller->tim_channels[i]);
    }
    ServoController_Home(controller);
}

bool ServoController_WriteUs(ServoController *controller, uint32_t channel, uint16_t pulse_us)
{
    if (channel >= SERVO_CHANNEL_COUNT) {
        return false;
    }
    if (pulse_us < controller->min_us[channel] || pulse_us > controller->max_us[channel]) {
        return false;
    }
    if (controller->stopped) {
        return false;
    }

    __HAL_TIM_SET_COMPARE(controller->htim, controller->tim_channels[channel], pulse_us);
    return true;
}

void ServoController_Home(ServoController *controller)
{
    controller->stopped = false;
    for (uint32_t i = 0; i < SERVO_CHANNEL_COUNT; i++) {
        ServoController_WriteUs(controller, i, controller->home_us[i]);
    }
}

void ServoController_Stop(ServoController *controller)
{
    controller->stopped = true;
}

bool ServoController_MoveFace(ServoController *controller, char face, int turns, uint32_t duration_ms)
{
    if (!is_valid_face(face)) {
        return false;
    }
    if (!(turns == 1 || turns == -1 || turns == 2)) {
        return false;
    }
    if (controller->stopped) {
        return false;
    }

    /*
     * TODO: thay bang sequence servo that sau khi chot co khi.
     * Hien tai ham nay chi giu timing de test UART pipeline end-to-end.
     */
    HAL_Delay(duration_ms);
    return true;
}

static bool is_valid_face(char face)
{
    return face == 'U' || face == 'R' || face == 'F' ||
           face == 'D' || face == 'L' || face == 'B';
}

