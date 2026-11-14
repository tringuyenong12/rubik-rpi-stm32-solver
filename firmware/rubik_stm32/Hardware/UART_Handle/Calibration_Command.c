#include "Calibration_Command.h"
#include "../Servo_Control/Servo_Control.h"
#include "../PCA9685/PCA9685.h"
#include <math.h>

/* Only offsets are edited: base angles, channels and runtime positions stay intact. */
static float temporary_offsets[SERVO_COUNT][4];
static uint32_t settle_ms = Delay_Servo_Move;
static uint32_t temporary_settle_ms;
static bool active;

void Calibration_CommandInit(void) { active = false; settle_ms = Delay_Servo_Move; }
bool Calibration_IsActive(void) { return active; }
uint32_t Calibration_SettleMs(void) { return settle_ms; }

static void PositionFields(unsigned id, unsigned position, float **base, float **offset)
{
    if (id < 4U)
    {
        Servo_Rotate_t *s = &servo[id].state.rotate;
        switch (position)
        {
        case 0: *base = &s->home_angle; *offset = &s->offset_calib_home_angle; break;
        case 1: *base = &s->clockwise_angle; *offset = &s->offset_calib_clockwise_angle; break;
        default: *base = &s->anticlockwise_angle; *offset = &s->offset_calib_anticlockwise_angle; break;
        }
    }
    else
    {
        Servo_Move_t *s = &servo[id].state.move;
        switch (position)
        {
        case 0: *base = &s->full_release_angle; *offset = &s->offset_calib_full_release_angle; break;
        case 1: *base = &s->half_release_angle; *offset = &s->offset_calib_half_release_angle; break;
        case 2: *base = &s->clamp_angle; *offset = &s->offset_calib_clamp_angle; break;
        default: *base = &s->tight_clamp_angle; *offset = &s->offset_calib_tight_clamp_angle; break;
        }
    }
}

static void CopyOffsets(bool save)
{
    for (unsigned id = 0; id < SERVO_COUNT; ++id)
        for (unsigned p = 0; p < (id < 4U ? 3U : 4U); ++p)
        {
            float *base, *offset;
            PositionFields(id, p, &base, &offset);
            if (save) *offset = temporary_offsets[id][p];
            else temporary_offsets[id][p] = *offset;
        }
}

static const char *ServoCalibration(const UART_Command *command, bool *read, uint32_t *value)
{
    enum { CAL_SET, CAL_ADD, CAL_SUB, CAL_GET };
    static const UART_Keyword actions[] = {
        {"SET", CAL_SET}, {"ADD", CAL_ADD}, {"SUB", CAL_SUB}, {"GET", CAL_GET}
    };
    uint32_t id, amount;
    int position, action;
    float *base, *offset, angle;
    if (command->count < 2U) return "BAD_ARG";
    action = UART_FindKeyword(command->args[1], actions, 4U);
    if (action < 0) return "UNKNOWN_CMD";
    *read = action == CAL_GET;
    if (command->count != (*read ? 4U : 5U)) return "BAD_ARG";
    if (!UART_ParseUnsigned(command->args[2], &id)) return "BAD_ARG";
    position = UART_ServoPosition(id, command->args[3]);
    if (position < 0) return "INVALID_POSITION";
    PositionFields(id, (unsigned)position, &base, &offset);
    angle = *base + (active ? temporary_offsets[id][position] : *offset);
    if (!isfinite(angle)) return "LIMIT";
    if (angle < 0.0f) angle = 0.0f;
    else if (angle > 180.0f) angle = 180.0f;
    /* Use the same truncation as PCA9685_SetServoAngle. */
    *value = (uint32_t)(angle * (max_pulse - min_pulse) / 180.0 + min_pulse);
    if (*read) return 0;
    if (!active) return "NOT_IN_CALIB_MODE";
    if (!UART_ParseUnsigned(command->args[4], &amount)) return "BAD_ARG";
    switch (action)
    {
    case CAL_SET: *value = amount; break;
    case CAL_ADD:
        if (amount > (uint32_t)max_pulse - *value) return "LIMIT";
        *value += amount;
        break;
    case CAL_SUB:
        if (amount > *value) return "LIMIT";
        *value -= amount;
        break;
    }
    if (*value < (uint32_t)min_pulse || *value > (uint32_t)max_pulse) return "LIMIT";
    /* Aim inside the requested count bin to avoid float truncation to count-1. */
    angle = ((float)*value + 0.25f - min_pulse) * 180.0f / (max_pulse - min_pulse);
    if (angle < 0.0f) angle = 0.0f;
    if (!isfinite(*base)) return "LIMIT";
    temporary_offsets[id][position] = angle - *base;
    return 0; /* No PWM is sent, including on SAVE. */
}

void Calibration_CommandHandler(const UART_Command *command)
{
    enum { CAL_START, CAL_SERVO, CAL_SET, CAL_GET, CAL_SAVE, CAL_RESET, CAL_EXIT };
    static const UART_Keyword actions[] = {
        {"START", CAL_START}, {"SERVO", CAL_SERVO}, {"SET", CAL_SET}, {"GET", CAL_GET},
        {"SAVE", CAL_SAVE}, {"RESET", CAL_RESET}, {"EXIT", CAL_EXIT}
    };
    static const UART_Keyword variables[] = {{"SERVO_SETTLE_MS", 0}};
    bool read = false;
    uint32_t value = 0;
    const char *error = 0;
    int action = UART_FindKeyword(command->args[0], actions, 7U);
    switch (action)
    {
    case CAL_SERVO: error = ServoCalibration(command, &read, &value); break;
    case CAL_SET:
    case CAL_GET:
        read = action == CAL_GET;
        if (command->count != (read ? 2U : 3U)) error = "BAD_ARG";
        else if (UART_FindKeyword(command->args[1], variables, 1U) < 0) error = "BAD_ARG";
        else if (read) value = active ? temporary_settle_ms : settle_ms;
        else if (!active) error = "NOT_IN_CALIB_MODE";
        else if (!UART_ParseUnsigned(command->args[2], &value)) error = "BAD_ARG";
        else if (!value || value > 60000U) error = "LIMIT";
        else temporary_settle_ms = value;
        break;
    case CAL_START:
        if (command->count != 1U) error = "BAD_ARG";
        else if (active) error = "BUSY";
        else { CopyOffsets(false); temporary_settle_ms = settle_ms; active = true; }
        break;
    case CAL_SAVE:
    case CAL_RESET:
    case CAL_EXIT:
        if (command->count != 1U) error = "BAD_ARG";
        else if (!active) error = "NOT_IN_CALIB_MODE";
        else
        {
            if (action == CAL_SAVE) { CopyOffsets(true); settle_ms = temporary_settle_ms; }
            active = false; /* RESET/EXIT discard the temporary values. */
        }
        break;
    default: error = "UNKNOWN_CMD"; break;
    }
    if (error) UART_Error(command->id, error);
    else if (read) UART_ReplyValue(command->id, value);
    else { UART_Accept(command->id); UART_Done(command->id); }
}
