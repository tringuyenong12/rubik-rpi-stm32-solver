#ifndef RUBIK_PROTOCOL_H
#define RUBIK_PROTOCOL_H

#include "main.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RUBIK_RX_LINE_SIZE 96

typedef enum {
    RUBIK_CMD_NONE = 0,
    RUBIK_CMD_PING,
    RUBIK_CMD_HOME,
    RUBIK_CMD_STOP,
    RUBIK_CMD_SERVO,
    RUBIK_CMD_MOVE,
    RUBIK_CMD_ACTUATOR,
    RUBIK_CMD_CLAMP,
    RUBIK_CMD_TURN,
    RUBIK_CMD_SCAN_POSE,
    RUBIK_CMD_ERROR
} RubikCommandType;

typedef struct {
    RubikCommandType type;
    char face;
    int turns;
    uint32_t duration_ms;
    uint32_t channel;
    uint16_t pulse_us;
    char role[24];
    char target[24];
    char error[32];
} RubikCommand;

typedef struct {
    UART_HandleTypeDef *huart;
    uint8_t rx_byte;
    char line[RUBIK_RX_LINE_SIZE];
    size_t line_len;
    volatile bool line_ready;
} RubikProtocol;

void RubikProtocol_Init(RubikProtocol *protocol, UART_HandleTypeDef *huart);
void RubikProtocol_StartReceive(RubikProtocol *protocol);
void RubikProtocol_OnRxCplt(RubikProtocol *protocol, UART_HandleTypeDef *huart);
bool RubikProtocol_ReadCommand(RubikProtocol *protocol, RubikCommand *command);
void RubikProtocol_SendLine(RubikProtocol *protocol, const char *line);
void RubikProtocol_SendError(RubikProtocol *protocol, const char *code, const char *message);

#ifdef __cplusplus
}
#endif

#endif

