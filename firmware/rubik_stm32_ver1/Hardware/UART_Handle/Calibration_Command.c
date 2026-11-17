/*
 * Calibration_Command.c
 *
 *  Created on: Nov 15, 2026
 *      Author: Dell
 */

#include "Calibration_Command.h"
#include "../Servo_Control/Servo_Control.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <math.h>

enum { CALIB_UNKNOWN, CALIB_SERVO };
enum { CALIB_SERVO_UNKNOWN, CALIB_SERVO_SET, CALIB_SERVO_ADD, CALIB_SERVO_SUB, CALIB_SERVO_GET };

static bool Calibration_Position(unsigned long id, int position,
        float **angle, float **offset)
{
    if (id <= SERVO_ROTATE_LEFT)
    {
        Servo_Rotate_t *rotate = &servo[id].state.rotate;
        switch (position)
        {
        case SERVO_ROTATE_HOME:
            *angle = &rotate->home_angle;
            *offset = &rotate->offset_calib_home_angle;
            return true;
        case SERVO_ROTATE_CLOCKWISE:
            *angle = &rotate->clockwise_angle;
            *offset = &rotate->offset_calib_clockwise_angle;
            return true;
        case SERVO_ROTATE_ANTICLOCKWISE:
            *angle = &rotate->anticlockwise_angle;
            *offset = &rotate->offset_calib_anticlockwise_angle;
            return true;
        default:
            return false;
        }
    }

    Servo_Move_t *move = &servo[id].state.move;
    switch (position)
    {
    case SERVO_MOVE_FULL_RELEASE:
        *angle = &move->full_release_angle;
        *offset = &move->offset_calib_full_release_angle;
        return true;
    case SERVO_MOVE_HALF_RELEASE:
        *angle = &move->half_release_angle;
        *offset = &move->offset_calib_half_release_angle;
        return true;
    case SERVO_MOVE_CLAMP:
        *angle = &move->clamp_angle;
        *offset = &move->offset_calib_clamp_angle;
        return true;
    case SERVO_MOVE_TIGHT_CLAMP:
        *angle = &move->tight_clamp_angle;
        *offset = &move->offset_calib_tight_clamp_angle;
        return true;
    default:
        return false;
    }
}

