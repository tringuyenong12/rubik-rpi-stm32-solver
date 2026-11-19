/* Replay Auto Solve through the real serial parser and motion handler. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "UART_Handle.h"
#include "../Hardware/Rubik_Control/Rubik_Control.h"

Servo_t servo[SERVO_COUNT];
static UART_HandleTypeDef uart;
static uint8_t *rx;
static char replies[192];
static unsigned front_turns;

HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *handle, uint8_t *data, uint16_t size)
{
    assert(handle == &uart && size == 1);
    rx = data;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *handle, uint8_t *data, uint16_t size, uint32_t timeout)
{
    assert(handle == &uart && timeout > 0 && strlen(replies) + size < sizeof(replies));
    strncat(replies, (const char *)data, size);
    return HAL_OK;
}

void Control_CommandHandler(uint8_t argc, char *argv[], uint16_t id)
{ (void)argc; (void)argv; (void)id; assert(0); }
void Calibration_CommandHandler(uint8_t argc, char *argv[], uint16_t id)
{ (void)argc; (void)argv; (void)id; assert(0); }
bool Servo_Move(Servo_ID_t id, Servo_Move_Position_t position)
{ (void)id; (void)position; return true; }
bool Servo_Rotate(Servo_ID_t id, Servo_Rotate_Position_t position)
{
    if (id == SERVO_ROTATE_FRONT && position == SERVO_ROTATE_CLOCKWISE)
        ++front_turns;
    return true;
}
bool waitUntilServosDone(void) { return true; }
void HAL_Delay(uint32_t ms) { (void)ms; }

static void feed(const char *frame)
{
    replies[0] = '\0';
    for (; *frame; ++frame) {
        *rx = (uint8_t)*frame;
        UART_Command_RxCallback(&uart);
    }
    UART_Command_Process();
}

int main(void)
{
    const char *commands[] = {
        "PING", "SCAN_BEGIN", "SCAN_POSE R", "SCAN_POSE F", "SCAN_POSE D",
        "SCAN_POSE L", "SCAN_POSE B", "SCAN_POSE U", "MOVE F",
    };
    UART_Command_Init(&uart);
    for (unsigned i = 0; i < sizeof(commands) / sizeof(commands[0]); ++i) {
        char frame[64], expected[64];
        unsigned id = i + 1;
        snprintf(frame, sizeof(frame), "#%u RUBIK %s\n", id, commands[i]);
        snprintf(expected, sizeof(expected), ">#%u OK\r\n>#%u DONE\r\n", id, id);
        front_turns = 0;
        feed(frame);
        assert(strcmp(replies, expected) == 0);
    }
    assert(front_turns == 1);
    feed("#10 RUBIK MOVE\n");
    assert(strcmp(replies, ">#10 ERR BAD_ARG\r\n") == 0);
    assert(front_turns == 1);
    puts("Auto Solve UART replay: #9 RUBIK MOVE F -> OK/DONE; missing argument -> ERR BAD_ARG.");
}
