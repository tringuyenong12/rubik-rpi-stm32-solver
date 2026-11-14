#include "Control_Command.h"
#include "Calibration_Command.h"
#include "../Servo_Control/Servo_Control.h"
#include "stm32f4xx_hal.h"

void Control_CommandHandler(const UART_Command *command)
{
    enum { CONTROL_SERVO };
    static const UART_Keyword actions[] = {{"SERVO", CONTROL_SERVO}};
    uint32_t id;
    int position;
    bool result;
    switch (UART_FindKeyword(command->args[0], actions, 1U))
    {
    case CONTROL_SERVO:
        if (command->count != 3U || !UART_ParseUnsigned(command->args[1], &id))
        { UART_Error(command->id, "BAD_ARG"); return; }
        position = UART_ServoPosition(id, command->args[2]);
        if (position < 0) { UART_Error(command->id, "INVALID_POSITION"); return; }
        UART_Accept(command->id);
        result = id < 4U ? Servo_Rotate((Servo_ID_t)id, (Servo_Rotate_Position_t)position) :
                           Servo_Move((Servo_ID_t)id, (Servo_Move_Position_t)position);
        if (!result) { UART_Error(command->id, "EXEC_FAILED"); return; }
        HAL_Delay(Calibration_SettleMs());
        UART_Done(command->id);
        break;
    default: UART_Error(command->id, "UNKNOWN_CMD"); break;
    }
}
