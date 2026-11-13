#include "rubik_protocol.h"
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void parse_line(char *line, RubikCommand *command);

static bool valid_identifier(const char *value)
{
    const char *letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_";
    const char *characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789";
    return value != NULL && value[0] != '\0' && strlen(value) <= 24 &&
           strchr(letters, value[0]) != NULL && strspn(value, characters) == strlen(value);
}

static bool parse_unsigned(const char *value, uint32_t maximum, uint32_t *result)
{
    if (value == NULL || value[0] == '\0' ||
        strspn(value, "0123456789") != strlen(value)) {
        return false;
    }
    errno = 0;
    unsigned long number = strtoul(value, NULL, 10);
    if (errno == ERANGE || number > maximum) {
        return false;
    }
    *result = (uint32_t)number;
    return true;
}

static void set_error(RubikCommand *command, const char *message)
{
    command->type = RUBIK_CMD_ERROR;
    snprintf(command->error, sizeof(command->error), "%s", message);
}

static bool parse_angle(const char *value, float *angle)
{
    if (value == NULL || value[0] == '\0' ||
        strspn(value, "0123456789.") != strlen(value)) {
        return false;
    }
    char *end;
    errno = 0;
    float number = strtof(value, &end);
    if (end == value || *end != '\0' || errno == ERANGE ||
        !isfinite(number) || number < 0.0f || number > 180.0f) {
        return false;
    }
    *angle = number;
    return true;
}

void RubikProtocol_Init(RubikProtocol *protocol, UART_HandleTypeDef *huart)
{
    memset(protocol, 0, sizeof(*protocol));
    protocol->huart = huart;
}

void RubikProtocol_StartReceive(RubikProtocol *protocol)
{
    if (protocol->huart != NULL) {
        protocol->receive_retry = HAL_UART_Receive_IT(
            protocol->huart, &protocol->rx_byte, 1) != HAL_OK;
    }
}

void RubikProtocol_OnRxCplt(RubikProtocol *protocol, UART_HandleTypeDef *huart)
{
    if (huart == NULL || huart != protocol->huart) {
        return;
    }
    uint8_t byte = protocol->rx_byte;
    bool newline = byte == '\n' || byte == '\r';
    if (protocol->line_ready) {
        /* Preserve the pending frame; drop any following frame in full. */
        protocol->discard_line = !newline;
    } else if (protocol->discard_line) {
        if (newline) {
            protocol->discard_line = false;
        }
    } else if (newline) {
        if (protocol->line_len > 0 || protocol->invalid) {
            protocol->line[protocol->line_len] = '\0';
            __DMB();
            protocol->line_ready = true;
        }
    } else if (byte != '\t' && (byte < 32 || byte > 126)) {
        protocol->invalid = true;
    } else if (protocol->line_len < RUBIK_RX_LINE_SIZE - 1) {
        protocol->line[protocol->line_len++] = (char)byte;
    } else {
        protocol->overflow = true;
    }
    RubikProtocol_StartReceive(protocol);
}

bool RubikProtocol_ReadCommand(RubikProtocol *protocol, RubikCommand *command)
{
    if (!protocol->line_ready) {
        return false;
    }
    char line[RUBIK_RX_LINE_SIZE];
    uint32_t interrupt_state = __get_PRIMASK();
    __disable_irq();
    bool overflow = protocol->overflow;
    bool invalid = protocol->invalid;
    memcpy(line, protocol->line, sizeof(line));
    protocol->line_len = 0;
    protocol->overflow = false;
    protocol->invalid = false;
    __DMB();
    protocol->line_ready = false;
    __set_PRIMASK(interrupt_state);
    parse_line(line, command);
    if (overflow) {
        set_error(command, "line_too_long");
    } else if (invalid) {
        set_error(command, "invalid_character");
    }
    snprintf(protocol->reply_tag, sizeof(protocol->reply_tag), "%s", command->tag);
    return true;
}

bool RubikProtocol_SendLine(RubikProtocol *protocol, const char *line)
{
    char frame[128];
    const char *tag = protocol->reply_tag[0] ? protocol->reply_tag : "?";
    int size = snprintf(frame, sizeof(frame), "#%s %s\n", tag, line);
    if (protocol->huart == NULL || size < 0 || (size_t)size >= sizeof(frame)) {
        return false;
    }
    return HAL_UART_Transmit(protocol->huart, (uint8_t *)frame,
                             (uint16_t)size, 100) == HAL_OK;
}

void RubikProtocol_SendError(RubikProtocol *protocol, const char *code, const char *message)
{
    char buffer[80];
    snprintf(buffer, sizeof(buffer), "NACK %s %s", code, message);
    RubikProtocol_SendLine(protocol, buffer);
}

