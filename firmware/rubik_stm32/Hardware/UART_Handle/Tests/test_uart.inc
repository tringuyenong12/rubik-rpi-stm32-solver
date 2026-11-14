/* Compiled explicitly by run_tests.py; .inc avoids inclusion in CubeIDE firmware. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "UART_Handle.h"
#include "UART_Command.h"
#include "Calibration_Command.h"
#include "../Servo_Control/Servo_Control.h"
#include "../PCA9685/PCA9685.h"

static UART_HandleTypeDef uart;
static uint8_t *rx;
static uint32_t tick;
static char replies[32768];
static unsigned output_length, writes, moves;
#ifndef UART_TEST_REAL_RUBIK
static unsigned last_move;
#endif
static bool isr;
static const char *during_move;
static float last_angle;
static unsigned last_channel;

HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *h, uint8_t *buffer, uint16_t n)
{
    assert(h == &uart && n == 1U);
    rx = buffer;
    return HAL_OK;
}
HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *h, uint8_t *buffer, uint16_t n, uint32_t timeout)
{
    assert(!isr && h == &uart && timeout == 20U);
    assert(output_length + n < sizeof(replies));
    memcpy(replies + output_length, buffer, n);
    output_length += n;
    replies[output_length] = 0;
    return HAL_OK;
}
HAL_StatusTypeDef HAL_UART_AbortReceive(UART_HandleTypeDef *h)
{ h->ErrorCode = 0; return HAL_OK; }
uint32_t HAL_GetTick(void) { return tick; }

static void feed(const char *text)
{
    while (*text)
    {
        *rx = (uint8_t)*text++;
        isr = true;
        UART_Command_RxCallback(&uart);
        isr = false;
    }
}
void HAL_Delay(uint32_t ms)
{
    assert(!isr);
    tick += ms;
    if (during_move)
    {
        const char *text = during_move;
        during_move = NULL;
        feed(text);
    }
}
void PCA9685_SetServoAngle(uint8_t channel, float angle)
{
    assert(!isr && channel < 16U && isfinite(angle) && angle >= 0 && angle <= 180);
    ++writes;
    last_angle = angle;
    last_channel = channel;
}

#ifndef UART_TEST_REAL_RUBIK
static void move(unsigned code)
{
    assert(!isr);
    ++moves;
    last_move = code;
    HAL_Delay(1000);
}
void Rubik_UpToFront(void) { move(0); }
void Rubik_DownToFront(void) { move(1); }
void Rubik_Left(void) { move(2); }
void Rubik_Right(void) { move(3); }
void Rubik_Front(void) { move(4); }
void Rubik_Back(void) { move(5); }
void Rubik_Up_ToFront(void) { move(6); }
void Rubik_Left_(void) { move(8); }
void Rubik_Right_(void) { move(9); }
void Rubik_Front_(void) { move(10); }
void Rubik_Back_(void) { move(11); }
void Rubik_Hold_Start_Position(void) { move(12); }
#endif

static void clear_output(void) { output_length = 0; replies[0] = 0; }
static void command(const char *line, const char *expected)
{
    clear_output();
    feed(line);
    UART_Command_Process();
    if (strcmp(replies, expected))
    {
        fprintf(stderr, "Command: %sExpected: %sActual: %s", line, expected, replies);
        assert(0);
    }
}

int main(void)
{
    static const char *const faces[] = {"U", "D", "L", "R", "F", "B", "U_", "D_", "L_", "R_", "F_", "B_"};
    char line[256];
    UART_Command_Init(NULL);
    UART_Command_Process();
    UART_Command_Init(&uart);
    for (unsigned i = 0; i < 12U; ++i)
    {
        unsigned before = moves;
        (void)before;
        snprintf(line, sizeof(line), "#65535 RUBIK MOVE %s 500\r\n", faces[i]);
        command(line, i == 7U ? "#65535 ERR NOT_IMPLEMENTED\n" : "#65535 OK\n#65535 DONE\n");
#ifndef UART_TEST_REAL_RUBIK
        assert(moves == before + (i != 7U));
        if (i != 7U) assert(last_move == i);
#endif
    }
    command("#1 RUBIK RESET\n", "#1 OK\n#1 DONE\n");
    command("#2 RUBIK PING\n", "#2 OK\n#2 DONE\n");
    command("\x23\x31\x20\x52\x55\x42\x49\x4B\x20\x50\x49\x4E\x47\x0A",
            "#1 OK\n#1 DONE\n"); /* Exact bytes sent from a hex terminal. */
    command("#1 RUBIK PING\r\n", "#1 OK\n#1 DONE\n");
    /* CRLF may arrive across separate main-loop iterations. */
    command("#1 RUBIK PING\r", "");
    command("\n", "#1 OK\n#1 DONE\n");
    command("\n", ""); /* Do not execute the completed command twice. */
    command("#1 RUBIK PING", ""); /* A delimiter is still required. */
    command("\n", "#1 OK\n#1 DONE\n");
    command("#0\tSYSTEM   VERSION\n", "#0 VALUE UART_1.0\n");
    command("#1 SYSTEM STATUS\n", "#1 VALUE IDLE\n");
    command("#1 UNKNOWN GET\n", "#1 ERR UNKNOWN_CMD\n");
    command("#1 RUBIK BAD\n", "#1 ERR UNKNOWN_CMD\n");
    command("#1 RUBIK MOVE L CW 500\n", "#1 ERR BAD_ARG\n");
    command("#1 RUBIK MOVE L -1\n", "#1 ERR BAD_ARG\n");
    command("#1 RUBIK MOVE L 4294967296\n", "#1 ERR BAD_ARG\n");
    command("#1 RUBIK MOVE L 0\n", "#1 ERR LIMIT\n");
    command("#1 RUBIK MOVE L 60001\n", "#1 ERR LIMIT\n");
    command("#1 RUBIK MOVE Q 500\n", "#1 ERR BAD_ARG\n");
    command("#65536 RUBIK PING\n", "#0 ERR BAD_FORMAT\n");
    command("#-1 RUBIK PING\n", "#0 ERR BAD_FORMAT\n");
    command("#1 RUBIK\n", "#1 ERR BAD_FORMAT\n");
    command("#1 RUBIK PING\001\n", "#1 ERR BAD_FORMAT\n");
    command("#1 RUBIK PI\rNG\n", "#1 ERR BAD_FORMAT\n");
    memset(line, ' ', sizeof(line));
    memcpy(line, "#1 RUBIK PING", 13);
    line[sizeof(line) - 2] = '\n'; line[sizeof(line) - 1] = 0;
    command(line, ""); /* Oversized lines are discarded. */
    clear_output(); feed("#1 RUBIK PI"); UART_Command_Process(); assert(!*replies);
    tick += 1001;
    command("NG\n#2 RUBIK PING\n", "#2 OK\n#2 DONE\n");
    feed("#1 RUBIK PI"); uart.ErrorCode = 8;
    HAL_UART_ErrorCallback(&uart);
    command("NG\n#2 RUBIK PING\n", "#2 OK\n#2 DONE\n");
    command("#1 RUBIK PING\n", "#1 OK\n#1 DONE\n");

    command("#1 CONTROL SERVO 4 CLOCK\n", "#1 ERR INVALID_POSITION\n");
    command("#1 CONTROL SERVO 8 HOME\n", "#1 ERR INVALID_POSITION\n");
    command("#1 CONTROL SERVO 0 HOME extra\n", "#1 ERR BAD_ARG\n");
    static const char *const positions[] = {"HOME", "CLOCK", "ANTI", "FULL_RELEASE", "HALF_RELEASE", "CLAMP", "TIGHT_CLAMP"};
    for (unsigned id = 0; id < 8; ++id)
        for (unsigned p = 0; p < (id < 4 ? 3U : 4U); ++p)
        {
            snprintf(line, sizeof(line), "#1 CONTROL SERVO %u %s\n", id, positions[p + (id < 4 ? 0 : 3)]);
            command(line, "#1 OK\n#1 DONE\n");
            assert(last_channel == id);
        }
    command("#1 CALIB SERVO SET 0 HOME 310\n", "#1 ERR NOT_IN_CALIB_MODE\n");
    command("#1 CALIB START\n", "#1 OK\n#1 DONE\n");
    command("#1 CALIB START\n", "#1 ERR BUSY\n");
    command("#1 SYSTEM STATUS\n", "#1 VALUE CALIB\n");
    unsigned before_writes = writes;
    float old_offset = servo[0].state.rotate.offset_calib_home_angle;
    for (unsigned pwm = 102; pwm <= 511; ++pwm)
    {
        snprintf(line, sizeof(line), "#1 CALIB SERVO SET 0 HOME %u\n", pwm);
        command(line, "#1 OK\n#1 DONE\n");
        char expected[48];
        snprintf(expected, sizeof(expected), "#1 VALUE %u\n", pwm);
        command("#1 CALIB SERVO GET 0 HOME\n", expected);
    }
    assert(writes == before_writes && servo[0].state.rotate.offset_calib_home_angle == old_offset);
    for (unsigned id = 0; id < 8; ++id)
        for (unsigned p = 0; p < (id < 4 ? 3U : 4U); ++p)
        {
            const char *name = positions[p + (id < 4 ? 0 : 3)];
            snprintf(line, sizeof(line), "#1 CALIB SERVO SET %u %s 310\n", id, name);
            command(line, "#1 OK\n#1 DONE\n");
            snprintf(line, sizeof(line), "#1 CALIB SERVO GET %u %s\n", id, name);
            command(line, "#1 VALUE 310\n");
        }
    command("#1 CALIB SERVO SET 0 HOME 512\n", "#1 ERR LIMIT\n");
    command("#1 CALIB SERVO ADD 0 HOME 4294967295\n", "#1 ERR LIMIT\n");
    command("#1 CALIB SERVO SUB 0 HOME 600\n", "#1 ERR LIMIT\n");
    command("#1 CALIB EXIT\n", "#1 OK\n#1 DONE\n");
    command("#1 CALIB SERVO GET 0 HOME\n", "#1 VALUE 307\n");
    command("#1 CALIB START\n", "#1 OK\n#1 DONE\n");
    command("#1 CALIB SERVO SET 0 HOME 310\n", "#1 OK\n#1 DONE\n");
    command("#1 CALIB SERVO ADD 0 HOME 5\n", "#1 OK\n#1 DONE\n");
    command("#1 CALIB SERVO SUB 0 HOME 2\n", "#1 OK\n#1 DONE\n");
    command("#1 CALIB SET SERVO_SETTLE_MS 42\n", "#1 OK\n#1 DONE\n");
    command("#1 CALIB GET SERVO_SETTLE_MS\n", "#1 VALUE 42\n");
    assert(Calibration_SettleMs() == 1000);
    command("#1 CALIB SAVE\n", "#1 OK\n#1 DONE\n");
    assert(writes == before_writes && Calibration_SettleMs() == 42);
    command("#1 CONTROL SERVO 0 HOME\n", "#1 OK\n#1 DONE\n");
    assert((unsigned)(last_angle * (max_pulse - min_pulse) / 180.0 + min_pulse) == 313);
    command("#1 CALIB START\n", "#1 OK\n#1 DONE\n");
    command("#1 CALIB SERVO SET 0 HOME 400\n", "#1 OK\n#1 DONE\n");
    command("#1 CALIB RESET\n", "#1 OK\n#1 DONE\n");
    command("#1 CALIB SERVO GET 0 HOME\n", "#1 VALUE 313\n");
    command("#1 CALIB SAVE\n", "#1 ERR NOT_IN_CALIB_MODE\n");
    command("#1 CONFIG GET UART_TIMEOUT_MS\n", "#1 VALUE 1000\n");
    command("#1 CONFIG SET UART_TIMEOUT_MS 123\n", "#1 OK\n#1 DONE\n");
    command("#1 CONFIG SAVE\n", "#1 OK\n#1 DONE\n");
    command("#1 CONFIG GET UART_TIMEOUT_MS\n", "#1 VALUE 123\n");
    command("#1 CONFIG SET UART_TIMEOUT_MS 0\n", "#1 ERR LIMIT\n");

    clear_output();
    feed("#1 RUBIK PING\n#2 RUBIK MOVE R 500\n");
    UART_Command_Process();
    UART_Command_Process();
    assert(!strcmp(replies, "#1 OK\n#1 DONE\n")); /* No queue. */
    during_move = "#2 RUBIK MOVE R 500\n";
    clear_output(); feed("#1 RUBIK MOVE L 500\n"); UART_Command_Process();
    UART_Command_Process();
    assert(!strcmp(replies, "#1 OK\n#1 DONE\n")); /* Busy input is ignored. */
    during_move = "#2 RUBIK MO";
    clear_output(); feed("#1 RUBIK MOVE L 500\n"); UART_Handle_Process();
    command("VE R 500\n#3 RUBIK PING\n", "#3 OK\n#3 DONE\n");
    command("#9 SYSTEM STOP\n", "#9 OK\n#9 DONE\n");
    command("#9 RUBIK STOP\n", "#9 OK\n#9 DONE\n");
    puts("UART tests passed: dispatch, servo integration, single-command reception and calibration.");
    return 0;
}
