#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "Rubik_Command.h"
#include "Control_Command.h"
#include "../Hardware/Servo_Control/Servo_Control.h"

typedef struct { char kind; int id; int position; } Event;
static Event events[64];
static unsigned count, accepted, done, errors;
static int fail_id = -1;
static const char *last_error;
Servo_t servo[SERVO_COUNT];

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

static void scan(char *action, char *face)
{
    char *args[] = {"15", "RUBIK", action, face};
    Rubik_CommandHandler(face ? 4 : 3, args, 15);
}

static void scan_quarter(unsigned offset, bool lr, bool clockwise)
{
    int first = lr ? SERVO_ROTATE_LEFT : SERVO_ROTATE_FRONT;
    int second = lr ? SERVO_ROTATE_RIGHT : SERVO_ROTATE_BACK;
    int support1 = lr ? SERVO_MOVE_FRONT : SERVO_MOVE_LEFT;
    int support2 = lr ? SERVO_MOVE_BACK : SERVO_MOVE_RIGHT;
    expect(offset, 'M', first + 4, SERVO_MOVE_TIGHT_CLAMP);
    expect(offset + 1, 'M', second + 4, SERVO_MOVE_TIGHT_CLAMP);
    expect(offset + 3, 'M', support1, SERVO_MOVE_FULL_RELEASE);
    expect(offset + 4, 'M', support2, SERVO_MOVE_FULL_RELEASE);
    expect(offset + 6, 'R', first, clockwise ? SERVO_ROTATE_CLOCKWISE : SERVO_ROTATE_ANTICLOCKWISE);
    expect(offset + 7, 'R', second, clockwise ? SERVO_ROTATE_ANTICLOCKWISE : SERVO_ROTATE_CLOCKWISE);
    expect(offset + 9, 'M', support1, SERVO_MOVE_CLAMP);
    expect(offset + 10, 'M', support2, SERVO_MOVE_CLAMP);
    expect(offset + 12, 'M', first + 4, SERVO_MOVE_FULL_RELEASE);
    expect(offset + 13, 'M', second + 4, SERVO_MOVE_FULL_RELEASE);
    expect(offset + 15, 'R', first, SERVO_ROTATE_HOME);
    expect(offset + 16, 'R', second, SERVO_ROTATE_HOME);
    expect(offset + 18, 'M', first + 4, SERVO_MOVE_CLAMP);
    expect(offset + 19, 'M', second + 4, SERVO_MOVE_CLAMP);
    for (unsigned i = 2; i < 21; i += 3) expect(offset + i, 'W', -1, -1);
}

static void test_scan(void)
{
    reset(); scan("SCAN_POSE", "F");
    assert(!accepted && !done && !count && errors == 1 && !strcmp(last_error, "SCAN_NOT_READY"));
    reset(); scan("SCAN_BEGIN", NULL);
    assert(accepted == 1 && done == 1 && !errors && count == 5);
    for (unsigned i = 0; i < 4; ++i) expect(i, 'M', i + 4, SERVO_MOVE_CLAMP);
    expect(4, 'W', -1, -1);
    reset(); scan("SCAN_POSE", "XX");
    assert(!accepted && !done && !count && errors == 1 && !strcmp(last_error, "BAD_SCAN_POSE"));
    char *route[] = {"F", "D", "B", "U", "R", "L", "U"};
    for (unsigned n = 0; n < sizeof(route) / sizeof(route[0]); ++n) {
        reset(); scan("SCAN_POSE", route[n]);
        assert(accepted == 1 && done == 1 && !errors);
        assert(count == (n == 5 ? 42U : 21U));
        scan_quarter(0, n < 4, false);
        if (n == 5) scan_quarter(21, false, false);
    }
    reset(); scan("SCAN_POSE", "U");
    assert(accepted == 1 && done == 1 && !errors && !count);
    reset(); fail_id = SERVO_MOVE_RIGHT; scan("SCAN_POSE", "F");
    assert(accepted == 1 && !done && errors == 1 && count == 2);
    assert(!strcmp(last_error, "SCAN_EXEC_FAILED"));
    reset(); scan("SCAN_POSE", "U");
    assert(!accepted && !done && errors == 1 && !count);
    servo[SERVO_ROTATE_FRONT].state.rotate.current_angle = 90.0f;
    reset(); scan("SCAN_BEGIN", NULL);
    assert(accepted == 1 && !done && errors == 1 && !count);
    assert(!strcmp(last_error, "SCAN_PREPARE_FAILED"));
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
int main(int argc, char *argv[])
{
#ifndef CONTROL_ONLY
    test_scan();
    if (argc == 2 && !strcmp(argv[1], "--scan-only")) {
        puts("Auto Solve firmware scan tests passed.");
        return 0;
    }
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
    (void)argc;
    (void)argv;
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
