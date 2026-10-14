#include "servo_controller.h"

#include <stddef.h>
#include <string.h>

static const char *const role_names[SERVO_ROLE_COUNT] = {
    "carriage_nw", "carriage_ne", "carriage_sw", "carriage_se",
    "tool_nw", "tool_ne", "tool_sw", "tool_se", "center_lift", "center_rotate"
};
static const char *const target_names[] = {
    "home", "approach", "engaged", "retract", "scan", "solve", "safe"
};

static bool valid_role(ServoRole role)
{
    return (uint32_t)role < (uint32_t)SERVO_ROLE_COUNT;
}

static bool valid_channel(uint32_t channel)
{
    return channel == TIM_CHANNEL_1 || channel == TIM_CHANNEL_2 ||
           channel == TIM_CHANNEL_3 || channel == TIM_CHANNEL_4;
}

/* Configuration is locked while any PWM output may still be running. */
static bool can_configure(const ServoController *c)
{
    if (c == NULL || c->started) {
        return false;
    }
    for (uint32_t i = 0; i < SERVO_MAX_CHANNELS; ++i) {
        if (c->channels[i].started) {
            return false;
        }
    }
    return true;
}

static bool pulse_ticks(const ServoPwmChannel *ch, uint16_t us, uint32_t *ticks)
{
    if (ch->htim == NULL || ch->htim->Instance == NULL ||
        !valid_channel(ch->tim_channel) || ch->counter_hz == 0u || us == 0u) {
        return false;
    }
    uint64_t value = ((uint64_t)us * ch->counter_hz + 500000u) / 1000000u;
    /* CCR must be nonzero and strictly shorter than the ARR+1 period. */
    if (value == 0u || value > UINT32_MAX ||
        value > __HAL_TIM_GET_AUTORELOAD(ch->htim)) {
        return false;
    }
    *ticks = (uint32_t)value;
    return true;
}

static bool in_range(const ServoProfile *p, uint16_t us)
{
    return us >= p->pulse_min_us && us <= p->pulse_max_us;
}

static bool valid_profile(const ServoController *c, const ServoProfile *p)
{
    uint32_t ticks;
    if (p->pwm_channel_index >= SERVO_MAX_CHANNELS || p->pulse_min_us == 0u ||
        p->pulse_min_us >= p->pulse_max_us) {
        return false;
    }
    return in_range(p, p->pulse_home_us) && in_range(p, p->pulse_approach_us) &&
           in_range(p, p->pulse_engaged_us) && in_range(p, p->pulse_retract_us) &&
           in_range(p, p->pulse_scan_us) &&
           pulse_ticks(&c->channels[p->pwm_channel_index], p->pulse_min_us, &ticks) &&
           pulse_ticks(&c->channels[p->pwm_channel_index], p->pulse_max_us, &ticks);
}

static bool valid_configuration(const ServoController *c)
{
    bool used[SERVO_MAX_CHANNELS] = {false};
    bool any = false;
    for (uint32_t r = 0; r < SERVO_ROLE_COUNT; ++r) {
        if (!c->profile_configured[r]) {
            continue;
        }
        const ServoProfile *p = &c->profiles[r];
        if (!valid_profile(c, p) || used[p->pwm_channel_index]) {
            return false;
        }
        used[p->pwm_channel_index] = true;
        any = true;
    }
    return any;
}

static void write_compare(ServoController *c, const ServoProfile *p, uint16_t us)
{
    ServoPwmChannel *ch = &c->channels[p->pwm_channel_index];
    uint32_t ticks = 0u;
    /* Caller validated pulse and channel before any writes. */
    (void)pulse_ticks(ch, us, &ticks);
    __HAL_TIM_SET_COMPARE(ch->htim, ch->tim_channel, ticks);
}

void ServoController_Init(ServoController *c, TIM_HandleTypeDef *htim)
{
    if (c == NULL) {
        return;
    }
    memset(c, 0, sizeof(*c));
    c->stopped = true;
    for (uint32_t r = 0; r < SERVO_ROLE_COUNT; ++r) {
        c->profiles[r].pwm_channel_index = r;
    }
    if (htim != NULL) {
        const uint32_t channels[] = {
            TIM_CHANNEL_1, TIM_CHANNEL_2, TIM_CHANNEL_3, TIM_CHANNEL_4
        };
        for (uint32_t i = 0; i < 4u; ++i) {
            (void)ServoController_ConfigChannel(c, i, htim, channels[i], 1000000u);
        }
    }
}

bool ServoController_ConfigChannel(ServoController *c, uint32_t index,
                                   TIM_HandleTypeDef *htim, uint32_t tim_channel,
                                   uint32_t counter_hz)
{
    if (!can_configure(c) || index >= SERVO_MAX_CHANNELS || htim == NULL ||
        htim->Instance == NULL || !valid_channel(tim_channel) || counter_hz == 0u) {
        return false;
    }
    for (uint32_t r = 0; r < SERVO_ROLE_COUNT; ++r) {
        if (c->profile_configured[r] && c->profiles[r].pwm_channel_index == index) {
            return false; /* Bind channels BEFORE enabling their profiles. */
        }
    }
    for (uint32_t i = 0; i < SERVO_MAX_CHANNELS; ++i) {
        const ServoPwmChannel *other = &c->channels[i];
        if (i != index && other->htim != NULL &&
            other->htim->Instance == htim->Instance &&
            (other->tim_channel == tim_channel || other->counter_hz != counter_hz)) {
            return false;
        }
    }
    c->channels[index].htim = htim;
    c->channels[index].tim_channel = tim_channel;
    c->channels[index].counter_hz = counter_hz;
    return true;
}