static void parse_line(char *line, RubikCommand *command)
{
    memset(command, 0, sizeof(*command));
    char *tag = strtok(line, " \t");
    if (tag == NULL || tag[0] != '#' || strlen(tag + 1) < 1 || strlen(tag + 1) > 32 ||
        strspn(tag + 1, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") != strlen(tag + 1)) {
        set_error(command, "invalid_tag");
        return;
    }
    strcpy(command->tag, tag + 1);
    char *function = strtok(NULL, " \t");
    char *operation = strtok(NULL, " \t");
    if (!valid_identifier(function) || !valid_identifier(operation)) {
        set_error(command, "invalid_function_operation");
        return;
    }
    strcpy(command->function, function);
    strcpy(command->operation, operation);
    bool legacy_move = strcmp(function, "TEST_RUBIK") == 0 && strcmp(operation, "MOVE") == 0;
    bool calibration = strcmp(function, "CALIB") == 0;
    if (strcmp(function, "RUBIK") != 0 && !legacy_move && !calibration) {
        char *argument;
        while ((argument = strtok(NULL, " \t")) != NULL) {
            if (command->arguments[0] != '\0') {
                strcat(command->arguments, " ");
            }
            strcat(command->arguments, argument);
        }
        command->type = RUBIK_CMD_CUSTOM;
        return;
    }
    char *first = strtok(NULL, " \t");
    if (!calibration && (strcmp(operation, "PING") == 0 || strcmp(operation, "HOME") == 0 ||
        strcmp(operation, "STOP") == 0)) {
        if (first != NULL) {
            set_error(command, "unexpected_arguments");
        } else if (strcmp(operation, "PING") == 0) {
            command->type = RUBIK_CMD_PING;
        } else if (strcmp(operation, "HOME") == 0) {
            command->type = RUBIK_CMD_HOME;
        } else {
            command->type = RUBIK_CMD_STOP;
        }
        return;
    }
    char *second = strtok(NULL, " \t");
    char *third = strtok(NULL, " \t");
    char *extra = strtok(NULL, " \t");
    if (calibration && (strcmp(operation, "SET") == 0 || strcmp(operation, "TEST") == 0)) {
        if (extra != NULL || !parse_unsigned(first, 7, &command->servo_id) ||
            second == NULL || strlen(second) >= sizeof(command->target)) {
            set_error(command, "calib_args");
            return;
        }
        strcpy(command->target, second);
        if (strcmp(operation, "SET") == 0) {
            if (!parse_angle(third, &command->angle_deg)) {
                set_error(command, "calib_angle");
                return;
            }
            command->type = CALIB_CMD_SET;
        } else {
            if (!parse_unsigned(third, 60000, &command->duration_ms)) {
                set_error(command, "calib_duration");
                return;
            }
            command->type = CALIB_CMD_TEST;
        }
        return;
    }
    if (calibration && strcmp(operation, "SERVO") != 0 && strcmp(operation, "servo") != 0) {
        command->type = RUBIK_CMD_CUSTOM;
        return;
    }
    if (strcmp(operation, "MOVE") == 0 || strcmp(operation, "TURN") == 0) {
        if (first == NULL || first[0] == '\0' || strchr("URFDLB", first[0]) == NULL ||
            !(strlen(first) == 1 || (strlen(first) == 2 && first[1] == '_')) ||
            ((second == NULL) != (third == NULL)) || extra != NULL) {
            set_error(command, "move_args");
            return;
        }
        command->face = first[0];
        command->turns = first[1] == '_' ? -1 : 1;
        command->duration_ms = 450;
        if (second != NULL) {
            if ((strcmp(second, "1") != 0 && strcmp(second, "-1") != 0 &&
                 strcmp(second, "2") != 0) ||
                (first[1] == '_' && strcmp(second, "-1") != 0) ||
                !parse_unsigned(third, 60000, &command->duration_ms)) {
                set_error(command, "move_args");
                return;
            }
            command->turns = atoi(second);
        }
        command->type = strcmp(operation, "MOVE") == 0 ? RUBIK_CMD_MOVE : RUBIK_CMD_TURN;
        return;
    }
    if (strcmp(operation, "SERVO") == 0 || (calibration && strcmp(operation, "servo") == 0)) {
        uint32_t pulse;
        if (extra != NULL || !parse_unsigned(first, 15, &command->channel) ||
            !parse_unsigned(second, 2500, &pulse) || pulse < 500 ||
            !parse_unsigned(third, 60000, &command->duration_ms)) {
            set_error(command, "servo_args");
            return;
        }
        command->pulse_us = (uint16_t)pulse;
        command->type = RUBIK_CMD_SERVO;
    } else if (strcmp(operation, "ACTUATOR") == 0) {
        command->type = RUBIK_CMD_ACTUATOR;
    } else if (strcmp(operation, "CLAMP") == 0) {
        command->type = RUBIK_CMD_CLAMP;
    } else if (strcmp(operation, "SCAN_POSE") == 0) {
        command->type = RUBIK_CMD_SCAN_POSE;
    } else {
        set_error(command, "unknown_operation");
    }
}
