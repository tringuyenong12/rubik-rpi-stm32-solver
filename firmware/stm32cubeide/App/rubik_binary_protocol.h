#ifndef RUBIK_BINARY_PROTOCOL_H
#define RUBIK_BINARY_PROTOCOL_H

#include "main.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RUBIK_UART_COMMAND_SOF 0xA5U
#define RUBIK_UART_RESPONSE_SOF 0x5AU

#define RUBIK_UART_ACK 0x06U
#define RUBIK_UART_DONE 0x44U
#define RUBIK_UART_ERROR 0x15U
#define RUBIK_UART_BUSY 0x42U

typedef struct {
    UART_HandleTypeDef *huart;
    uint8_t rx_byte;
    uint8_t parser_state;
    uint8_t parser_sequence;
    uint8_t parser_command;

    volatile bool command_ready;
    volatile uint8_t pending_sequence;
    volatile uint8_t pending_command;

    volatile bool active;
    volatile uint8_t active_sequence;
    volatile uint8_t active_command;

    volatile bool last_completed_valid;
    volatile uint8_t last_completed_sequence;
    volatile uint8_t last_completed_command;
    volatile bool replay_done_pending;
    volatile uint8_t replay_done_sequence;
} RubikBinaryProtocol;

void RubikBinaryProtocol_Init(RubikBinaryProtocol *protocol, UART_HandleTypeDef *huart);
void RubikBinaryProtocol_StartReceive(RubikBinaryProtocol *protocol);
void RubikBinaryProtocol_OnRxCplt(RubikBinaryProtocol *protocol, UART_HandleTypeDef *huart);
void RubikBinaryProtocol_OnError(RubikBinaryProtocol *protocol, UART_HandleTypeDef *huart);

bool RubikBinaryProtocol_TakeCommand(
    RubikBinaryProtocol *protocol,
    uint8_t *sequence,
    uint8_t *command);
void RubikBinaryProtocol_MarkCompleted(
    RubikBinaryProtocol *protocol,
    uint8_t sequence,
    uint8_t command);
void RubikBinaryProtocol_AbortActive(RubikBinaryProtocol *protocol);
bool RubikBinaryProtocol_TakeDoneReplay(RubikBinaryProtocol *protocol, uint8_t *sequence);
void RubikBinaryProtocol_SendStatus(
    RubikBinaryProtocol *protocol,
    uint8_t sequence,
    uint8_t status);

#ifdef __cplusplus
}
#endif

#endif