bool ServoController_ConfigProfile(ServoController *c, ServoRole role,
                                   const ServoProfile *profile)
{
    if (!can_configure(c) || !valid_role(role) || profile == NULL ||
        !valid_profile(c, profile)) {
        return false;
    }
    for (uint32_t r = 0; r < SERVO_ROLE_COUNT; ++r) {
        if (r != (uint32_t)role && c->profile_configured[r] &&
            c->profiles[r].pwm_channel_index == profile->pwm_channel_index) {
            return false;
        }
    }
    c->profiles[role] = *profile;
    c->profiles[role].state = ACTUATOR_STATE_UNKNOWN;
    c->profile_configured[role] = true;
    c->angle_configured[role] = false;
    return true;
}

bool ServoController_ConfigAngles(ServoController *c, ServoRole role,
                                  const ServoAngleCalibration *calibration)
{
    if (!can_configure(c) || !valid_role(role) || calibration == NULL ||
        !c->profile_configured[role]) {
        return false;
    }
    const int16_t *a = calibration->angle_decideg;
    const uint16_t *p = calibration->pulse_us;
    if (a[0] >= a[1] || a[1] >= a[2] || (int32_t)a[2] - a[0] > 2700 ||
        !((p[0] < p[1] && p[1] < p[2]) || (p[0] > p[1] && p[1] > p[2]))) {
        return false;
    }
    for (uint32_t i = 0; i < 3u; ++i) {
        if (!in_range(&c->profiles[role], p[i])) {
            return false;
        }
    }
    c->angles[role] = *calibration;
    c->angle_configured[role] = true;
    return true;
}

bool ServoController_Start(ServoController *c)
{
    if (!can_configure(c) || !valid_configuration(c)) {
        return false;
    }
    /* Preload all compare registers before enabling any output. */
    for (uint32_t r = 0; r < SERVO_ROLE_COUNT; ++r) {
        if (c->profile_configured[r]) {
            write_compare(c, &c->profiles[r], c->profiles[r].pulse_home_us);
        }
    }
    c->stopped = true;
    for (uint32_t r = 0; r < SERVO_ROLE_COUNT; ++r) {
        if (!c->profile_configured[r]) {
            continue;
        }
        ServoPwmChannel *ch = &c->channels[c->profiles[r].pwm_channel_index];
        /* Include the attempted channel in cleanup if HAL fails midway. */
        ch->started = true;
        if (HAL_TIM_PWM_Start(ch->htim, ch->tim_channel) != HAL_OK) {
            for (uint32_t i = 0; i < SERVO_MAX_CHANNELS; ++i) {
                ServoPwmChannel *active = &c->channels[i];
                if (active->started &&
                    HAL_TIM_PWM_Stop(active->htim, active->tim_channel) == HAL_OK) {
                    active->started = false;
                }
            }
            for (uint32_t i = 0; i < SERVO_ROLE_COUNT; ++i) {
                if (c->profile_configured[i]) {
                    c->profiles[i].state = ACTUATOR_STATE_ERROR;
                }
            }
            return false;
        }
    }
    c->started = true;
    c->stopped = false;
    for (uint32_t r = 0; r < SERVO_ROLE_COUNT; ++r) {
        if (c->profile_configured[r]) {
            c->profiles[r].state = ACTUATOR_STATE_HOME;
        }
    }
    return true;
}

bool ServoController_WriteUs(ServoController *c, uint32_t channel_idx,
                             uint16_t pulse_us)
{
    if (c == NULL || !c->started || c->stopped || channel_idx >= SERVO_MAX_CHANNELS ||
        !c->channels[channel_idx].started) {
        return false;
    }
    for (uint32_t r = 0; r < SERVO_ROLE_COUNT; ++r) {
        ServoProfile *p = &c->profiles[r];
        if (c->profile_configured[r] && p->pwm_channel_index == channel_idx) {
            uint32_t ticks;
            if (!in_range(p, pulse_us) ||
                !pulse_ticks(&c->channels[channel_idx], pulse_us, &ticks)) {
                return false;
            }
            write_compare(c, p, pulse_us);
            p->state = ACTUATOR_STATE_MOVING;
            return true;
        }
    }
    return false;
}

