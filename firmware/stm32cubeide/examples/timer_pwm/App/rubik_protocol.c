#include "rubik_protocol.h"

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

void RubikProtocol_Init(RubikProtocol *protocol, UART_HandleTypeDef *huart)
{
    memset(protocol, 0, sizeof(*protocol));
    protocol->huart = huart;
}

void RubikProtocol_StartReceive(RubikProtocol *protocol)
{
    HAL_UART_Receive_IT(protocol->huart, &protocol->rx_byte, 1);
}

void RubikProtocol_OnRxCplt(RubikProtocol *protocol, UART_HandleTypeDef *huart)
{
    if (huart != protocol->huart) {
        return;
    }

    if (protocol->line_ready) {
        /* One outstanding request: keep the completed frame immutable. */
    } else if (protocol->rx_byte == '\n' || protocol->rx_byte == '\r') {
        if (protocol->line_len > 0) {
            protocol->line[protocol->line_len] = '\0';
            protocol->line_ready = true;
        }
    } else if (protocol->overflow) {
        /* Discard the rest of this frame, never execute its suffix. */
    } else if (protocol->line_len < RUBIK_RX_LINE_SIZE - 1) {
        protocol->line[protocol->line_len++] = (char)protocol->rx_byte;
    } else {
        protocol->overflow = true;
    }

    HAL_UART_Receive_IT(protocol->huart, &protocol->rx_byte, 1);
}

bool RubikProtocol_ReadCommand(RubikProtocol *protocol, RubikCommand *command)
{
    if (!protocol->line_ready) {
        return false;
    }

    char line[RUBIK_RX_LINE_SIZE];
    bool overflow = protocol->overflow;
    memcpy(line, protocol->line, sizeof(line));
    protocol->line_len = 0;
    protocol->overflow = false;
    protocol->line_ready = false;
    if (overflow) {
        parse_line(line, command);
        command->type = RUBIK_CMD_ERROR;
        strcpy(command->error, "line_too_long");
    } else {
        parse_line(line, command);
    }
    snprintf(protocol->reply_tag, sizeof(protocol->reply_tag), "%s", command->tag);
    return true;
}

void RubikProtocol_SendLine(RubikProtocol *protocol, const char *line)
{
    const char *tag = protocol->reply_tag[0] ? protocol->reply_tag : "?";
    HAL_UART_Transmit(protocol->huart, (uint8_t *)"#", 1, HAL_MAX_DELAY);
    HAL_UART_Transmit(protocol->huart, (uint8_t *)tag, (uint16_t)strlen(tag), HAL_MAX_DELAY);
    HAL_UART_Transmit(protocol->huart, (uint8_t *)" ", 1, HAL_MAX_DELAY);
    HAL_UART_Transmit(protocol->huart, (uint8_t *)line, (uint16_t)strlen(line), HAL_MAX_DELAY);
    HAL_UART_Transmit(protocol->huart, (uint8_t *)"\n", 1, HAL_MAX_DELAY);
}

void RubikProtocol_SendError(RubikProtocol *protocol, const char *code, const char *message)
{
    char buffer[80];
    snprintf(buffer, sizeof(buffer), "NACK %s %s", code, message);
    RubikProtocol_SendLine(protocol, buffer);
}

static void set_error(RubikCommand *command, const char *message)
{
    command->type = RUBIK_CMD_ERROR;
    snprintf(command->error, sizeof(command->error), "%s", message);
}

