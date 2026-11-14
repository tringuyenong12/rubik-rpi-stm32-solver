#include "Rubik_Command.h"
#include "../Rubik_Control/Rubik_Control.h"

static const char *RubikMove(const UART_Command *command)
{
    enum { MOVE_U, MOVE_D, MOVE_L, MOVE_R, MOVE_F, MOVE_B,
           MOVE_U_INV, MOVE_D_INV, MOVE_L_INV, MOVE_R_INV, MOVE_F_INV, MOVE_B_INV };
    static const UART_Keyword faces[] = {
        {"U", MOVE_U}, {"D", MOVE_D}, {"L", MOVE_L}, {"R", MOVE_R},
        {"F", MOVE_F}, {"B", MOVE_B}, {"U_", MOVE_U_INV}, {"D_", MOVE_D_INV},
        {"L_", MOVE_L_INV}, {"R_", MOVE_R_INV}, {"F_", MOVE_F_INV}, {"B_", MOVE_B_INV}
    };
    uint32_t duration;
    if (command->count != 3U) return "BAD_ARG";
    int face = UART_FindKeyword(command->args[1], faces, 12U);
    if (face < 0 || !UART_ParseUnsigned(command->args[2], &duration)) return "BAD_ARG";
    if (!duration || duration > UART_MAX_DURATION_MS) return "LIMIT";
    /* Rubik_Down_ToFront() is empty in the current library. Do not report success. */
    if (face == MOVE_D_INV) return "NOT_IMPLEMENTED";
    UART_Accept(command->id);
    /* duration is validated only; Rubik_Control currently uses fixed delays. */
    switch (face)
    {
    case MOVE_U: Rubik_UpToFront(); break;
    case MOVE_D: Rubik_DownToFront(); break;
    case MOVE_L: Rubik_Left(); break;
    case MOVE_R: Rubik_Right(); break;
    case MOVE_F: Rubik_Front(); break;
    case MOVE_B: Rubik_Back(); break;
    case MOVE_U_INV: Rubik_Up_ToFront(); break;
    case MOVE_L_INV: Rubik_Left_(); break;
    case MOVE_R_INV: Rubik_Right_(); break;
    case MOVE_F_INV: Rubik_Front_(); break;
    case MOVE_B_INV: Rubik_Back_(); break;
    }
    UART_Done(command->id);
    return 0;
}

void Rubik_CommandHandler(const UART_Command *command)
{
    enum { RUBIK_PING, RUBIK_RESET, RUBIK_MOVE, RUBIK_STOP };
    static const UART_Keyword actions[] = {
        {"PING", RUBIK_PING}, {"RESET", RUBIK_RESET},
        {"MOVE", RUBIK_MOVE}, {"STOP", RUBIK_STOP}
    };
    const char *error;
    int action = UART_FindKeyword(command->args[0], actions, 4U);
    if (action < 0) { UART_Error(command->id, "UNKNOWN_CMD"); return; }
    if (action != RUBIK_MOVE && command->count != 1U)
    { UART_Error(command->id, "BAD_ARG"); return; }
    switch (action)
    {
    case RUBIK_PING: UART_Accept(command->id); UART_Done(command->id); break;
    case RUBIK_RESET:
        UART_Accept(command->id);
        Rubik_Hold_Start_Position();
        UART_Done(command->id);
        break;
    case RUBIK_MOVE:
        error = RubikMove(command);
        if (error) UART_Error(command->id, error);
        break;
    case RUBIK_STOP: UART_Command_Stop(command->id); break;
    }
}
