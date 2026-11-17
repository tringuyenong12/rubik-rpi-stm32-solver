/*
 * Control_Command.c
 *
 *  Created on: Nov 15, 2026
 *      Author: Dell
 */


#include "Control_Command.h"
#include "../Servo_Control/Servo_Control.h"
#include <string.h>
#include <stdlib.h>
#include <errno.h>

//#<ID> CONTROL SERVO <servo_id> <position>

enum { CONTROL_UNKNOWN, CONTROL_SERVO };

void Control_CommandHandler(uint8_t argc, char *argv[], uint16_t command_id)
{
    if (argc < 3U)
    {
        UART_Error(command_id, "BAD_ARG");
        return;
    }
    const char *action = argv[2];
    int code = CONTROL_UNKNOWN;
    if (strcmp(action, "SERVO") == 0) code = CONTROL_SERVO;

    switch (code)
    {
    case CONTROL_SERVO:
    {
        if (argc != 5U) { UART_Error(command_id, "BAD_ARG"); return; }

        const char *id_text = argv[3];
        if (*id_text == '\0') { UART_Error(command_id, "BAD_ARG"); return; }
        for (const char *p = id_text; *p != '\0'; p++)
        {
            if (*p < '0' || *p > '9')
            { UART_Error(command_id, "BAD_ARG"); return; }
        }

        char *end;
        errno = 0;
        unsigned long id = strtoul(id_text, &end, 10);
        if (errno == ERANGE || *end != '\0' || id >= SERVO_COUNT)
        { UART_Error(command_id, "INVALID_POSITION"); return; }

        const char *position_text = argv[4];
        int position = -1;
        bool result;

        if (id <= SERVO_ROTATE_LEFT)
        {
            if (strcmp(position_text, "HOME") == 0) position = SERVO_ROTATE_HOME;
            else if (strcmp(position_text, "CLOCK") == 0) position = SERVO_ROTATE_CLOCKWISE;
            else if (strcmp(position_text, "ANTI") == 0) position = SERVO_ROTATE_ANTICLOCKWISE;

            if (position < 0) { UART_Error(command_id, "INVALID_POSITION"); return; }
            UART_Accept(command_id);
            result = Servo_Rotate((Servo_ID_t)id, (Servo_Rotate_Position_t)position);
        }
        else
        {
            if (strcmp(position_text, "FULL_RELEASE") == 0) position = SERVO_MOVE_FULL_RELEASE;
            else if (strcmp(position_text, "HALF_RELEASE") == 0) position = SERVO_MOVE_HALF_RELEASE;
            else if (strcmp(position_text, "CLAMP") == 0) position = SERVO_MOVE_CLAMP;
            else if (strcmp(position_text, "TIGHT_CLAMP") == 0) position = SERVO_MOVE_TIGHT_CLAMP;

            if (position < 0) { UART_Error(command_id, "INVALID_POSITION"); return; }
            UART_Accept(command_id);
            result = Servo_Move((Servo_ID_t)id, (Servo_Move_Position_t)position);
        }

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