static void parse_line(char *line, RubikCommand *command)
{
    memset(command, 0, sizeof(*command));

    char *tag = strtok(line, " ");
    if (tag == NULL || tag[0] != '#' || strlen(tag + 1) < 1 ||
        strlen(tag + 1) > 32 ||
        strspn(tag + 1, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") != strlen(tag + 1)) {
        set_error(command, "invalid_tag");
        return;
    }
    strcpy(command->tag, tag + 1);
    char *function = strtok(NULL, " ");
    char *cmd = strtok(NULL, " ");
    if (!valid_identifier(function) || !valid_identifier(cmd)) {
        set_error(command, "invalid_function_operation");
        return;
    }
    strcpy(command->function, function);
    strcpy(command->operation, cmd);
    if (strcmp(function, "RUBIK") != 0) {
        /* Preserve custom arguments for the application's own handler. */
        char *argument;
        while ((argument = strtok(NULL, " ")) != NULL) {
            if (command->arguments[0] != '\0') {
                strcat(command->arguments, " ");
            }
            strcat(command->arguments, argument);
        }
        command->type = RUBIK_CMD_CUSTOM;
        return;
    }

    if (strcmp(cmd, "PING") == 0) {
        if (strtok(NULL, " ") != NULL) {
            set_error(command, "ping_args");
            return;
        }
        command->type = RUBIK_CMD_PING;
        return;
    }

    if (strcmp(cmd, "HOME") == 0) {
        command->type = RUBIK_CMD_HOME;
        return;
    }

    if (strcmp(cmd, "STOP") == 0) {
        command->type = RUBIK_CMD_STOP;
        return;
    }

    if (strcmp(cmd, "SERVO") == 0) {
        char *channel_s = strtok(NULL, " ");
        char *pulse_s = strtok(NULL, " ");
        char *duration_s = strtok(NULL, " ");
        if (channel_s == NULL || pulse_s == NULL || duration_s == NULL) {
            set_error(command, "servo_args");
            return;
        }

        command->type = RUBIK_CMD_SERVO;
        command->channel = (uint32_t)strtoul(channel_s, NULL, 10);
        command->pulse_us = (uint16_t)strtoul(pulse_s, NULL, 10);
        command->duration_ms = (uint32_t)strtoul(duration_s, NULL, 10);
        return;
    }

    if (strcmp(cmd, "MOVE") == 0) {
        char *face_s = strtok(NULL, " ");
        char *turns_s = strtok(NULL, " ");
        char *duration_s = strtok(NULL, " ");
        if (face_s == NULL ||
            !(strlen(face_s) == 1 || (strlen(face_s) == 2 && face_s[1] == '_')) ||
            strchr("URFDLB", face_s[0]) == NULL ||
            (face_s[1] == '_' && turns_s != NULL && strcmp(turns_s, "-1") != 0) ||
            ((turns_s == NULL) != (duration_s == NULL)) || strtok(NULL, " ") != NULL) {
            set_error(command, "move_args");
            return;
        }

        command->type = RUBIK_CMD_MOVE;
        command->face = face_s[0];
        command->turns = turns_s ? atoi(turns_s) : (face_s[1] == '_' ? -1 : 1);
        command->duration_ms = duration_s ? (uint32_t)strtoul(duration_s, NULL, 10) : 450;
        return;
    }

    if (strcmp(cmd, "ACTUATOR") == 0) {
        char *role_s = strtok(NULL, " ");
        char *target_s = strtok(NULL, " ");
        char *duration_s = strtok(NULL, " ");
        if (role_s == NULL || target_s == NULL || duration_s == NULL) {
            set_error(command, "actuator_args");
            return;
        }

        command->type = RUBIK_CMD_ACTUATOR;
        snprintf(command->role, sizeof(command->role), "%s", role_s);
        snprintf(command->target, sizeof(command->target), "%s", target_s);
        command->duration_ms = (uint32_t)strtoul(duration_s, NULL, 10);
        return;
    }

    if (strcmp(cmd, "CLAMP") == 0) {
        char *role_s = strtok(NULL, " ");
        char *target_s = strtok(NULL, " ");
        if (role_s == NULL || target_s == NULL) {
            set_error(command, "clamp_args");
            return;
        }

        command->type = RUBIK_CMD_CLAMP;
        snprintf(command->role, sizeof(command->role), "%s", role_s);
        snprintf(command->target, sizeof(command->target), "%s", target_s);
        return;
    }

    if (strcmp(cmd, "TURN") == 0) {
        char *face_s = strtok(NULL, " ");
        char *turns_s = strtok(NULL, " ");
        char *duration_s = strtok(NULL, " ");
        if (face_s == NULL ||
            !(strlen(face_s) == 1 || (strlen(face_s) == 2 && face_s[1] == '_')) ||
            strchr("URFDLB", face_s[0]) == NULL ||
            (face_s[1] == '_' && turns_s != NULL && strcmp(turns_s, "-1") != 0) ||
            ((turns_s == NULL) != (duration_s == NULL)) || strtok(NULL, " ") != NULL) {
            set_error(command, "turn_args");
            return;
        }

        command->type = RUBIK_CMD_TURN;
        command->face = face_s[0];
        command->turns = turns_s ? atoi(turns_s) : (face_s[1] == '_' ? -1 : 1);
        command->duration_ms = duration_s ? (uint32_t)strtoul(duration_s, NULL, 10) : 450;
        return;
    }

    if (strcmp(cmd, "SCAN_POSE") == 0) {
        char *face_s = strtok(NULL, " ");
        if (face_s == NULL) {
            set_error(command, "scan_pose_args");
            return;
        }

        command->type = RUBIK_CMD_SCAN_POSE;
        command->face = face_s[0];
        return;
    }

    set_error(command, "unknown");
}

