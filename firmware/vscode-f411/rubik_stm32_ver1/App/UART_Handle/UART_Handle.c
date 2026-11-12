#include "UART_Handle.h"
#include "../rubik_protocol.h"
#include "../../Hardware/PCA9685/PCA9685.h"
#include "../../Hardware/Rubik_Control/Rubik_Control.h"
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
        UART_Command_ErrorCallback(huart);
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
    const char *const rotate_positions[] = {"HOME", "CLOCKWISE", "ANTICLOCKWISE"};
    const char *const move_positions[] = {"FULL_RELEASE", "HALF_RELEASE", "CLAMP", "TIGHT_CLAMP"};
    bool rotate = command->servo_id <= SERVO_ROTATE_LEFT;
    const char *const *positions = rotate ? rotate_positions : move_positions;
    size_t position_count = rotate ? 3 : 4;
    size_t position = 0;
    while (position < position_count && strcmp(command->target, positions[position]) != 0) {
        ++position;
    }
    if (position == position_count) {
        RubikProtocol_SendError(&protocol, "BAD_ARG", "calib_position");
        return;
    }
    if (!RubikProtocol_SendLine(&protocol, "ACK")) {
        return;
    }
    Servo_ID_t id = (Servo_ID_t)command->servo_id;
    bool success;
    if (command->type == CALIB_CMD_SET) {
        if (rotate) {
            success = Servo_SetRotateCalibration(id, (Servo_Rotate_Position_t)position, command->angle_deg);
        } else {
            success = Servo_SetMoveCalibration(id, (Servo_Move_Position_t)position, command->angle_deg);
        }
    } else {
        if (rotate) {
            success = Servo_Rotate(id, (Servo_Rotate_Position_t)position);
        } else {
            success = Servo_Move(id, (Servo_Move_Position_t)position);
        }
    }
    if (!success) {
        RubikProtocol_SendError(&protocol, "LIMIT", "calib_servo");
        return;
    }
    if (command->type == CALIB_CMD_TEST) {
        HAL_Delay(command->duration_ms);
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