bool ServoController_WriteAngle(ServoController *c, ServoRole role,
                                int16_t angle_decideg)
{
    if (c == NULL || !valid_role(role) || !c->profile_configured[role] ||
        !c->angle_configured[role]) {
        return false;
    }
    const ServoAngleCalibration *cal = &c->angles[role];
    if (angle_decideg < cal->angle_decideg[0] ||
        angle_decideg > cal->angle_decideg[2]) {
        return false;
    }
    uint32_t i = angle_decideg <= cal->angle_decideg[1] ? 0u : 1u;
    int32_t span = (int32_t)cal->angle_decideg[i + 1u] - cal->angle_decideg[i];
    int32_t offset = (int32_t)angle_decideg - cal->angle_decideg[i];
    /* Weighted positive numerator also rounds reversed pulse mappings correctly. */
    int64_t numerator = (int64_t)cal->pulse_us[i] * (span - offset) +
                        (int64_t)cal->pulse_us[i + 1u] * offset;
    uint16_t pulse = (uint16_t)((numerator + span / 2) / span);
    return ServoController_WriteUs(c, c->profiles[role].pwm_channel_index, pulse);
}

bool ServoController_WriteRole(ServoController *c, ServoRole role,
                               ServoTarget target)
{
    if (c == NULL || !valid_role(role) || !c->profile_configured[role]) {
        return false;
    }
    ServoProfile *p = &c->profiles[role];
    uint16_t pulse;
    ActuatorState state;
    switch (target) {
    case SERVO_TARGET_HOME:
    case SERVO_TARGET_SAFE:
        pulse = p->pulse_home_us; state = ACTUATOR_STATE_HOME; break;
    case SERVO_TARGET_APPROACH:
        pulse = p->pulse_approach_us; state = ACTUATOR_STATE_MOVING; break;
    case SERVO_TARGET_ENGAGED:
    case SERVO_TARGET_SOLVE:
        pulse = p->pulse_engaged_us; state = ACTUATOR_STATE_ENGAGED; break;
    case SERVO_TARGET_RETRACT:
        pulse = p->pulse_retract_us; state = ACTUATOR_STATE_RETRACTED; break;
    case SERVO_TARGET_SCAN:
        pulse = p->pulse_scan_us; state = ACTUATOR_STATE_MOVING; break;
    default:
        return false;
    }
    if (!ServoController_WriteUs(c, p->pwm_channel_index, pulse)) {
        return false;
    }
    p->state = state;
    return true;
}

ActuatorState ServoController_GetState(const ServoController *c, ServoRole role)
{
    if (c == NULL || !valid_role(role) || !c->profile_configured[role]) {
        return ACTUATOR_STATE_UNKNOWN;
    }
    return c->profiles[role].state;
}

bool ServoController_Home(ServoController *c)
{
    if (c == NULL || !c->started || !valid_configuration(c)) {
        return false;
    }
    for (uint32_t r = 0; r < SERVO_ROLE_COUNT; ++r) {
        if (c->profile_configured[r] &&
            !c->channels[c->profiles[r].pwm_channel_index].started) {
            return false;
        }
    }
    c->stopped = false;
    for (uint32_t r = 0; r < SERVO_ROLE_COUNT; ++r) {
        if (c->profile_configured[r]) {
            write_compare(c, &c->profiles[r], c->profiles[r].pulse_home_us);
            c->profiles[r].state = ACTUATOR_STATE_HOME;
        }
    }
    return true;
}

void ServoController_Stop(ServoController *c)
{
    if (c == NULL) {
        return;
    }
    c->stopped = true;
    for (uint32_t r = 0; r < SERVO_ROLE_COUNT; ++r) {
        if (c->profile_configured[r]) {
            c->profiles[r].state = ACTUATOR_STATE_STOPPED;
        }
    }
}

bool ServoController_Clamp(ServoController *c, ServoRole role, bool close)
{
    if (role != SERVO_ROLE_TOOL_NW && role != SERVO_ROLE_TOOL_NE &&
        role != SERVO_ROLE_TOOL_SW && role != SERVO_ROLE_TOOL_SE) {
        return false;
    }
    return ServoController_WriteRole(c, role,
                                     close ? SERVO_TARGET_ENGAGED : SERVO_TARGET_RETRACT);
}

bool ServoController_TurnFace(ServoController *c, char face, int turns,
                              uint32_t duration_ms)
{
    /* Implement only after the face-to-actuator sequence has been measured. */
    (void)c; (void)face; (void)turns; (void)duration_ms;
    return false;
}

bool ServoController_ScanPose(ServoController *c, char face)
{
    (void)c; (void)face;
    return false;
}

bool ServoRole_FromString(const char *role_str, ServoRole *out)
{
    if (role_str == NULL || out == NULL) {
        return false;
    }
    for (uint32_t i = 0; i < SERVO_ROLE_COUNT; ++i) {
        if (strcmp(role_str, role_names[i]) == 0) {
            *out = (ServoRole)i;
            return true;
        }
    }
    return false;
}

bool ServoTarget_FromString(const char *target_str, ServoTarget *out)
{
    if (target_str == NULL || out == NULL) {
        return false;
    }
    for (uint32_t i = 0; i < sizeof(target_names) / sizeof(target_names[0]); ++i) {
        if (strcmp(target_str, target_names[i]) == 0) {
            *out = (ServoTarget)i;
            return true;
        }
    }
    return false;
}
