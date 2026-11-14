#include "Config_Command.h"

static volatile uint32_t uart_timeout_ms = 1000U;

void Config_CommandInit(void) { uart_timeout_ms = 1000U; }
uint32_t Config_UartTimeoutMs(void) { return uart_timeout_ms; }

void Config_CommandHandler(const UART_Command *command)
{
    enum { CONFIG_SET, CONFIG_GET, CONFIG_SAVE };
    static const UART_Keyword actions[] = {
        {"SET", CONFIG_SET}, {"GET", CONFIG_GET}, {"SAVE", CONFIG_SAVE}
    };
    static const UART_Keyword variables[] = {{"UART_TIMEOUT_MS", 0}};
    uint32_t value;
    int action = UART_FindKeyword(command->args[0], actions, 3U);
    switch (action)
    {
    case CONFIG_SET:
    case CONFIG_GET:
        if (command->count != (action == CONFIG_GET ? 2U : 3U))
        { UART_Error(command->id, "BAD_ARG"); return; }
        if (UART_FindKeyword(command->args[1], variables, 1U) < 0)
        { UART_Error(command->id, "BAD_ARG"); return; }
        if (action == CONFIG_GET) { UART_ReplyValue(command->id, uart_timeout_ms); return; }
        if (!UART_ParseUnsigned(command->args[2], &value))
        { UART_Error(command->id, "BAD_ARG"); return; }
        if (!value || value > 60000U) { UART_Error(command->id, "LIMIT"); return; }
        uart_timeout_ms = value;
        break;
    case CONFIG_SAVE:
        if (command->count != 1U) { UART_Error(command->id, "BAD_ARG"); return; }
        /* SET already updates RAM. No Flash persistence in this implementation. */
        break;
    default: UART_Error(command->id, "UNKNOWN_CMD"); return;
    }
    UART_Accept(command->id);
    UART_Done(command->id);
}
