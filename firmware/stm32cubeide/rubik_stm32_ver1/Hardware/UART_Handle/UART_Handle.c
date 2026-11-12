#include "UART_Handle.h"
#include "../Rubik_Control/Rubik_Control.h"
#include <stdio.h>
#include <string.h>

// ==============================
// UART VARIABLES
// ==============================

static UART_HandleTypeDef *uart_cmd;

static uint8_t rx_byte;

static char rx_buffer[UART_BUFFER_SIZE];
static char cmd_buffer[UART_BUFFER_SIZE];

static uint8_t rx_index = 0;
static bool frame_started = false;

static volatile bool cmd_ready = false;

// ==============================
// UART INITIALIZATION
// ==============================

void UART_Command_Init(UART_HandleTypeDef *huart)
{
    uart_cmd = huart;

    rx_index = 0;
    frame_started = false;
    cmd_ready = false;

    HAL_UART_Receive_IT(uart_cmd, &rx_byte, 1);
}

// ==============================
// UART RECEIVE CALLBACK
// ==============================

void UART_Command_RxCallback(UART_HandleTypeDef *huart)
{
    if (huart != uart_cmd)
        return;

    // Khong nhan lenh moi khi lenh cu chua xu ly
    if (cmd_ready)
    {
        HAL_UART_Receive_IT(uart_cmd, &rx_byte, 1);
        return;
    }

    if (rx_byte == '#')
    {
        rx_index = 0;
        frame_started = true;
    }
    else if (frame_started)
    {
        if (rx_byte == '\n')
        {
            if (rx_index > 0)
            {
                rx_buffer[rx_index] = '\0';

                memcpy(cmd_buffer,
                       rx_buffer,
                       rx_index + 1);

                cmd_ready = true;
            }

            rx_index = 0;
            frame_started = false;
        }
        else if (rx_byte != '\r')
        {
            if (rx_index < UART_BUFFER_SIZE - 1)
            {
                rx_buffer[rx_index++] = rx_byte;
            }
            else
            {
                // Bo khung qua dai
                rx_index = 0;
                frame_started = false;
            }
        }
    }

    HAL_UART_Receive_IT(uart_cmd, &rx_byte, 1);
}

// ==============================
// RUBIK MOVE DISPATCHER
// ==============================

static void Rubik_HandleMove(const char *move)
{
    if (strcmp(move, "L") == 0)
    {
        Rubik_Left();
    }
    else if (strcmp(move, "R") == 0)
    {
        Rubik_Right();
    }
    else if (strcmp(move, "U") == 0)
    {
        Rubik_UpToFront();
    }
    else if (strcmp(move, "D") == 0)
    {
        Rubik_DownToFront();
    }
    else if (strcmp(move, "F") == 0)
    {
        Rubik_Front();
    }
    else if (strcmp(move, "B") == 0)
    {
        Rubik_Back();
    }
    else if (strcmp(move, "L_") == 0)
    {
        Rubik_Left_();
    }
    else if (strcmp(move, "R_") == 0)
    {
        Rubik_Right_();
    }
    else if (strcmp(move, "U_") == 0)
    {
        Rubik_Up_ToFront();
    }
    else if (strcmp(move, "D_") == 0)
    {
        Rubik_Down_ToFront();
    }
    else if (strcmp(move, "F_") == 0)
    {
        Rubik_Front_();
    }
    else if (strcmp(move, "B_") == 0)
    {
        Rubik_Back_();
    }
}

// ==============================
// COMMAND PARSER
// ==============================

static void UART_ParseCommand(const char *command)
{
    unsigned int id;
    char group[16];
    char action[16];
    char param[16];
    char extra;

    int count = sscanf(
        command,
        "%u %15s %15s %15s %c",
        &id,
        group,
        action,
        param,
        &extra
    );

    // Yeu cau dung 4 thanh phan
    if (count != 4)
        return;

    if (strcmp(group, "TEST_RUBIK") == 0)
    {
        if (strcmp(action, "MOVE") == 0)
        {
            Rubik_HandleMove(param);
        }
    }
}

// ==============================
// MAIN LOOP PROCESS
// ==============================

void UART_Command_Process(void)
{
    if (!cmd_ready)
        return;

    // Xu ly lenh, giu cmd_ready = true
    // de ISR khong ghi de buffer.
    UART_ParseCommand(cmd_buffer);

    cmd_ready = false;
}
