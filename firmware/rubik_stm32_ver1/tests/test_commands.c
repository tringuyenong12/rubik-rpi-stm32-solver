#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "Rubik_Command.h"
#include "Control_Command.h"
#include "../Hardware/Servo_Control/Servo_Control.h"

typedef struct { char kind; int id; int position; } Event;
static Event events[32];
static unsigned count, accepted, done, errors;
static int fail_id = -1;
static const char *last_error;

static void record(char kind, int id, int position)
{
    assert(count < sizeof(events) / sizeof(events[0]));
    events[count++] = (Event){kind, id, position};
}
bool Servo_Rotate(Servo_ID_t id, Servo_Rotate_Position_t position)
{ record('R', id, position); return (int)id != fail_id; }
bool Servo_Move(Servo_ID_t id, Servo_Move_Position_t position)
{ record('M', id, position); return (int)id != fail_id; }
bool waitUntilServosDone(void) { record('W', -1, -1); return true; }
void UART_Accept(uint16_t id) { assert(id == 15); ++accepted; }
void UART_Done(uint16_t id) { assert(id == 15); ++done; }
void UART_Error(uint16_t id, const char *error)
{ assert(id == 15); ++errors; last_error = error; }
void UART_Command_Stop(uint16_t id) { assert(id == 15); }
void HAL_Delay(uint32_t ms) { (void)ms; }

static void reset(void)
{ count = accepted = done = errors = 0; fail_id = -1; last_error = NULL; }
static void expect(unsigned index, char kind, int id, int position)
{
    assert(index < count);
    assert(events[index].kind == kind);
    assert(events[index].id == id);
    assert(events[index].position == position);
}
#ifndef CONTROL_ONLY
static void rubik(char *move)
{
    char *args[] = {"15", "RUBIK", "MOVE", move};
    Rubik_CommandHandler(4, args, 15);
}
#endif
static void control(char *ids, char *position)
{
    char *args[] = {"15", "CONTROL", "SERVO", ids, position};
    Control_CommandHandler(5, args, 15);
}
static void control_two(char *ids, char *first, char *second)
{
    char *args[] = {"15", "CONTROL", "SERVO", ids, first, second};
    Control_CommandHandler(6, args, 15);
}
int main(void)
{
#ifndef CONTROL_ONLY
    char *moves[] = {"LR", "L_R", "FB", "F_B"};
    for (unsigned n = 0; n < 4; ++n) {
        int first = n < 2 ? SERVO_ROTATE_LEFT : SERVO_ROTATE_FRONT;
        int second = n < 2 ? SERVO_ROTATE_RIGHT : SERVO_ROTATE_BACK;
        reset(); rubik(moves[n]);
        assert(accepted == 1 && done == 1 && errors == 0 && count == 12);
        expect(0, 'R', first, n % 2 ? SERVO_ROTATE_ANTICLOCKWISE : SERVO_ROTATE_CLOCKWISE);
        expect(1, 'R', second, SERVO_ROTATE_CLOCKWISE);
        expect(3, 'M', first + 4, SERVO_MOVE_FULL_RELEASE);
        expect(4, 'M', second + 4, SERVO_MOVE_FULL_RELEASE);
        expect(6, 'R', first, SERVO_ROTATE_HOME);
        expect(7, 'R', second, SERVO_ROTATE_HOME);
        expect(9, 'M', first + 4, SERVO_MOVE_CLAMP);
        expect(10, 'M', second + 4, SERVO_MOVE_CLAMP);
        for (unsigned i = 2; i < 12; i += 3) expect(i, 'W', -1, -1);
    }
#endif
    char *pairs[] = {"02", "13", "46", "57"};
    char *rotate_positions[] = {"HOME", "CLOCK", "ANTI"};
    char *move_positions[] = {"FULL_RELEASE", "HALF_RELEASE", "CLAMP", "TIGHT_CLAMP"};
    for (unsigned n = 0; n < 4; ++n) {
        for (unsigned p = 0; p < (n < 2 ? 3U : 4U); ++p) {
            reset(); control(pairs[n], n < 2 ? rotate_positions[p] : move_positions[p]);
            assert(accepted == 1 && done == 1 && errors == 0 && count == 3);
            expect(0, n < 2 ? 'R' : 'M', pairs[n][0] - '0', p);
            expect(1, n < 2 ? 'R' : 'M', pairs[n][1] - '0', p);
            expect(2, 'W', -1, -1);
        }
    }
    for (int id = 0; id < 8; ++id) {
        char text[] = {(char)('0' + id), '\0'};
        reset(); control(text, id < 4 ? "HOME" : "CLAMP");
        assert(accepted == 1 && done == 1 && errors == 0 && count == 2);
        expect(0, id < 4 ? 'R' : 'M', id, id < 4 ? SERVO_ROTATE_HOME : SERVO_MOVE_CLAMP);
    }
    for (unsigned n = 0; n < 4; ++n) {
        unsigned limit = n < 2 ? 3U : 4U;
        for (unsigned first = 0; first < limit; ++first) {
            for (unsigned second = 0; second < limit; ++second) {
                char **positions = n < 2 ? rotate_positions : move_positions;
                reset(); control_two(pairs[n], positions[first], positions[second]);
                assert(accepted == 1 && done == 1 && !errors && count == 3);
                expect(0, n < 2 ? 'R' : 'M', pairs[n][0] - '0', first);
                expect(1, n < 2 ? 'R' : 'M', pairs[n][1] - '0', second);
                expect(2, 'W', -1, -1);
            }
        }
    }
    reset(); control_two("02", "CLOCK", "CLAMP");
    assert(errors == 1 && !accepted && !done && !count);
    reset(); control_two("46", "CLAMP", "ANTI");
    assert(errors == 1 && !accepted && !done && !count);
    reset(); control_two("0", "CLOCK", "ANTI");
    assert(errors == 1 && !accepted && !done && !count);
    char *extra_args[] = {"15", "CONTROL", "SERVO", "02", "CLOCK", "ANTI", "HOME"};
    reset(); Control_CommandHandler(7, extra_args, 15);
    assert(errors == 1 && !accepted && !done && !count);
    char *invalid_ids[] = {"", "26", "45", "8", "-1", "2x", "999999999999999999999999999999"};
    for (unsigned n = 0; n < sizeof(invalid_ids) / sizeof(invalid_ids[0]); ++n) {
        reset(); control(invalid_ids[n], "HOME");
        assert(errors == 1 && !accepted && !done && !count);
    }
    reset(); control("02", "CLAMP");
    assert(errors == 1 && !accepted && !count);
    reset(); control("46", "HOME");
    assert(errors == 1 && !accepted && !count);
    reset(); fail_id = 0; control("02", "HOME");
    assert(accepted == 1 && errors == 1 && !done && count == 2);
    assert(strcmp(last_error, "EXEC_FAILED") == 0);
#ifndef CONTROL_ONLY
    reset(); fail_id = SERVO_ROTATE_RIGHT; rubik("LR");
    assert(accepted == 1 && errors == 1 && !done && count == 2);
    reset(); rubik("XX");
    assert(errors == 1 && !accepted && !count);
    char *short_args[] = {"15", "RUBIK", "MOVE"};
    reset(); Rubik_CommandHandler(3, short_args, 15);
    assert(errors == 1 && !accepted && !count);
    reset(); Rubik_CommandHandler(2, short_args, 15);
    assert(errors == 1 && !accepted && !count);
#endif
    puts("Command tests passed: pair positions, single IDs, invalid inputs and failures.");
    return 0;
}
