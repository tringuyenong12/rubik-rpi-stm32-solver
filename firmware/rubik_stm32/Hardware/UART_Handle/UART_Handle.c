#include "UART_Handle.h"
#include "UART_Command.h"
#include "Calibration_Command.h"
#include "Config_Command.h"
#include <stdio.h>
#include <string.h>

static UART_HandleTypeDef *uart_cmd;
static uint8_t rx_byte;
static char rx_buffer[UART_BUFFER_SIZE];
static char command_buffer[UART_BUFFER_SIZE];
static unsigned rx_index;
static bool receiving;
static volatile bool command_ready;
static uint32_t last_rx_tick;
#if UART_COMMAND_TRACE
static volatile bool rx_seen;
static volatile uint8_t first_rx_byte;
static bool rx_reported;
#endif

void UART_Command_Init(UART_HandleTypeDef *huart)
{
    uart_cmd = huart;
    rx_index = 0;
    receiving = false;
    command_ready = false;
#if UART_COMMAND_TRACE
    rx_seen = false;
    rx_reported = false;
#endif
    Calibration_CommandInit();
    Config_CommandInit();
    if (uart_cmd) HAL_UART_Receive_IT(uart_cmd, &rx_byte, 1U);
}

void UART_Command_RxCallback(UART_HandleTypeDef *huart)
{
    if (!uart_cmd || huart != uart_cmd) return;

#if UART_COMMAND_TRACE
    if (!rx_seen)
    {
        first_rx_byte = rx_byte;
        rx_seen = true;
    }
#endif

    /* One request at a time. Keep the command buffer unchanged until DONE. */
    if (command_ready || huart->ErrorCode != HAL_UART_ERROR_NONE)
    {
        receiving = false;
        rx_index = 0;
    }
    else
    {
        uint32_t now = HAL_GetTick();
        if (receiving && (uint32_t)(now - last_rx_tick) > Config_UartTimeoutMs())
            receiving = false;
        last_rx_tick = now;

        if (rx_byte == '#')
        {
            rx_index = 0;
            receiving = true;
        }
        else if (receiving && rx_byte == '\n')
        {
            /* Accept both LF and CRLF endings. */
            if (rx_index && rx_buffer[rx_index - 1U] == '\r') --rx_index;
            rx_buffer[rx_index] = '\0';
            memcpy(command_buffer, rx_buffer, rx_index + 1U);
            __DMB();
            command_ready = true;
            receiving = false;
        }
        else if (receiving)
        {
            if (rx_index >= UART_BUFFER_SIZE - 1U || rx_byte == '\0')
                receiving = false; /* Discard the whole line, never a truncated command. */
            else
                rx_buffer[rx_index++] = (char)rx_byte;
        }
    }
    HAL_UART_Receive_IT(uart_cmd, &rx_byte, 1U);
}

void UART_Command_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (!uart_cmd || huart != uart_cmd) return;
    receiving = false;
    rx_index = 0;
    HAL_UART_AbortReceive(uart_cmd);
    HAL_UART_Receive_IT(uart_cmd, &rx_byte, 1U);
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    UART_Command_ErrorCallback(huart);
}

void UART_Reply(uint16_t id, const char *status, const char *value)
{
    char reply[96];
    int length = snprintf(reply, sizeof(reply), "#%u %s%s%s\r\n", (unsigned)id,
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

void UART_Command_Stop(uint16_t id)
{
    /* No queued motion. Retain PWM/clamps; blocking Rubik calls cannot be aborted here. */
    UART_Accept(id);
    UART_Done(id);
}

void UART_Command_Process(void)
{
#if UART_COMMAND_TRACE
    char trace[128];
    int length;
    /* Transmit diagnostics in main, never inside the RX interrupt. */
    if (rx_seen && !rx_reported)
    {
        rx_reported = true;
        length = snprintf(trace, sizeof(trace), "UART RX FIRST=0x%02X\r\n",
                          (unsigned)first_rx_byte);
        HAL_UART_Transmit(uart_cmd, (uint8_t *)trace, (uint16_t)length, 20U);
    }
#endif
    if (!command_ready) return;
    __DMB();
#if UART_COMMAND_TRACE
    length = snprintf(trace, sizeof(trace), "UART LINE=#%s\r\n", command_buffer);
    HAL_UART_Transmit(uart_cmd, (uint8_t *)trace, (uint16_t)length, 20U);
#endif
    UART_Command command;
    const char *error = UART_ParseCommand(command_buffer, &command);
    if (error) {
        
        UART_Error(command.id, error);
    
    }
    else
    {
#if UART_COMMAND_TRACE
        for (unsigned i = 0; i < command.argc; ++i)
        {
            length = snprintf(trace, sizeof(trace), "UART argv[%u]=%s\r\n",
                              i, command.argv[i]);
            HAL_UART_Transmit(uart_cmd, (uint8_t *)trace, (uint16_t)length, 20U);
        }
        length = snprintf(trace, sizeof(trace),
                          "UART PARSE ID=%u GROUP=%u ACTION=%s PARAMS=%u\r\n",
                          (unsigned)command.id, (unsigned)command.group,
                          command.args[0], command.count - 1U);
        HAL_UART_Transmit(uart_cmd, (uint8_t *)trace, (uint16_t)length, 20U);
#endif
        UART_DispatchCommand(&command);
    }
    __DMB();
    command_ready = false;
}

void UART_Handle_Process(void) { UART_Command_Process(); }
