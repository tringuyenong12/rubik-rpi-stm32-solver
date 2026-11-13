#include "UART_Handle.h"
#include "../rubik_protocol.h"
#include "../../Hardware/PCA9685/PCA9685.h"
#include "../../Hardware/Rubik_Control/Rubik_Control.h"
#include "../../Hardware/Servo_Control/Servo_Control.h"
#include <string.h>

static RubikProtocol protocol;
static bool stopped;

void UART_Command_Init(UART_HandleTypeDef *huart)
{
    RubikProtocol_Init(&protocol, huart);
    stopped = false;
    RubikProtocol_StartReceive(&protocol);
}

void UART_Command_RxCallback(UART_HandleTypeDef *huart)
{
    if (huart != NULL && huart == protocol.huart && huart->ErrorCode != HAL_UART_ERROR_NONE) {
        /* HAL still needs ErrorCode to decide whether to end RX (ORE).
         * It calls HAL_UART_ErrorCallback after this completion callback.
         * Rearming here would clear ErrorCode before HAL makes that decision. */
        return;
    }
    RubikProtocol_OnRxCplt(&protocol, huart);
}

void UART_Command_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart == NULL || huart != protocol.huart) {
        return;
    }
    HAL_UART_AbortReceive(huart);
    /* On STM32F4 an SR read followed by a DR read clears PE/FE/NE/ORE,
     * including errors raised without a completed RX byte. */
    __HAL_UART_CLEAR_OREFLAG(huart);
    if (!protocol.line_ready) {
        protocol.line_len = 0;
        protocol.overflow = false;
        protocol.invalid = false;
    }
    protocol.discard_line = true;
    RubikProtocol_StartReceive(&protocol);
}

static void process_move(const RubikCommand *command)
{
    const char *faces = "LRFBUD";
    void (*const clockwise[])(void) = {
        Rubik_Left, Rubik_Right, Rubik_Front, Rubik_Back, Rubik_UpToFront, NULL
    };
    void (*const inverse[])(void) = {
        Rubik_Left_, Rubik_Right_, Rubik_Front_, Rubik_Back_, NULL, NULL
    };
    const char *face = strchr(faces, command->face);
    if (face == NULL) {
        RubikProtocol_SendError(&protocol, "BAD_ARG", "face");
        return;
    }
    size_t index = (size_t)(face - faces);
    void (*motion)(void) = command->turns == -1 ? inverse[index] : clockwise[index];
    if (motion == NULL) {
        /* These source sequences are incomplete or fail the motion tests. */
        RubikProtocol_SendError(&protocol, "UNSUPPORTED", "motion_incomplete");
        return;
    }
    if (!RubikProtocol_SendLine(&protocol, "ACK")) {
        return;
    }
    uint32_t start = HAL_GetTick();
    int repeats = command->turns == 2 ? 2 : 1;
    for (int i = 0; i < repeats; ++i) {
        motion();
    }
    uint32_t elapsed = HAL_GetTick() - start;
    if (elapsed < command->duration_ms) {
        HAL_Delay(command->duration_ms - elapsed);
    }
    RubikProtocol_SendLine(&protocol, "DONE");
}

