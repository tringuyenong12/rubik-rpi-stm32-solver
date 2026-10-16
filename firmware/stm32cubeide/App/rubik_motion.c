#include "rubik_motion.h"

#include "main.h"

#define PULL 0
#define PUSH 60
#define DIR_DOWN 180
#define DIR_UP 0

#define SERVO_SETTLE_MS 300U
#define CUBE_TURN_SETTLE_MS 350U

static RubikServoWriteFn write_servo;

static bool is_ready(void)
{
    return write_servo != NULL;
}

static void set_servo(int servo_index, int angle_deg)
{
    write_servo(servo_index, angle_deg);
}

/* These functions are deliberately called only from the main loop, never
 * from HAL_UART_RxCpltCallback.  The UART interrupt remains free to collect
 * bytes while a servo sequence is in progress. */
static void rotate_face(int grip_servo, int slide_servo, int angle)
{
    set_servo(grip_servo, angle);
    HAL_Delay(SERVO_SETTLE_MS);
    set_servo(slide_servo, PULL);
    HAL_Delay(SERVO_SETTLE_MS);
    set_servo(grip_servo, 90);
    HAL_Delay(SERVO_SETTLE_MS);
    set_servo(slide_servo, PUSH);
    HAL_Delay(SERVO_SETTLE_MS);
}

static void c_rotate_F(void) { rotate_face(0, 1, 180); }
static void cc_rotate_F(void) { rotate_face(0, 1, 0); }
static void rotate_2_F(void) { c_rotate_F(); c_rotate_F(); }

static void c_rotate_B(void) { rotate_face(2, 3, 180); }
static void cc_rotate_B(void) { rotate_face(2, 3, 0); }
static void rotate_2_B(void) { c_rotate_B(); c_rotate_B(); }

static void c_rotate_L(void) { rotate_face(4, 5, 180); }
static void cc_rotate_L(void) { rotate_face(4, 5, 0); }
static void rotate_2_L(void) { c_rotate_L(); c_rotate_L(); }

static void c_rotate_R(void) { rotate_face(6, 7, 180); }
static void cc_rotate_R(void) { rotate_face(6, 7, 0); }
static void rotate_2_R(void) { c_rotate_R(); c_rotate_R(); }

static void rotate_cube(int direction)
{
    set_servo(1, PULL);
    set_servo(3, PULL);
    HAL_Delay(SERVO_SETTLE_MS);

    /* Servo 6 is mounted in the mirrored direction. */
    set_servo(4, direction);
    set_servo(6, 180 - direction);
    HAL_Delay(CUBE_TURN_SETTLE_MS);

    set_servo(1, PUSH);
    set_servo(3, PUSH);
    HAL_Delay(SERVO_SETTLE_MS);

    set_servo(5, PULL);
    set_servo(7, PULL);
    HAL_Delay(SERVO_SETTLE_MS);

    set_servo(4, 90);
    set_servo(6, 90);
    HAL_Delay(SERVO_SETTLE_MS);

    set_servo(5, PUSH);
    set_servo(7, PUSH);
    HAL_Delay(SERVO_SETTLE_MS);
}

static void c_rotate_U(void) { rotate_cube(DIR_DOWN); c_rotate_F(); rotate_cube(DIR_UP); }
static void cc_rotate_U(void) { rotate_cube(DIR_DOWN); cc_rotate_F(); rotate_cube(DIR_UP); }
static void rotate_2_U(void) { rotate_cube(DIR_DOWN); rotate_2_F(); rotate_cube(DIR_UP); }

static void c_rotate_D(void) { rotate_cube(DIR_DOWN); c_rotate_B(); rotate_cube(DIR_UP); }
static void cc_rotate_D(void) { rotate_cube(DIR_DOWN); cc_rotate_B(); rotate_cube(DIR_UP); }
static void rotate_2_D(void) { rotate_cube(DIR_DOWN); rotate_2_B(); rotate_cube(DIR_UP); }

void RubikMotion_Init(RubikServoWriteFn writer)
{
    write_servo = writer;
}

bool RubikMotion_IsSupported(uint8_t command)
{
    return command == RUBIK_CMD_PING ||
           (command >= RUBIK_CMD_F_CW && command <= RUBIK_CMD_D_2) ||
           command == RUBIK_CMD_HOME || command == RUBIK_CMD_FINISH;
}

bool RubikMotion_Home(void)
{
    if (!is_ready()) {
        return false;
    }

    set_servo(0, 90);
    set_servo(2, 90);
    set_servo(4, 90);
    set_servo(6, 90);
    set_servo(1, PUSH);
    set_servo(3, PUSH);
    set_servo(5, PUSH);
    set_servo(7, PUSH);
    HAL_Delay(SERVO_SETTLE_MS);
    return true;
}

bool RubikMotion_Execute(uint8_t command)
{
    if (command == RUBIK_CMD_PING) {
        return true;
    }
    if (command == RUBIK_CMD_HOME) {
        return RubikMotion_Home();
    }
    if (!is_ready()) {
        return false;
    }

    switch (command) {
    case RUBIK_CMD_F_CW: c_rotate_F(); break;
    case RUBIK_CMD_F_CCW: cc_rotate_F(); break;
    case RUBIK_CMD_F_2: rotate_2_F(); break;
    case RUBIK_CMD_B_CW: c_rotate_B(); break;
    case RUBIK_CMD_B_CCW: cc_rotate_B(); break;
    case RUBIK_CMD_B_2: rotate_2_B(); break;
    case RUBIK_CMD_L_CW: c_rotate_L(); break;
    case RUBIK_CMD_L_CCW: cc_rotate_L(); break;
    case RUBIK_CMD_L_2: rotate_2_L(); break;
    case RUBIK_CMD_R_CW: c_rotate_R(); break;
    case RUBIK_CMD_R_CCW: cc_rotate_R(); break;
    case RUBIK_CMD_R_2: rotate_2_R(); break;
    case RUBIK_CMD_U_CW: c_rotate_U(); break;
    case RUBIK_CMD_U_CCW: cc_rotate_U(); break;
    case RUBIK_CMD_U_2: rotate_2_U(); break;
    case RUBIK_CMD_D_CW: c_rotate_D(); break;
    case RUBIK_CMD_D_CCW: cc_rotate_D(); break;
    case RUBIK_CMD_D_2: rotate_2_D(); break;
    case RUBIK_CMD_FINISH: RubikMotion_OnFinished(); break;
    default: return false;
    }
    return true;
}

__weak void RubikMotion_OnFinished(void)
{
    /* Optional: toggle an LED or run a buzzer here. */
}
