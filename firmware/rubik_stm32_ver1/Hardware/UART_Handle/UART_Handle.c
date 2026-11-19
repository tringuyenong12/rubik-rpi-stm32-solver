#include "UART_Handle.h"
#include "Calibration_Command.h"
#include "Control_Command.h"
#include "Rubik_Command.h"
#include <stdio.h>
#include "../Rubik_Control/Rubik_Control.h"
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


static char *argv_parse[UART_MAX_ARGS];
static uint8_t argc_parse = 0;

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


// static void Rubik_HandleMove(const char *move)
// {
//     if (strcmp(move, "L") == 0)
//     {
//         Rubik_Left();
//     }
//     else if (strcmp(move, "R") == 0)
//     {
//         Rubik_Right();
//     }
//     else if (strcmp(move, "U") == 0)
//     {
//         Rubik_UpToFront();
//     }
//     else if (strcmp(move, "D") == 0)
//     {
//         Rubik_DownToFront();
//     }
//     else if (strcmp(move, "F") == 0)
//     {
//         Rubik_Front();
//     }
//     else if (strcmp(move, "B") == 0)
//     {
//         Rubik_Back();
//     }
//     else if (strcmp(move, "L_") == 0)
//     {
//         Rubik_Left_();
//     }
//     else if (strcmp(move, "R_") == 0)
//     {
//         Rubik_Right_();
//     }
//     else if (strcmp(move, "U_") == 0)
//     {
//         Rubik_Up_ToFront();
//     }
//     else if (strcmp(move, "D_") == 0)
//     {
//         Rubik_Down_ToFront();
//     }
//     else if (strcmp(move, "F_") == 0)
//     {
//         Rubik_Front_();
//     }
//     else if (strcmp(move, "B_") == 0)
//     {
//         Rubik_Back_();
//     }
// }

// ==============================
// COMMAND PARSER
// ==============================

static uint8_t UART_Split_Command(char *str)
{
    uint8_t count = 0;
    char *p = str;

    while (*p != '\0')
    {
        /* Skip spaces */
        while (*p == ' ')
            p++;

        if (*p == '\0')
            break;

        if (count >= UART_MAX_ARGS)
            return 0;

        argv_parse[count++] = p;

        /* Find end of token */
        while (*p != '\0' && *p != ' ')
            p++;

        if (*p == ' ')
        {
            *p = '\0';
            p++;
        }
    }

    return count;
}


/* Kiem tra chuoi so thap phan, sau do dung sscanf nhu yeu cau.
   Khong chap nhan '-1', '+1', '1abc' hay so vuot uint16_t. */
static bool UART_ParseId(const char *text, uint16_t *id)
{
    unsigned int value = 0U;
    const char *p = text;
    if (*p == '\0') return false;

    while (*p != '\0')
    {
        if (*p < '0' || *p > '9') return false;
        ++p;
    }

    /* Gioi han do dai tranh so qua lon khi sscanf. */
    if (strlen(text) > 5U) return false;
    if (sscanf(text, "%u", &value) != 1 || value > UINT16_MAX)
        return false;

    *id = (uint16_t)value;
    return true;
}



UART_Command_t UART_Get_Command(const char *str)
{
    if (str == NULL)
        return CMD_UNKNOWN;

    if (strcmp(str, "RUBIK") == 0)   return CMD_RUBIK;
    if (strcmp(str, "CONTROL") == 0) return CMD_CONTROL;
    if (strcmp(str, "CALIB") == 0)   return CMD_CALIB;
    if (strcmp(str, "CONFIG") == 0)   return CMD_CONFIG;
    if (strcmp(str, "SYSTEM") == 0) return CMD_SYSTEM;
    return CMD_UNKNOWN;
}




static void UART_ParseCommand(char *command)
{

    uint16_t command_id;

    argc_parse = UART_Split_Command(command);

    if (!argc_parse) return;
    if (!UART_ParseId(argv_parse[0], &command_id)) return;

    // Yeu cau dung 4 thanh phan
    if (argc_parse < 2){
        
        UART_Reply(command_id, "BAD ARGC", NULL);
        return;
    }
  
    
    UART_Command_t cmd = UART_Get_Command(argv_parse[1]);

    switch (cmd)
     {
         case CMD_RUBIK:
         {
         	Rubik_CommandHandler(argc_parse, argv_parse, command_id);
            //UART_Reply(command_id, "RUBIK_CMD", NULL);
         	break;
         }

         case CMD_CONTROL:
         {
          	Control_CommandHandler(argc_parse, argv_parse, command_id);
            //UART_Reply(command_id, "CONTROL_CMD", NULL);
             // Xử lý điều khiển từng servo
             break;
         }

         case CMD_CALIB:
         {
          	Calibration_CommandHandler(argc_parse, argv_parse, command_id);
            //UART_Reply(command_id, "CALIB_CMD", NULL);
             // Xử lý điều khiển từng servo
             break;
         }

         case CMD_CONFIG:
         {
          	//Config_CommandHandler(argc_parse, argv_parse, command_id);
            //UART_Reply(command_id, "CONFIG_CMD", NULL);
             // Xử lý điều khiển từng servo
             break;
         }

         case CMD_SYSTEM:
         {
          	//System_CommandHandler(argc_parse, argv_parse, command_id);
            //UART_Reply(command_id, "SYSTEM_CMD", NULL);
             // Xử lý điều khiển từng servo
             break;
         }
         default:
        	UART_Reply(command_id, "UNKNOWN_GROUP", NULL);
         	break;

     }







//    if (strcmp(group, "TEST_RUBIK") == 0)
//    {
//        if (strcmp(action, "MOVE") == 0)
//        {
//            Rubik_HandleMove(param);
//        }
//    UART_Done(id);
//    }
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


void UART_Reply(uint16_t id, const char *status, const char *value)
{
    char reply[96];
    int length = snprintf(reply, sizeof(reply), ">#%u %s%s%s\r\n", (unsigned)id,
                          status, value ? " " : "", value ? value : "");
    HAL_UART_Transmit(uart_cmd, (uint8_t *)reply, (uint16_t)length, 20U);
}

void UART_ReplyValue(uint16_t id, uint32_t value)
{
    char number[11];
    snprintf(number, sizeof(number), "%lu", (unsigned long)value);
    UART_Reply(id, "VALUE", number);
}

void UART_Accept(uint16_t id) { UART_Reply(id, "OK", NULL); }
void UART_Done(uint16_t id) { UART_Reply(id, "DONE", NULL); }
void UART_Error(uint16_t id, const char *error) { UART_Reply(id, "ERR", error); }
void UART_Command_Stop(uint16_t id){

}
