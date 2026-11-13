#include "servo_controller.h"
#include <assert.h>
#include <stddef.h>
#include <stdio.h>

static TIM_TypeDef tim2, tim3;
static TIM_HandleTypeDef htim2 = {&tim2}, htim3 = {&tim3};
static unsigned writes, starts, stops, fail_start, fail_stop;

void test_set_compare(TIM_HandleTypeDef *timer, uint32_t channel, uint32_t value)
{
    ++writes;
    timer->Instance->CCR[channel / 4u] = value;
}
HAL_StatusTypeDef HAL_TIM_PWM_Start(TIM_HandleTypeDef *timer, uint32_t channel)
{
    ++starts;
    assert(timer->Instance->CCR[channel / 4u] > 0u); /* Loaded before enable. */
    timer->Instance->running[channel / 4u] = 1;
    return starts == fail_start ? HAL_ERROR : HAL_OK;
}
HAL_StatusTypeDef HAL_TIM_PWM_Stop(TIM_HandleTypeDef *timer, uint32_t channel)
{
    ++stops;
    if (stops == fail_stop) {
        return HAL_ERROR;
    }
    timer->Instance->running[channel / 4u] = 0;
    return HAL_OK;
}

static void reset(void)
{
    tim2 = (TIM_TypeDef){.ARR = 19999u};
    tim3 = (TIM_TypeDef){.ARR = 39999u};
    writes = starts = stops = fail_start = fail_stop = 0;
}
static ServoProfile profile(uint32_t ch)
{
    return (ServoProfile){
        .pwm_channel_index = ch, .pulse_home_us = 1510,
        .pulse_approach_us = 1200, .pulse_engaged_us = 2000,
        .pulse_retract_us = 1000, .pulse_scan_us = 1600,
        .pulse_min_us = 700, .pulse_max_us = 2300,
        .state = ACTUATOR_STATE_ENGAGED
    };
}
static void setup(ServoController *c)
{
    reset();
    ServoController_Init(c, &htim2);
    ServoProfile p = profile(0);
    assert(ServoController_ConfigProfile(c, SERVO_ROLE_CARRIAGE_NW, &p));
}

static void test_invalid_input(void)
{
    ServoController c;
    setup(&c);
    ServoController_Init(NULL, NULL);
    ServoController_Stop(NULL);
    assert(!ServoController_Start(NULL));
    assert(!ServoController_Home(NULL));
    assert(!ServoController_WriteUs(NULL, 0, 1500));
    assert(!ServoController_WriteRole(NULL, 0, 0));
    assert(!ServoController_WriteAngle(NULL, 0, 0));
    assert(!ServoController_ConfigChannel(NULL, 0, &htim2, TIM_CHANNEL_1, 1000000));
    assert(!ServoController_ConfigProfile(&c, (ServoRole)-1, &c.profiles[0]));
    assert(!ServoController_ConfigProfile(&c, SERVO_ROLE_COUNT, &c.profiles[0]));
    assert(!ServoController_ConfigProfile(&c, 0, NULL));
    assert(!ServoController_ConfigAngles(&c, (ServoRole)-1, NULL));
    assert(!ServoController_WriteRole(&c, (ServoRole)-1, 0));
    assert(!ServoController_WriteAngle(&c, (ServoRole)-1, 0));
    assert(ServoController_GetState(&c, (ServoRole)-1) == ACTUATOR_STATE_UNKNOWN);
    assert(ServoController_GetState(NULL, 0) == ACTUATOR_STATE_UNKNOWN);
    assert(!ServoController_WriteUs(&c, 0, 1500)); /* Not started. */
    assert(!ServoController_Home(&c));
    assert(writes == 0 && starts == 0);
}

