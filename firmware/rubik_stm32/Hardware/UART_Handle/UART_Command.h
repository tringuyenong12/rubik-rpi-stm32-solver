#ifndef UART_COMMAND_H_
#define UART_COMMAND_H_

#include <stdbool.h>
#include <stdint.h>

#define UART_MAX_TOKENS 8U
#define UART_MAX_DURATION_MS 60000U

typedef enum
{
    UART_GROUP_UNKNOWN, UART_GROUP_RUBIK, UART_GROUP_CONTROL,
    UART_GROUP_CALIB, UART_GROUP_CONFIG, UART_GROUP_SYSTEM
} UART_Group;

typedef struct
{
    uint16_t id;
    UART_Group group;
    unsigned count;
    char *args[UART_MAX_TOKENS]; /* ACTION and arguments, excludes ID/GROUP. */
} UART_Command;

typedef struct { const char *name; int code; } UART_Keyword;

int UART_FindKeyword(const char *name, const UART_Keyword *keywords, unsigned count);
bool UART_ParseUnsigned(const char *text, uint32_t *value);
const char *UART_ParseCommand(char *line, UART_Command *command);
void UART_DispatchCommand(const UART_Command *command);
int UART_ServoPosition(uint32_t id, const char *name);

void UART_Reply(uint16_t id, const char *status, const char *value);
void UART_ReplyValue(uint16_t id, uint32_t value);
void UART_Accept(uint16_t id);
void UART_Done(uint16_t id);
void UART_Error(uint16_t id, const char *error);
void UART_Command_Stop(uint16_t id);

#endif
