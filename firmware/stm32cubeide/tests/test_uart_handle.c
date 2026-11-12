#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "UART_Handle.h"
#include "../App/rubik_protocol.h"
#include "Rubik_Control.h"

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "Check failed at line %d: %s\n", __LINE__, #condition); \
        exit(EXIT_FAILURE); \
    } \
} while (0)

static UART_HandleTypeDef uart;
static uint8_t *rx;
static char calls[32];
static unsigned count;
static bool in_isr;
static const char *during_move;
static char replies[2048];
static uint32_t ticks;
static unsigned pwm_count;
static uint8_t pwm_channel;
static uint16_t pwm_off;
static HAL_StatusTypeDef transmit_result;
static HAL_StatusTypeDef receive_result;
static unsigned abort_count;
static Servo_t default_servos[SERVO_COUNT];
static unsigned angle_count;
static float last_angle;

HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *handle,
                                     uint8_t *byte, uint16_t size)
{
    CHECK(handle == &uart && size == 1);
    rx = byte;
    return receive_result;
}

HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *handle, uint8_t *data,
                                   uint16_t size, uint32_t timeout)
{
    CHECK(!in_isr && handle == &uart && timeout > 0);
    if (transmit_result != HAL_OK) {
        return transmit_result;
    }
    size_t length = strlen(replies);
    CHECK(length + size < sizeof(replies));
    memcpy(replies + length, data, size);
    replies[length + size] = 0;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_UART_AbortReceive(UART_HandleTypeDef *handle)
{
    CHECK(handle == &uart);
    ++abort_count;
    handle->ErrorCode = 0;
    return HAL_OK;
}

void HAL_Delay(uint32_t delay_ms) { CHECK(!in_isr); ticks += delay_ms; }
uint32_t HAL_GetTick(void) { return ticks; }

void PCA9685_SetPWM(uint8_t channel, uint16_t on, uint16_t off)
{
    CHECK(!in_isr && on == 0 && strstr(replies, " ACK\n") != NULL);
    ++pwm_count;
    pwm_channel = channel;
    pwm_off = off;
}

void PCA9685_SetServoAngle(uint8_t channel, float angle)
{
    CHECK(!in_isr && strstr(replies, " ACK\n") != NULL);
    ++angle_count;
    pwm_channel = channel;
    last_angle = angle;
}

static void feed(const char *line)
{
    while (*line) {
        *rx = (uint8_t)*line++;
        in_isr = true;
        UART_Command_RxCallback(&uart);
        in_isr = false;
    }
}

static void record(char face)
{
    CHECK(!in_isr && count < sizeof(calls) - 1);
    CHECK(strstr(replies, " ACK\n") != NULL);
    calls[count++] = face;
    calls[count] = 0;
    ticks += 4000;
    if (during_move) {
        feed(during_move);
        during_move = NULL;
    }
}

void Rubik_Left(void) { record('L'); }
void Rubik_Right(void) { record('R'); }
void Rubik_Front(void) { record('F'); }
void Rubik_Back(void) { record('B'); }
void Rubik_UpToFront(void) { record('U'); }
void Rubik_Left_(void) { record('l'); }
void Rubik_Right_(void) { record('r'); }
void Rubik_Front_(void) { record('f'); }
void Rubik_Back_(void) { record('b'); }
void Rubik_Hold_Start_Position(void) { record('H'); }

static void reset(void)
{
    count = 0;
    calls[0] = 0;
    replies[0] = 0;
    ticks = 0;
    pwm_count = 0;
    angle_count = 0;
    memcpy(servo, default_servos, sizeof(default_servos));
    abort_count = 0;
    during_move = NULL;
    transmit_result = HAL_OK;
    receive_result = HAL_OK;
    uart.ErrorCode = HAL_UART_ERROR_NONE;
    UART_Command_Init(&uart);
}

static void request(const char *line)
{
    feed(line);
    UART_Command_Process();
}

int main(void)
{
    memcpy(default_servos, servo, sizeof(default_servos));
    const char *moves[] = {"U", "L", "R", "F", "B", "L_", "R_", "F_", "B_"};
    const char expected[] = "ULRFBlrfb";
    char line[256];
    UART_Command_Init(NULL);
    UART_Command_Process();
    UART_Command_RxCallback(NULL);
    UART_Command_ErrorCallback(NULL);
    for (unsigned i = 0; i < sizeof(moves) / sizeof(moves[0]); ++i) {
        reset();
        snprintf(line, sizeof(line), "#abc-123 RUBIK MOVE %s\r\n", moves[i]);
        feed(line);
        CHECK(count == 0 && replies[0] == 0);
        UART_Command_Process();
        CHECK(count == 1 && calls[0] == expected[i]);
        CHECK(strcmp(replies, "#abc-123 ACK\n#abc-123 DONE\n") == 0);
        UART_Command_Process();
        CHECK(count == 1);
    }
    reset();
    request("#1 RUBIK TURN R 2 12000\n");
    CHECK(strcmp(calls, "RR") == 0 && ticks == 12000);
    reset();
    request("#1 RUBIK MOVE R -1 1\n");
    CHECK(strcmp(calls, "r") == 0 && ticks == 4000);
    reset();
    request("#1 TEST_RUBIK MOVE R_\n");
    CHECK(strcmp(calls, "r") == 0);
    reset();
    request("#12345678901234567890123456789012 RUBIK PING\n");
    CHECK(strcmp(replies, "#12345678901234567890123456789012 ACK\n") == 0);
    reset();
    request("#1\tRUBIK   PING\n");
    CHECK(strcmp(replies, "#1 ACK\n") == 0 && count == 0);

    const char *invalid[] = {
        "#1 RUBIK MOVE U_", "#1 RUBIK MOVE D", "#1 RUBIK MOVE D_",
        "#1 RUBIK MOVE R_ 1 400", "#1 RUBIK MOVE R 0 400",
        "#1 RUBIK MOVE R 3 400", "#1 RUBIK MOVE R 1",
        "#1 RUBIK MOVE R 1 -1", "#1 RUBIK MOVE R 1 60001",
        "#1 RUBIK MOVE R 1 9999999999999999999999999999",
        "#1 RUBIK MOVE R 1x 400", "#1 RUBIK MOVE R 1 4x",
        "#1 RUBIK MOVE R 1 400 extra", "#1 RUBIK MOVE Q", "#1 RUBIK MOVE R2",
        "#1 RUBIK PING extra", "#1 RUBIK STOP extra", "#1 RUBIK HOME extra",
        "#1 OTHER servo 0 1500 300", "#1 RUBIK ACTUATOR x y 10",
        "#1 RUBIK CLAMP x open", "#1 RUBIK SCAN_POSE U",
        "#1 RUBIK SERVO 16 1500 300", "#1 RUBIK SERVO -1 1500 300",
        "#1 RUBIK SERVO 0 499 300", "#1 RUBIK SERVO 0 2501 300",
        "#1 RUBIK SERVO 0 65536500 300", "#1 RUBIK SERVO 0 1500 -1",
        "#1 RUBIK SERVO 0 1500 300 extra", "# RUBIK PING",
        "@1 RUBIK PING", "#123456789012345678901234567890123 RUBIK PING"
    };
    for (unsigned i = 0; i < sizeof(invalid) / sizeof(invalid[0]); ++i) {
        reset();
        snprintf(line, sizeof(line), "%s\n", invalid[i]);
        request(line);
        CHECK(count == 0 && pwm_count == 0);
        CHECK(strstr(replies, " NACK ") != NULL);
        CHECK(strstr(replies, " ACK\n") == NULL && strstr(replies, " DONE\n") == NULL);
    }
    reset();
    request("#1 RUBIK SERVO 15 1500 300\n");
    CHECK(pwm_count == 1 && pwm_channel == 15 && pwm_off == 307 && ticks == 300);
    CHECK(strcmp(replies, "#1 ACK\n#1 DONE\n") == 0);
    reset();
    request("#1 RUBIK STOP\n");
    request("#2 RUBIK MOVE R\n");
    CHECK(count == 0 && strstr(replies, "#2 NACK STOPPED home_required\n") != NULL);
    request("#3 RUBIK HOME\n");
    request("#4 RUBIK MOVE R\n");
    CHECK(strcmp(calls, "HR") == 0);

    reset();
    feed("#1 RUBIK MO");
    UART_Command_Process();
    CHECK(count == 0);
    request("VE R\n");
    CHECK(strcmp(calls, "R") == 0);
    reset();
    memset(line, 'x', sizeof(line));
    memcpy(line, "#1 RUBIK MOVE R ", 16);
    line[sizeof(line) - 2] = '\n';
    line[sizeof(line) - 1] = 0;
    request(line);
    CHECK(count == 0 && strstr(replies, "line_too_long") != NULL);
    request("#2 RUBIK MOVE R\n");
    CHECK(strcmp(calls, "R") == 0);
    reset();
    feed("#1 RUBIK MOVE R");
    *rx = 0;
    UART_Command_RxCallback(&uart);
    request("\n");
    CHECK(count == 0 && strstr(replies, "invalid_character") != NULL);

    /* One pending request: a frame arriving behind it must be dropped whole. */
    reset();
    feed("#1 RUBIK MOVE R\n#2 RUBIK MO");
    UART_Command_Process();
    request("VE L\n#3 RUBIK MOVE F\n");
    CHECK(strcmp(calls, "RF") == 0);
    CHECK(strstr(replies, "#2 ") == NULL);
    /* During a blocking motion, one complete next request may be received. */
    reset();
    during_move = "#2 RUBIK STOP\n";
    request("#1 RUBIK MOVE R\n");
    CHECK(strcmp(replies, "#1 ACK\n#1 DONE\n") == 0);
    UART_Command_Process();
    CHECK(strcmp(replies, "#1 ACK\n#1 DONE\n#2 ACK\n") == 0);
    request("#3 RUBIK MOVE R\n");
    CHECK(strcmp(calls, "R") == 0);

    reset();
    feed("#1 RUBIK MOVE R");
    UART_Command_ErrorCallback(&uart);
    request("\n#2 RUBIK PING\n");
    CHECK(abort_count == 1 && count == 0 && strcmp(replies, "#2 ACK\n") == 0);
    reset();
    feed("#1 RUBIK MOVE R");
    uart.ErrorCode = 8;
    *rx = '\n';
    UART_Command_RxCallback(&uart);
    request("\n#2 RUBIK PING\n");
    CHECK(abort_count == 1 && count == 0 && strcmp(replies, "#2 ACK\n") == 0);
    reset();
    transmit_result = HAL_ERROR;
    request("#1 RUBIK MOVE R\n");
    CHECK(count == 0);
    reset();
    receive_result = HAL_BUSY;
    UART_Command_Init(&uart);
    receive_result = HAL_OK;
    UART_Command_Process();
    request("#1 RUBIK PING\n");
    CHECK(strcmp(replies, "#1 ACK\n") == 0);
    reset();
    request("#1 CALIB SERVO 2 1500 300\n");
    CHECK(pwm_count == 1 && pwm_channel == 2 && pwm_off == 307);
    CHECK(strcmp(replies, "#1 ACK\n#1 DONE\n") == 0);
    request("#2 CALIB servo 3 1500 0\n");
    CHECK(pwm_count == 2 && pwm_channel == 3);
    reset();
    request("#1 CALIB SET 0 HOME 92.5\n");
    CHECK(angle_count == 0 && pwm_count == 0);
    CHECK(servo[0].state.rotate.offset_calib_home_angle == 2.5f);
    CHECK(strcmp(replies, "#1 ACK\n#1 DONE\n") == 0);
    request("#2 CALIB TEST 0 HOME 300\n");
    CHECK(angle_count == 1 && last_angle == 92.5f && ticks == 300);
    CHECK(servo[0].state.rotate.current_angle == 92.5f);
    reset();
    request("#1 CALIB SET 4 CLAMP 12\n");
    CHECK(servo[4].state.move.offset_calib_clamp_angle == 2.0f);
    servo[4].channel = 11;
    request("#2 CALIB TEST 4 CLAMP 250\n");
    CHECK(angle_count == 1 && last_angle == 12.0f && pwm_channel == 11 && ticks == 250);
    request("#3 CALIB SET 4 FULL_RELEASE 175\n");
    request("#4 CALIB TEST 4 FULL_RELEASE 0\n");
    CHECK(last_angle == 175.0f);
    request("#5 CALIB SET 4 HALF_RELEASE 88\n");
    request("#6 CALIB TEST 4 HALF_RELEASE 0\n");
    CHECK(last_angle == 88.0f);
    request("#7 CALIB SET 4 TIGHT_CLAMP 3\n");
    request("#8 CALIB TEST 4 TIGHT_CLAMP 0\n");
    CHECK(last_angle == 3.0f);
    reset();
    request("#1 CALIB SET 3 CLOCKWISE 175\n");
    request("#2 CALIB TEST 3 CLOCKWISE 0\n");
    CHECK(last_angle == 175.0f);
    request("#3 CALIB SET 3 ANTICLOCKWISE 5\n");
    request("#4 CALIB TEST 3 ANTICLOCKWISE 0\n");
    CHECK(last_angle == 5.0f);

    const char *invalid_calibration[] = {
        "SET 8 HOME 90", "SET -1 HOME 90", "SET 0 HOME -1", "SET 0 HOME 180.1",
        "SET 0 HOME nan", "SET 0 HOME inf", "SET 0 HOME 1.2.3", "SET 0 HOME 0x10",
        "SET 0 HOME 90 extra", "SET 0 HOME", "SET 0 CLAMP 10", "SET 4 HOME 90",
        "SET 0 UNKNOWN 90", "TEST 0 HOME -1", "TEST 0 HOME 60001", "TEST 4 HOME 0",
        "TEST 0 HOME 0 extra", "PING", "MOVE R", "SERVO 16 1500 0"
    };
    for (unsigned i = 0; i < sizeof(invalid_calibration) / sizeof(invalid_calibration[0]); ++i) {
        reset();
        snprintf(line, sizeof(line), "#calib CALIB %s\n", invalid_calibration[i]);
        request(line);
        CHECK(strstr(replies, "#calib NACK ") != NULL);
        CHECK(angle_count == 0 && pwm_count == 0);
        CHECK(memcmp(servo, default_servos, sizeof(default_servos)) == 0);
    }
    reset();
    transmit_result = HAL_ERROR;
    request("#1 CALIB SET 0 HOME 92.5\n");
    CHECK(servo[0].state.rotate.offset_calib_home_angle == 0.0f);
    reset();
    request("#1 RUBIK STOP\n");
    request("#2 CALIB SET 0 HOME 92.5\n");
    CHECK(servo[0].state.rotate.offset_calib_home_angle == 2.5f);
    request("#3 CALIB TEST 0 HOME 0\n");
    request("#4 CALIB SERVO 0 1500 0\n");
    CHECK(angle_count == 0 && pwm_count == 0);
    CHECK(strstr(replies, "#3 NACK STOPPED home_required") != NULL);
    CHECK(strstr(replies, "#4 NACK STOPPED home_required") != NULL);
    puts("UART passed: dispatch, ACK/DONE/NACK, limits, STOP/HOME, framing, busy RX, recovery and TX failure.");
    return 0;
}