/* GET dung ten truong trong Servo_Control.h, khong gui lenh di chuyen. */
static bool Calibration_GetParameter(unsigned long id, const char *field, float *value)
{
    if (strcmp(field, "channel") == 0) { *value = servo[id].channel; return true; }

#define GET_FIELD(state, name) \
    if (strcmp(field, #name) == 0) { *value = state->name; return true; }
    if (id <= SERVO_ROTATE_LEFT)
    {
        Servo_Rotate_t *rotate = &servo[id].state.rotate;
        GET_FIELD(rotate, current_angle);
        GET_FIELD(rotate, target_angle);
        GET_FIELD(rotate, home_angle);
        GET_FIELD(rotate, offset_calib_home_angle);
        GET_FIELD(rotate, clockwise_angle);
        GET_FIELD(rotate, offset_calib_clockwise_angle);
        GET_FIELD(rotate, anticlockwise_angle);
        GET_FIELD(rotate, offset_calib_anticlockwise_angle);
    }
    else
    {
        Servo_Move_t *move = &servo[id].state.move;
        GET_FIELD(move, current_angle);
        GET_FIELD(move, target_angle);
        GET_FIELD(move, full_release_angle);
        GET_FIELD(move, offset_calib_full_release_angle);
        GET_FIELD(move, half_release_angle);
        GET_FIELD(move, offset_calib_half_release_angle);
        GET_FIELD(move, clamp_angle);
        GET_FIELD(move, offset_calib_clamp_angle);
        GET_FIELD(move, tight_clamp_angle);
        GET_FIELD(move, offset_calib_tight_clamp_angle);
    }
#undef GET_FIELD
    return false;
}

/* Khong dung printf float de tuong thich cau hinh newlib-nano cua STM32.
 * Tra goc/offset voi 3 chu so thap phan, giu ca gia tri am. */
static void Calibration_ReplyValue(uint16_t command_id, float value)
{
    if (!isfinite(value) || value < -1000000.0f || value > 1000000.0f)
    { UART_Error(command_id, "LIMIT"); return; }

    long scaled = (long)(value * 1000.0f + (value < 0.0f ? -0.5f : 0.5f));
    unsigned long magnitude = (unsigned long)(scaled < 0 ? -scaled : scaled);
    char number[24];
    snprintf(number, sizeof(number), "%s%lu.%03lu", scaled < 0 ? "-" : "",
            magnitude / 1000UL, magnitude % 1000UL);
    UART_Accept(command_id);
    UART_Reply(command_id, "VALUE", number);
    UART_Done(command_id);
}

// #<ID> CALIB SERVO SET <servo_id> <position> <target_degree>
// #<ID> CALIB SERVO ADD/SUB <servo_id> <position> <offset_degree>
// #<ID> CALIB SERVO GET <servo_id> <position|field_name>
// #<ID> CALIB SERVO GET <servo_id> <position> REAL_ANGLE
// REAL_ANGLE = goc vi tri + offset, khong phai phan hoi do tu servo.
void Calibration_CommandHandler(uint8_t argc, char *argv[], uint16_t command_id)
{
    if (argc < 3U) { UART_Error(command_id, "BAD_ARG"); return; }
    int code = CALIB_UNKNOWN;
    if (strcmp(argv[2], "SERVO") == 0) code = CALIB_SERVO;

    switch (code)
    {
    case CALIB_SERVO:
    {
        if (argc < 4U) { UART_Error(command_id, "BAD_ARG"); return; }
        int operation = CALIB_SERVO_UNKNOWN;
        if (strcmp(argv[3], "SET") == 0) operation = CALIB_SERVO_SET;
        else if (strcmp(argv[3], "ADD") == 0) operation = CALIB_SERVO_ADD;
        else if (strcmp(argv[3], "SUB") == 0) operation = CALIB_SERVO_SUB;
        else if (strcmp(argv[3], "GET") == 0) operation = CALIB_SERVO_GET;

        if (operation == CALIB_SERVO_UNKNOWN)
        { UART_Error(command_id, "UNKNOWN_CMD"); return; }
        if (operation == CALIB_SERVO_GET)
        {
            if (argc != 6U && argc != 7U)
            { UART_Error(command_id, "BAD_ARG"); return; }
            if (argc == 7U && strcmp(argv[6], "REAL_ANGLE") != 0)
            { UART_Error(command_id, "BAD_ARG"); return; }
        }
        else if (argc != 7U)
        { UART_Error(command_id, "BAD_ARG"); return; }

        const char *id_text = argv[4];
        if (*id_text == '\0') { UART_Error(command_id, "BAD_ARG"); return; }
        for (const char *p = id_text; *p != '\0'; p++)
        {
            if (*p < '0' || *p > '9') { UART_Error(command_id, "BAD_ARG"); return; }
        }
        char *end;
        errno = 0;
        unsigned long id = strtoul(id_text, &end, 10);
        if (errno == ERANGE || *end != '\0' || id >= SERVO_COUNT)
        { UART_Error(command_id, "INVALID_POSITION"); return; }

        if (operation == CALIB_SERVO_GET && argc == 6U)
        {
            float value;
            if (Calibration_GetParameter(id, argv[5], &value))
            {
                Calibration_ReplyValue(command_id, value);
                return;
            }
        }

        int position = -1;
        if (id <= SERVO_ROTATE_LEFT)
        {
            if (strcmp(argv[5], "HOME") == 0) position = SERVO_ROTATE_HOME;
            else if (strcmp(argv[5], "CLOCK") == 0) position = SERVO_ROTATE_CLOCKWISE;
            else if (strcmp(argv[5], "ANTI") == 0) position = SERVO_ROTATE_ANTICLOCKWISE;
        }
        else
        {
            if (strcmp(argv[5], "FULL_RELEASE") == 0) position = SERVO_MOVE_FULL_RELEASE;
            else if (strcmp(argv[5], "HALF_RELEASE") == 0) position = SERVO_MOVE_HALF_RELEASE;
            else if (strcmp(argv[5], "CLAMP") == 0) position = SERVO_MOVE_CLAMP;
            else if (strcmp(argv[5], "TIGHT_CLAMP") == 0) position = SERVO_MOVE_TIGHT_CLAMP;
        }
        float *angle, *offset;
        if (!Calibration_Position(id, position, &angle, &offset))
        { UART_Error(command_id, "INVALID_POSITION"); return; }

        if (operation == CALIB_SERVO_GET)
        {
            Calibration_ReplyValue(command_id, *angle + *offset);
            return;
        }

        /* Chi nhan so thap phan theo do, khong nhan hex, NaN hay Inf. */
        const char *number = argv[6];
        const char *p = number;
        if (*p == '+' || *p == '-') p++;
        bool digit = false, dot = false;
        for (; *p != '\0'; p++)
        {
            if (*p >= '0' && *p <= '9') digit = true;
            else if (*p == '.' && !dot) dot = true;
            else { UART_Error(command_id, "BAD_ARG"); return; }
        }
        if (!digit) { UART_Error(command_id, "BAD_ARG"); return; }
        errno = 0;
        float value = strtof(number, &end);
        if (errno == ERANGE || !isfinite(value))
        { UART_Error(command_id, "LIMIT"); return; }
        if (*end != '\0') { UART_Error(command_id, "BAD_ARG"); return; }
        if (value < 0.0f || value > 180.0f)
        { UART_Error(command_id, "LIMIT"); return; }

        float new_offset = *offset;
        switch (operation)
        {
        case CALIB_SERVO_SET: new_offset = value - *angle; break;
        case CALIB_SERVO_ADD: new_offset += value; break;
        case CALIB_SERVO_SUB: new_offset -= value; break;
        default: break;
        }
        float target = *angle + new_offset;
        if (!isfinite(new_offset) || !isfinite(target) || target < 0.0f || target > 180.0f)
        { UART_Error(command_id, "LIMIT"); return; }
        if (servo[id].channel > 15U)
        { UART_Error(command_id, "EXEC_FAILED"); return; }

        UART_Accept(command_id);
        *offset = new_offset;
        /* Servo_Control tu cong offset va cap nhat current_angle/target_angle. */
        bool result;
        if (id <= SERVO_ROTATE_LEFT)
            result = Servo_Rotate((Servo_ID_t)id, (Servo_Rotate_Position_t)position);
        else
            result = Servo_Move((Servo_ID_t)id, (Servo_Move_Position_t)position);
        if (!result) { UART_Error(command_id, "EXEC_FAILED"); return; }
        waitUntilServosDone();
        UART_Done(command_id);
        break;
    }
    default:
        UART_Error(command_id, "UNKNOWN_CMD");
        break;
    }
}
