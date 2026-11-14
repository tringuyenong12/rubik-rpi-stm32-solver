#include "System_Command.h"
#include "Calibration_Command.h"

void System_CommandHandler(const UART_Command *command)
{
    enum { SYSTEM_STATUS, SYSTEM_STOP, SYSTEM_VERSION };
    static const UART_Keyword actions[] = {
        {"STATUS", SYSTEM_STATUS}, {"STOP", SYSTEM_STOP}, {"VERSION", SYSTEM_VERSION}
    };
    int action = UART_FindKeyword(command->args[0], actions, 3U);
    if (action < 0) { UART_Error(command->id, "UNKNOWN_CMD"); return; }
    if (command->count != 1U) { UART_Error(command->id, "BAD_ARG"); return; }
    switch (action)
    {
    case SYSTEM_STATUS:
        UART_Reply(command->id, "VALUE", Calibration_IsActive() ? "CALIB" : "IDLE");
        break;
    case SYSTEM_STOP: UART_Command_Stop(command->id); break;
    case SYSTEM_VERSION: UART_Reply(command->id, "VALUE", "UART_1.0"); break;
    }
}