static void test_configuration(void)
{
    ServoController c;
    reset();
    ServoController_Init(&c, NULL);
    assert(!ServoController_Start(&c));
    ServoProfile p = profile(0);
    assert(!ServoController_ConfigProfile(&c, 0, &p)); /* Unbound. */
    assert(!ServoController_ConfigChannel(&c, 10, &htim2, TIM_CHANNEL_1, 1000000));
    assert(!ServoController_ConfigChannel(&c, 0, &htim2, 42, 1000000));
    assert(!ServoController_ConfigChannel(&c, 0, &htim2, TIM_CHANNEL_1, 0));
    TIM_HandleTypeDef invalid = {NULL};
    assert(!ServoController_ConfigChannel(&c, 0, &invalid, TIM_CHANNEL_1, 1000000));
    assert(ServoController_ConfigChannel(&c, 0, &htim2, TIM_CHANNEL_1, 1000000));
    TIM_HandleTypeDef alias = {&tim2};
    assert(!ServoController_ConfigChannel(&c, 1, &alias, TIM_CHANNEL_1, 1000000));
    assert(!ServoController_ConfigChannel(&c, 1, &alias, TIM_CHANNEL_2, 2000000));
    assert(ServoController_ConfigProfile(&c, 0, &p));
    assert(c.profiles[0].state == ACTUATOR_STATE_UNKNOWN);
    assert(!ServoController_ConfigProfile(&c, 1, &p)); /* Shared channel. */
    assert(!ServoController_ConfigChannel(&c, 0, &htim3, TIM_CHANNEL_1, 2000000));
    p.pulse_home_us = 2400;
    assert(!ServoController_ConfigProfile(&c, 0, &p));
    assert(c.profiles[0].pulse_home_us == 1510); /* Atomic rejection. */
    p = profile(0); p.pulse_min_us = 0;
    assert(!ServoController_ConfigProfile(&c, 0, &p));
    p = profile(0); p.pulse_max_us = 700;
    assert(!ServoController_ConfigProfile(&c, 0, &p));
    p = profile(10);
    assert(!ServoController_ConfigProfile(&c, 0, &p));
    tim2.ARR = 1000; /* Period changed: Start must revalidate. */
    assert(!ServoController_Start(&c));
    assert(writes == 0 && starts == 0);
}

static void test_timers_and_limits(void)
{
    ServoController c;
    setup(&c);
    assert(ServoController_ConfigChannel(&c, 4, &htim3, TIM_CHANNEL_1, 2000000));
    ServoProfile p = profile(4);
    p.pulse_home_us = 1550;
    assert(ServoController_ConfigProfile(&c, SERVO_ROLE_TOOL_NW, &p));
    assert(ServoController_Start(&c));
    assert(starts == 2 && writes == 2);
    assert(tim2.CCR[0] == 1510 && tim3.CCR[0] == 3100);
    assert(ServoController_WriteUs(&c, 4, 1800));
    assert(tim2.CCR[0] == 1510 && tim3.CCR[0] == 3600);
    assert(ServoController_WriteUs(&c, 0, 700));
    assert(ServoController_WriteUs(&c, 0, 2300));
    unsigned before = writes;
    assert(!ServoController_WriteUs(&c, 0, 699));
    assert(!ServoController_WriteUs(&c, 0, 2301));
    assert(!ServoController_WriteUs(&c, 1, 1500)); /* Bound but no profile. */
    assert(!ServoController_WriteUs(&c, 10, 1500));
    assert(!ServoController_Start(&c));
    assert(!ServoController_ConfigProfile(&c, SERVO_ROLE_TOOL_NW, &p));
    assert(!ServoController_WriteRole(&c, 0, (ServoTarget)-1));
    assert(!ServoController_WriteRole(&c, 0, (ServoTarget)99));
    assert(!ServoController_WriteRole(&c, SERVO_ROLE_TOOL_NE, SERVO_TARGET_HOME));
    assert(writes == before);
    assert(ServoController_Clamp(&c, SERVO_ROLE_TOOL_NW, true));
    assert(tim3.CCR[0] == 4000);
    assert(ServoController_GetState(&c, SERVO_ROLE_TOOL_NW) == ACTUATOR_STATE_ENGAGED);
    assert(ServoController_Clamp(&c, SERVO_ROLE_TOOL_NW, false));
    assert(tim3.CCR[0] == 2000);
    assert(!ServoController_Clamp(&c, SERVO_ROLE_CARRIAGE_NW, true));
}

static void test_angles(bool reversed)
{
    ServoController c;
    setup(&c);
    ServoAngleCalibration cal = {{-900, 0, 900}, {800, 1510, 2200}};
    if (reversed) {
        cal.pulse_us[0] = 2200;
        cal.pulse_us[2] = 800;
    }
    assert(ServoController_ConfigAngles(&c, 0, &cal));
    assert(ServoController_Start(&c));
    for (int i = 0; i < 3; ++i) {
        assert(ServoController_WriteAngle(&c, 0, cal.angle_decideg[i]));
        assert(tim2.CCR[0] == cal.pulse_us[i]);
    }
    assert(ServoController_WriteAngle(&c, 0, -450));
    assert(tim2.CCR[0] == (reversed ? 1855u : 1155u));
    assert(ServoController_WriteAngle(&c, 0, 450));
    assert(tim2.CCR[0] == (reversed ? 1155u : 1855u));
    unsigned before = writes;
    assert(!ServoController_WriteAngle(&c, 0, -901));
    assert(!ServoController_WriteAngle(&c, 0, 901));
    assert(!ServoController_WriteAngle(&c, 0, 1800)); /* No wrapping. */
    assert(!ServoController_WriteAngle(&c, 1, 0));
    assert(writes == before);
}

