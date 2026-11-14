#include "UART_Command.h"
#include "Rubik_Command.h"
#include "Control_Command.h"
#include "Calibration_Command.h"
#include "Config_Command.h"
#include "System_Command.h"
#include <stddef.h>
#include <string.h>

int UART_FindKeyword(const char *name, const UART_Keyword *keywords, unsigned count)
{
    for (unsigned i = 0; i < count; ++i)
        if (!strcmp(name, keywords[i].name)) return keywords[i].code;
    return -1;
}

bool UART_ParseUnsigned(const char *text, uint32_t *value)
{
    uint32_t number = 0;
    if (!text || !*text) return false;
    while (*text)
    {
        unsigned digit = (unsigned)(*text++ - '0');
        if (digit > 9U || number > (UINT32_MAX - digit) / 10U) return false;
        number = number * 10U + digit;
    }
    *value = number;
    return true;
}

const char *UART_ParseCommand(char *line, UART_Command *command)
{
    char *token;
    uint32_t id;
    static const UART_Keyword groups[] = {
        {"RUBIK", UART_GROUP_RUBIK}, {"CONTROL", UART_GROUP_CONTROL},
        {"CALIB", UART_GROUP_CALIB}, {"CONFIG", UART_GROUP_CONFIG},
        {"SYSTEM", UART_GROUP_SYSTEM}
    };
    *command = (UART_Command){0};
    command->args = &command->argv[2];

    /* RX removes '#'; also accept a complete line when calling the parser directly. */
    if (*line == '#') ++line;
    token = strtok(line, " \t\r\n");
    while (token)
    {
        if (command->argc == UART_MAX_TOKENS + 2U) return "BAD_ARG";
        command->argv[command->argc++] = token;
        token = strtok(NULL, " \t\r\n");
    }

    for (unsigned field = 0; field < command->argc; ++field)
    {
        switch (field)
        {
        case 0: /* argv[0]: request ID */
            if (!UART_ParseUnsigned(command->argv[0], &id) || id > 65535U)
                return "BAD_FORMAT";
            command->id = (uint16_t)id;
            break;
        case 1: /* argv[1]: command group */
        {
            int group = UART_FindKeyword(command->argv[1], groups,
                                        sizeof(groups) / sizeof(groups[0]));
            if (group < 0) return "UNKNOWN_CMD";
            command->group = (UART_Group)group;
            break;
        }
        default: /* argv[2] and later: action and parameters for the handler */
            break;
        }
    }
    if (command->argc < 3U) return "BAD_FORMAT";
    command->count = command->argc - 2U;
    return NULL;
}

void UART_DispatchCommand(const UART_Command *command)
{
    switch (command->group)
    {
    case UART_GROUP_RUBIK: Rubik_CommandHandler(command); break;
    case UART_GROUP_CONTROL: Control_CommandHandler(command); break;
    case UART_GROUP_CALIB: Calibration_CommandHandler(command); break;
    case UART_GROUP_CONFIG: Config_CommandHandler(command); break;
    case UART_GROUP_SYSTEM: System_CommandHandler(command); break;
    default: UART_Error(command->id, "UNKNOWN_CMD"); break;
    }
}

int UART_ServoPosition(uint32_t id, const char *name)
{
    static const UART_Keyword rotate[] = {{"HOME", 0}, {"CLOCK", 1}, {"ANTI", 2}};
    static const UART_Keyword move[] = {
        {"FULL_RELEASE", 0}, {"HALF_RELEASE", 1}, {"CLAMP", 2}, {"TIGHT_CLAMP", 3}
    };
    if (id > 7U) return -1;
    return id < 4U ? UART_FindKeyword(name, rotate, 3U) : UART_FindKeyword(name, move, 4U);
}
