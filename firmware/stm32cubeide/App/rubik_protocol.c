#include "rubik_protocol.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void parse_line(char *line, RubikCommand *command);

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

    if (protocol->rx_byte == '\n' || protocol->rx_byte == '\r') {
        if (protocol->line_len > 0) {
            protocol->line[protocol->line_len] = '\0';
            protocol->line_ready = true;
        }
    } else if (protocol->line_len < RUBIK_RX_LINE_SIZE - 1) {
        protocol->line[protocol->line_len++] = (char)protocol->rx_byte;
    } else {
        protocol->line_len = 0;
        protocol->line[0] = '\0';
        RubikProtocol_SendError(protocol, "BAD_CMD", "line_too_long");
    }

    HAL_UART_Receive_IT(protocol->huart, &protocol->rx_byte, 1);
}

bool RubikProtocol_ReadCommand(RubikProtocol *protocol, RubikCommand *command)
{
    if (!protocol->line_ready) {
        return false;
    }

    protocol->line_ready = false;
    parse_line(protocol->line, command);
    protocol->line_len = 0;
    memset(protocol->line, 0, sizeof(protocol->line));
    return true;
}

void RubikProtocol_SendLine(RubikProtocol *protocol, const char *line)
{
    HAL_UART_Transmit(protocol->huart, (uint8_t *)line, (uint16_t)strlen(line), HAL_MAX_DELAY);
    HAL_UART_Transmit(protocol->huart, (uint8_t *)"\n", 1, HAL_MAX_DELAY);
}

void RubikProtocol_SendError(RubikProtocol *protocol, const char *code, const char *message)
{
    char buffer[80];
    snprintf(buffer, sizeof(buffer), "ERR %s %s", code, message);
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

    char *cmd = strtok(line, " ");
    if (cmd == NULL) {
        set_error(command, "empty");
        return;
    }

    if (strcmp(cmd, "PING") == 0) {
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
        if (face_s == NULL || turns_s == NULL || duration_s == NULL) {
            set_error(command, "move_args");
            return;
        }

        command->type = RUBIK_CMD_MOVE;
        command->face = face_s[0];
        command->turns = atoi(turns_s);
        command->duration_ms = (uint32_t)strtoul(duration_s, NULL, 10);
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
        if (face_s == NULL || turns_s == NULL || duration_s == NULL) {
            set_error(command, "turn_args");
            return;
        }

        command->type = RUBIK_CMD_TURN;
        command->face = face_s[0];
        command->turns = atoi(turns_s);
        command->duration_ms = (uint32_t)strtoul(duration_s, NULL, 10);
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