static void test_calibration_validation(void)
{
    ServoController c;
    setup(&c);
    ServoAngleCalibration cal = {{0, 900, 1800}, {800, 1510, 2200}};
    assert(!ServoController_WriteAngle(&c, 0, 0));
    assert(!ServoController_ConfigAngles(&c, 1, &cal));
    assert(ServoController_ConfigAngles(&c, 0, &cal));
    cal.angle_decideg[1] = 0;
    assert(!ServoController_ConfigAngles(&c, 0, &cal));
    cal.angle_decideg[1] = 900; cal.angle_decideg[2] = 2701;
    assert(!ServoController_ConfigAngles(&c, 0, &cal));
    cal.angle_decideg[2] = 1800; cal.pulse_us[1] = 2200;
    assert(!ServoController_ConfigAngles(&c, 0, &cal));
    cal.pulse_us[1] = 1510; cal.pulse_us[0] = 699;
    assert(!ServoController_ConfigAngles(&c, 0, &cal));
    assert(c.angles[0].pulse_us[0] == 800);
    ServoProfile p = profile(0);
    assert(ServoController_ConfigProfile(&c, 0, &p));
    assert(!c.angle_configured[0]);
    cal = (ServoAngleCalibration){{-1350, 0, 1350}, {800, 1510, 2200}};
    assert(ServoController_ConfigAngles(&c, 0, &cal));
}

static void test_stop_home_and_placeholders(void)
{
    ServoController c;
    setup(&c);
    ServoAngleCalibration cal = {{-900, 0, 900}, {800, 1510, 2200}};
    assert(ServoController_ConfigAngles(&c, 0, &cal));
    assert(ServoController_Start(&c));
    assert(ServoController_WriteUs(&c, 0, 1700));
    unsigned before = writes;
    ServoController_Stop(&c);
    assert(c.stopped && tim2.CCR[0] == 1700 && tim2.running[0]);
    assert(ServoController_GetState(&c, 0) == ACTUATOR_STATE_STOPPED);
    assert(!ServoController_WriteUs(&c, 0, 1800));
    assert(!ServoController_WriteAngle(&c, 0, 0));
    assert(!ServoController_WriteRole(&c, 0, SERVO_TARGET_HOME));
    assert(!ServoController_Start(&c));
    tim2.ARR = 1000;
    assert(!ServoController_Home(&c));
    assert(c.stopped && writes == before);
    tim2.ARR = 19999;
    assert(ServoController_Home(&c));
    assert(!c.stopped && tim2.CCR[0] == 1510);
    assert(ServoController_GetState(&c, 0) == ACTUATOR_STATE_HOME);
    before = writes;
    assert(!ServoController_TurnFace(&c, 'R', 1, 300));
    assert(!ServoController_MoveFace(&c, 'U', -1, 300));
    assert(!ServoController_ScanPose(&c, 'U'));
    assert(writes == before);
}

static void test_start_failure(bool cleanup_fails)
{
    ServoController c;
    setup(&c);
    ServoProfile p = profile(1);
    assert(ServoController_ConfigProfile(&c, 1, &p));
    fail_start = 2;
    fail_stop = cleanup_fails ? 1 : 0;
    assert(!ServoController_Start(&c));
    assert(c.stopped && !c.started && starts == 2 && stops == 2);
    assert(ServoController_GetState(&c, 0) == ACTUATOR_STATE_ERROR);
    assert(!ServoController_WriteUs(&c, 0, 1500));
    assert(!ServoController_Home(&c));
    if (cleanup_fails) {
        assert(c.channels[0].started);
        assert(!ServoController_ConfigProfile(&c, 0, &p));
        assert(!ServoController_Start(&c));
    } else {
        assert(!tim2.running[0] && !tim2.running[1]);
        fail_start = 0;
        assert(ServoController_Start(&c));
    }
}

static void test_strings(void)
{
    ServoRole role = SERVO_ROLE_COUNT;
    ServoTarget target = SERVO_TARGET_SAFE;
    assert(ServoRole_FromString("center_rotate", &role));
    assert(role == SERVO_ROLE_CENTER_ROTATE);
    assert(ServoTarget_FromString("approach", &target));
    assert(target == SERVO_TARGET_APPROACH);
    assert(!ServoRole_FromString(NULL, &role));
    assert(!ServoRole_FromString("tool_nw", NULL));
    assert(!ServoRole_FromString("invalid", &role));
    assert(!ServoTarget_FromString(NULL, &target));
    assert(!ServoTarget_FromString("home", NULL));
    assert(!ServoTarget_FromString("invalid", &target));
}

int main(void)
{
    test_invalid_input();
    test_configuration();
    test_timers_and_limits();
    test_angles(false);
    test_angles(true);
    test_calibration_validation();
    test_stop_home_and_placeholders();
    test_start_failure(false);
    test_start_failure(true);
    test_strings();
    puts("PASS: 10 servo test scenarios");
    return 0;
}