static void process_calibration(const RubikCommand *command)
{
    /* Use the named driver enums; UART position order must not define them. */
    static const struct {
        const char *name;
        Servo_Rotate_Position_t position;
    } rotate_positions[] = {
        {"HOME", SERVO_ROTATE_HOME},
        {"CLOCKWISE", SERVO_ROTATE_CLOCKWISE},
        {"ANTICLOCKWISE", SERVO_ROTATE_ANTICLOCKWISE}
    };
    static const struct {
        const char *name;
        Servo_Move_Position_t position;
    } move_positions[] = {
        {"FULL_RELEASE", SERVO_MOVE_FULL_RELEASE},
        {"HALF_RELEASE", SERVO_MOVE_HALF_RELEASE},
        {"CLAMP", SERVO_MOVE_CLAMP},
        {"TIGHT_CLAMP", SERVO_MOVE_TIGHT_CLAMP}
    };
    if (command->servo_id >= SERVO_COUNT) {
        RubikProtocol_SendError(&protocol, "BAD_ARG", "calib_servo");
        return;
    }
    Servo_ID_t id = (Servo_ID_t)command->servo_id;
    bool rotate = id >= SERVO_ROTATE_FRONT && id <= SERVO_ROTATE_LEFT;
    Servo_Rotate_Position_t rotate_position = SERVO_ROTATE_HOME;
    Servo_Move_Position_t move_position = SERVO_MOVE_FULL_RELEASE;
    bool found = false;
    if (rotate) {
        for (size_t i = 0; i < sizeof(rotate_positions) / sizeof(rotate_positions[0]); ++i) {
            if (strcmp(command->target, rotate_positions[i].name) == 0) {
                rotate_position = rotate_positions[i].position;
                found = true;
                break;
            }
        }
    } else {
        for (size_t i = 0; i < sizeof(move_positions) / sizeof(move_positions[0]); ++i) {
            if (strcmp(command->target, move_positions[i].name) == 0) {
                move_position = move_positions[i].position;
                found = true;
                break;
            }
        }
    }
    if (!found) {
        RubikProtocol_SendError(&protocol, "BAD_ARG", "calib_position");
        return;
    }
    if (!RubikProtocol_SendLine(&protocol, "ACK")) {
        return;
    }
    bool success;
    if (command->type == CALIB_CMD_SET) {
        if (rotate) {
            success = Servo_SetRotateCalibration(id, rotate_position, command->angle_deg);
        } else {
            success = Servo_SetMoveCalibration(id, move_position, command->angle_deg);
        }
    } else {
        if (rotate) {
            success = Servo_Rotate(id, rotate_position);
        } else {
            success = Servo_Move(id, move_position);
        }
    }
    if (!success) {
        RubikProtocol_SendError(&protocol, "LIMIT", "calib_servo");
        return;
    }
    if (command->type == CALIB_CMD_TEST) {
        /* Servo_Move/Rotate send PWM immediately. Match the settling time
         * used by Rubik_Control before acknowledging completion. */
        uint32_t start = HAL_GetTick();
        if (!waitUntilServosDone()) {
            RubikProtocol_SendError(&protocol, "LIMIT", "calib_wait");
            return;
        }
        uint32_t elapsed = HAL_GetTick() - start;
        if (elapsed < command->duration_ms) {
            HAL_Delay(command->duration_ms - elapsed);
        }
    }
    RubikProtocol_SendLine(&protocol, "DONE");
}

void UART_Command_Process(void)
{
    if (protocol.receive_retry) {
        uint32_t interrupt_state = __get_PRIMASK();
        __disable_irq();
        RubikProtocol_StartReceive(&protocol);
        __set_PRIMASK(interrupt_state);
    }
    RubikCommand command;
    if (!RubikProtocol_ReadCommand(&protocol, &command)) {
        return;
    }
    if (command.type == RUBIK_CMD_ERROR) {
        RubikProtocol_SendError(&protocol, "BAD_CMD", command.error);
        return;
    }
    if (stopped && (command.type == RUBIK_CMD_MOVE || command.type == RUBIK_CMD_TURN ||
                    command.type == RUBIK_CMD_SERVO || command.type == CALIB_CMD_TEST)) {
        RubikProtocol_SendError(&protocol, "STOPPED", "home_required");
        return;
    }
    switch (command.type) {
    case RUBIK_CMD_PING:
        RubikProtocol_SendLine(&protocol, "ACK");
        break;
    case RUBIK_CMD_STOP:
        stopped = true;
        RubikProtocol_SendLine(&protocol, "ACK");
        break;
    case RUBIK_CMD_HOME:
        if (RubikProtocol_SendLine(&protocol, "ACK")) {
            Rubik_Hold_Start_Position();
            stopped = false;
            RubikProtocol_SendLine(&protocol, "DONE");
        }
        break;
    case RUBIK_CMD_MOVE:
    case RUBIK_CMD_TURN:
        process_move(&command);
        break;
    case RUBIK_CMD_SERVO:
        if (RubikProtocol_SendLine(&protocol, "ACK")) {
            uint16_t ticks = (uint16_t)((uint32_t)command.pulse_us * 4096U / 20000U);
            PCA9685_SetPWM((uint8_t)command.channel, 0, ticks);
            HAL_Delay(command.duration_ms);
            RubikProtocol_SendLine(&protocol, "DONE");
        }
        break;
    case CALIB_CMD_SET:
    case CALIB_CMD_TEST:
        process_calibration(&command);
        break;
    default:
        RubikProtocol_SendError(&protocol, "UNSUPPORTED", command.operation);
        break;
    }
}
