#include "rubik_binary_protocol.h"

#include <string.h>

enum {
    WAIT_SOF = 0,
    WAIT_SEQUENCE,
    WAIT_COMMAND,
    WAIT_CRC,
};

static uint8_t crc8_pair(uint8_t first, uint8_t second)
{
    uint8_t crc = 0;
    const uint8_t values[2] = {first, second};

    for (uint32_t i = 0; i < 2; ++i) {
        crc ^= values[i];
        for (uint32_t bit = 0; bit < 8; ++bit) {
            crc = (crc & 0x80U) ? (uint8_t)((crc << 1U) ^ 0x07U)
                                 : (uint8_t)(crc << 1U);
        }
    }
    return crc;
}

static void accept_frame(RubikBinaryProtocol *protocol, uint8_t sequence, uint8_t command)
{
    /* A retransmission while a servo move is running is intentionally
     * discarded.  The original DONE will still be sent after that move. */
    if (protocol->active && sequence == protocol->active_sequence &&
        command == protocol->active_command) {
        return;
    }

    /* If Raspberry Pi missed DONE and retries after the move completed,
     * request a replay of DONE rather than executing the move twice. */
    if (protocol->last_completed_valid &&
        sequence == protocol->last_completed_sequence &&
        command == protocol->last_completed_command) {
        protocol->replay_done_sequence = sequence;
        protocol->replay_done_pending = true;
        return;
    }

    /* Raspberry Pi sends one command only after DONE.  A second unrelated
     * command while one is pending is dropped instead of overflowing memory. */
    if (!protocol->command_ready && !protocol->active) {
        protocol->pending_sequence = sequence;
        protocol->pending_command = command;
        protocol->command_ready = true;
    }
}

void RubikBinaryProtocol_Init(RubikBinaryProtocol *protocol, UART_HandleTypeDef *huart)
{
    memset(protocol, 0, sizeof(*protocol));
    protocol->huart = huart;
    protocol->parser_state = WAIT_SOF;
}

void RubikBinaryProtocol_StartReceive(RubikBinaryProtocol *protocol)
{
    HAL_UART_Receive_IT(protocol->huart, &protocol->rx_byte, 1);
}

void RubikBinaryProtocol_OnRxCplt(RubikBinaryProtocol *protocol, UART_HandleTypeDef *huart)
{
    if (huart != protocol->huart) {
        return;
    }

    const uint8_t value = protocol->rx_byte;
    switch (protocol->parser_state) {
    case WAIT_SOF:
        if (value == RUBIK_UART_COMMAND_SOF) {
            protocol->parser_state = WAIT_SEQUENCE;
        }
        break;

    case WAIT_SEQUENCE:
        protocol->parser_sequence = value;
        protocol->parser_state = WAIT_COMMAND;
        break;

    case WAIT_COMMAND:
        protocol->parser_command = value;
        protocol->parser_state = WAIT_CRC;
        break;

    case WAIT_CRC:
        if (value == crc8_pair(protocol->parser_sequence, protocol->parser_command)) {
            accept_frame(protocol, protocol->parser_sequence, protocol->parser_command);
        }
        protocol->parser_state = WAIT_SOF;
        break;

    default:
        protocol->parser_state = WAIT_SOF;
        break;
    }

    HAL_UART_Receive_IT(protocol->huart, &protocol->rx_byte, 1);
}

void RubikBinaryProtocol_OnError(RubikBinaryProtocol *protocol, UART_HandleTypeDef *huart)
{
    if (huart != protocol->huart) {
        return;
    }

    protocol->parser_state = WAIT_SOF;
    /* Cube HAL returns the UART receiver to READY before ErrorCallback.
     * Rearming here recovers automatically from a noise/overrun error. */
    HAL_UART_Receive_IT(protocol->huart, &protocol->rx_byte, 1);
}

bool RubikBinaryProtocol_TakeCommand(
    RubikBinaryProtocol *protocol,
    uint8_t *sequence,
    uint8_t *command)
{
    if (!protocol->command_ready) {
        return false;
    }

    *sequence = protocol->pending_sequence;
    *command = protocol->pending_command;
    protocol->command_ready = false;
    protocol->active_sequence = *sequence;
    protocol->active_command = *command;
    protocol->active = true;
    return true;
}

void RubikBinaryProtocol_MarkCompleted(
    RubikBinaryProtocol *protocol,
    uint8_t sequence,
    uint8_t command)
{
    protocol->last_completed_sequence = sequence;
    protocol->last_completed_command = command;
    protocol->last_completed_valid = true;
    protocol->active = false;
}

void RubikBinaryProtocol_AbortActive(RubikBinaryProtocol *protocol)
{
    /* Do not cache an unsuccessful command as DONE.  A caller can correct
     * calibration/configuration and submit it again with a new sequence. */
    protocol->active = false;
}

bool RubikBinaryProtocol_TakeDoneReplay(RubikBinaryProtocol *protocol, uint8_t *sequence)
{
    if (!protocol->replay_done_pending) {
        return false;
    }

    *sequence = protocol->replay_done_sequence;
    protocol->replay_done_pending = false;
    return true;
}

void RubikBinaryProtocol_SendStatus(
    RubikBinaryProtocol *protocol,
    uint8_t sequence,
    uint8_t status)
{
    uint8_t frame[4] = {
        RUBIK_UART_RESPONSE_SOF,
        sequence,
        status,
        crc8_pair(sequence, status),
    };
    HAL_UART_Transmit(protocol->huart, frame, sizeof(frame), 100U);
}
