#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "UART_Handle.h"
#include "Rubik_Control.h"

static UART_HandleTypeDef uart;
static uint8_t *rx;
static char calls[32];
static unsigned count;
static int in_isr;
static const char *during_move;

HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *h, uint8_t *b, uint16_t n)
{
    assert(h == &uart && n == 1U);
    rx = b;
    return HAL_OK;
}
HAL_StatusTypeDef HAL_UART_AbortReceive(UART_HandleTypeDef *h)
{
    h->ErrorCode = 0U;
    return HAL_OK;
}
static void feed(const char *s)
{
    while (*s) {
        *rx = (uint8_t)*s++;
        in_isr = 1;
        HAL_UART_RxCpltCallback(&uart);
        in_isr = 0;
    }
}
static void record(char c)
{
    assert(!in_isr);
    calls[count++] = c;
    calls[count] = 0;
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
void Rubik_DownToFront(void) { record('D'); }
static void reset(void)
{
    count = 0;
    calls[0] = 0;
    during_move = NULL;
    uart.ErrorCode = 0U;
    UART_Command_Init(&uart);
}
int main(void)
{
    const char *invalid[] = {
        "@1 RUBIK MOVE U\n", "# RUBIK MOVE U\n", "#-1 RUBIK MOVE U\n",
        "#1X RUBIK MOVE U\n", "#1 SERVO MOVE U\n", "#1 RUBIK RESET U\n",
        "#1 RUBIK MOVE\n", "#1 RUBIK MOVE U extra\n", "#1 RUBIK MOVE Q\n",
        "#1 RUBIK MOVE U2\n", "#1 RUBIK MOVE R'\n", "#1 RUBIK MOVE UU\n",
        "#1 rubik MOVE U\n", "\n", " \r\n", "#1 RUBIK MOVE U\001\n"
    };
    char line[128];
    UART_Command_Init(NULL);
    for (unsigned i = 0; i < 6; ++i) {
        const char face = "UDLRFB"[i];
        reset();
        snprintf(line, sizeof(line), "#1 RUBIK MOVE %c\r\n", face);
        feed(line);
        assert(count == 0); /* ISR must not execute motion. */
        UART_Handle_Process();
        assert(count == 1 && calls[0] == face);
        UART_Handle_Process();
        assert(count == 1); /* Each line executes once. */
    }
    for (unsigned i = 0; i < sizeof(invalid)/sizeof(invalid[0]); ++i) {
        reset();
        feed(invalid[i]);
        UART_Handle_Process();
        assert(count == 0);
    }
    /* Numeric value has no uint32_t/uint64_t limit. */
    reset();
    feed("#9999999999999999999999999999999999999999 RUBIK MOVE U\n");
    UART_Command_Process();
    assert(strcmp(calls, "U") == 0);
    reset();
    feed("#0000000000000000000000000000000000000000 RUBIK MOVE R\n");
    UART_Command_Process();
    assert(strcmp(calls, "R") == 0);
    reset();
    feed("#0\tRUBIK   MOVE\tF\r\n");
    UART_Command_Process();
    assert(strcmp(calls, "F") == 0);

    reset();
    feed("#1 RUBIK MO");
    UART_Handle_Process();
    assert(count == 0);
    feed("VE U\n");
    UART_Handle_Process();
    assert(strcmp(calls, "U") == 0);

    reset();
    strcpy(line, "#1 RUBIK MOVE U");
    memset(line + strlen(line), ' ', sizeof(line) - strlen(line) - 2U);
    line[sizeof(line)-2U] = '\n'; line[sizeof(line)-1U] = 0;
    feed(line);
    UART_Handle_Process();
    assert(count == 0); /* An oversized valid prefix must not execute. */
    feed("#2 RUBIK MOVE R\n");
    UART_Handle_Process();
    assert(strcmp(calls, "R") == 0);

    reset();
    feed("#1 RUBIK MOVE U\n#2 RUBIK MOVE R\n");
    UART_Handle_Process();
    UART_Handle_Process();
    assert(strcmp(calls, "U") == 0); /* Single buffer, no queue. */

    reset();
    during_move = "#2 RUBIK MO";
    feed("#1 RUBIK MOVE U\n");
    UART_Handle_Process();
    feed("VE R\n#3 RUBIK MOVE F\n");
    UART_Handle_Process();
    assert(strcmp(calls, "UF") == 0); /* Drop the entire busy line. */

    reset();
    feed("#1 RUBIK MOVE U");
    *rx = 0; HAL_UART_RxCpltCallback(&uart);
    feed("\n"); UART_Handle_Process();
    assert(count == 0);
    feed("#2 RUBIK MOVE B\n"); UART_Handle_Process();
    assert(strcmp(calls, "B") == 0);

    reset();
    feed("#1 RUBIK MOVE U");
    uart.ErrorCode = 8U;
    HAL_UART_RxCpltCallback(&uart);
    HAL_UART_ErrorCallback(&uart);
    feed("\n#2 RUBIK MOVE L\n"); UART_Handle_Process();
    assert(strcmp(calls, "L") == 0);
    reset();
    feed("#2 RUBIK MOVE ");
    *rx = 'B'; UART_Command_RxCallback(&uart);
    *rx = '\n'; UART_Command_RxCallback(&uart);
    UART_Command_Process();
    assert(strcmp(calls, "B") == 0);
    puts("UART step 1 passed: six faces, framing, validation, single buffer, RX recovery, motion in main.");
    return 0;
}
