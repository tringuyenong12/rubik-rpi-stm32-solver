/**
 * @file servo_controller.h
 * @brief Positional-servo driver. See SERVO_CONTROLLER_GUIDE.md.
 *
 * Call from one main-loop/task context, not concurrently or from interrupts.
 * Timers: edge-aligned, up-counting PWM mode 1, active high.
 * Commands positions without position feedback or path planning.
 */
#ifndef SERVO_CONTROLLER_H
#define SERVO_CONTROLLER_H

#include "main.h"
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SERVO_MAX_CHANNELS 10u

typedef enum {
    SERVO_ROLE_CARRIAGE_NW = 0,
    SERVO_ROLE_CARRIAGE_NE,
    SERVO_ROLE_CARRIAGE_SW,
    SERVO_ROLE_CARRIAGE_SE,
    SERVO_ROLE_TOOL_NW,
    SERVO_ROLE_TOOL_NE,
    SERVO_ROLE_TOOL_SW,
    SERVO_ROLE_TOOL_SE,
    SERVO_ROLE_CENTER_LIFT,
    SERVO_ROLE_CENTER_ROTATE,
    SERVO_ROLE_COUNT
} ServoRole;

/** Command state, NOT confirmation that the shaft reached a position. */
typedef enum {
    ACTUATOR_STATE_UNKNOWN = 0,
    ACTUATOR_STATE_HOMING,
    ACTUATOR_STATE_HOME,
    ACTUATOR_STATE_MOVING,
    ACTUATOR_STATE_ENGAGED,
    ACTUATOR_STATE_RETRACTED,
    ACTUATOR_STATE_ERROR,
    ACTUATOR_STATE_STOPPED
} ActuatorState;

typedef enum {
    SERVO_TARGET_HOME = 0,
    SERVO_TARGET_APPROACH,
    SERVO_TARGET_ENGAGED,
    SERVO_TARGET_RETRACT,
    SERVO_TARGET_SCAN,
    SERVO_TARGET_SOLVE, /* Alias for ENGAGED. */
    SERVO_TARGET_SAFE   /* Alias for HOME; no collision-free path planning. */
} ServoTarget;

typedef struct {
    uint32_t pwm_channel_index;
    uint16_t pulse_home_us;
    uint16_t pulse_approach_us;
    uint16_t pulse_engaged_us;
    uint16_t pulse_retract_us;
    uint16_t pulse_scan_us;
    uint16_t pulse_min_us;
    uint16_t pulse_max_us;
    ActuatorState state; /* Driver-owned; ignored during configuration. */
} ServoProfile;

/**
 * Three measured points, ordered by angle, in tenths of a degree.
 * Example coordinates: {-900, 0, 900} = {-90, 0, +90} degrees.
 * Pulses must strictly increase OR strictly decrease (reversed mounting).
 * No extrapolation or wrapping; maximum calibrated span is 270 degrees.
 * HOME uses profile.pulse_home_us independently of these coordinates.
 */
typedef struct {
    int16_t angle_decideg[3];
    uint16_t pulse_us[3];
} ServoAngleCalibration;

typedef struct {
    TIM_HandleTypeDef *htim;
    uint32_t tim_channel;
    uint32_t counter_hz; /* Actual counter rate AFTER the prescaler. */
    bool started;
} ServoPwmChannel;

/** Treat fields as read-only after Init; configure through the APIs. */
typedef struct {
    ServoPwmChannel channels[SERVO_MAX_CHANNELS];
    ServoProfile profiles[SERVO_ROLE_COUNT];
    ServoAngleCalibration angles[SERVO_ROLE_COUNT];
    bool profile_configured[SERVO_ROLE_COUNT];
    bool angle_configured[SERVO_ROLE_COUNT];
    bool started;
    bool stopped;
} ServoController;

/**
 * Software initialization only; does not move servos.
 * Non-NULL htim binds indices 0..3 to CH1..4 at 1 MHz counter rate.
 * Pass NULL for fully explicit binding. No role is enabled by default.
 * Do not reinitialize an instance whose PWM outputs are running.
 */
void ServoController_Init(ServoController *controller, TIM_HandleTypeDef *htim);

/** Before Start: bind a unique timer/channel. Reject duplicate physical outputs. */
bool ServoController_ConfigChannel(ServoController *controller, uint32_t index,
                                   TIM_HandleTypeDef *htim, uint32_t tim_channel,
                                   uint32_t counter_hz);
/**
 * Before Start: validate and copy measured limits/targets, enabling this role.
 * Each role must own a unique, bound channel. Replacing a profile clears its
 * angle calibration. Failure leaves the previous configuration unchanged.
 */
bool ServoController_ConfigProfile(ServoController *controller, ServoRole role,
                                   const ServoProfile *profile);
/** Before Start: install three measured points within profile limits. */
bool ServoController_ConfigAngles(ServoController *controller, ServoRole role,
                                  const ServoAngleCalibration *calibration);
/**
 * Validate enabled profiles, load HOME compare values, then start PWM.
 * False if no roles are configured or HAL fails. No delays or motion feedback.
 * Use Home, not Start, to recover from a software Stop after successful Start.
 */
bool ServoController_Start(ServoController *controller);

/** Reject inactive/stopped channels or out-of-range pulses; never clamp. */
bool ServoController_WriteUs(ServoController *controller, uint32_t channel_idx,
                             uint16_t pulse_us);
/** Piecewise linear interpolation of measured points, rounded to 1 us. */
bool ServoController_WriteAngle(ServoController *controller, ServoRole role,
                                int16_t angle_decideg);
/** Write a named target without waiting for physical motion. */
bool ServoController_WriteRole(ServoController *controller, ServoRole role,
                               ServoTarget target);
ActuatorState ServoController_GetState(const ServoController *controller,
                                       ServoRole role);
/**
 * Requires successful Start. Validate active roles, clear Stop, command HOME.
 * All active roles move together; caller is responsible for a safe path.
 */
bool ServoController_Home(ServoController *controller);
/**
 * Block writes, retain PWM at the LAST COMMANDED target. A servo may still finish
 * moving to that target. NOT an emergency stop or measured-position hold.
 * Home resumes commands. Servo power is not cut.
 */
void ServoController_Stop(ServoController *controller);
/** TOOL roles only: close -> ENGAGED; open -> RETRACT. */
bool ServoController_Clamp(ServoController *controller, ServoRole role, bool close);

/** Mechanical sequence not implemented: return false, never fake success. */
bool ServoController_TurnFace(ServoController *controller, char face, int turns,
                              uint32_t duration_ms);
static inline bool ServoController_MoveFace(ServoController *controller,
                                            char face, int turns,
                                            uint32_t duration_ms)
{
    return ServoController_TurnFace(controller, face, turns, duration_ms);
}
/** Mechanical sequence not implemented: return false. */
bool ServoController_ScanPose(ServoController *controller, char face);

bool ServoRole_FromString(const char *role_str, ServoRole *out);
bool ServoTarget_FromString(const char *target_str, ServoTarget *out);

#ifdef __cplusplus
}
#endif
#endif /* SERVO_CONTROLLER_H */
