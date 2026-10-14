/*
 * Day la snippet de chen vao Core/Src/main.c do STM32CubeIDE sinh ra.
 * Khong copy file nay de thay the main.c nguyen file.
 *
 * Neu ban dung USART2 hoac TIM3, doi huart1/htim2 thanh handle tuong ung.
 */

/* USER CODE BEGIN Includes */
#include "rubik_protocol.h"
#include "servo_controller.h"
#include <string.h>
/* USER CODE END Includes */

/* USER CODE BEGIN PV */
static RubikProtocol  rubik_protocol;
static ServoController servo_controller;
/* USER CODE END PV */

/*
 * Trong main(), sau MX_USARTx_UART_Init() va MX_TIMx_Init().
 */
/* USER CODE BEGIN 2 */
RubikProtocol_Init(&rubik_protocol, &huart1);
ServoController_Init(&servo_controller, &htim2);
/* Bat buoc: ConfigChannel (neu them timer), ConfigProfile cho tung servo
 * voi so do that; ConfigAngles neu dung WriteAngle. Xem SERVO_CONTROLLER_GUIDE.md.
 * Khong co profile -> Start tra false, khong bat PWM. */
bool servo_ready = ServoController_Start(&servo_controller);
RubikProtocol_StartReceive(&rubik_protocol);
if (servo_ready) {
    RubikProtocol_SendLine(&rubik_protocol, "OK BOOT");
} else {
    RubikProtocol_SendError(&rubik_protocol, "CONFIG", "servo_not_ready");
}
/* USER CODE END 2 */

/*
 * Trong while (1) - thay noi dung block USER CODE WHILE bang vong lap nay.
 */
/* USER CODE BEGIN WHILE */
while (1)
{
    RubikCommand command;
    if (RubikProtocol_ReadCommand(&rubik_protocol, &command)) {
        switch (command.type) {

        /* ---------------------------------------------------------------
         * PING - kiem tra ket noi
         * --------------------------------------------------------------- */
        case RUBIK_CMD_PING:
            RubikProtocol_SendLine(&rubik_protocol, "OK PONG");
            break;

        /* ---------------------------------------------------------------
         * HOME - dua tat ca actuator ve home
         * --------------------------------------------------------------- */
        case RUBIK_CMD_HOME:
            RubikProtocol_SendLine(&rubik_protocol, "OK HOME");
            if (ServoController_Home(&servo_controller)) {
                HAL_Delay(500u); /* Thoi gian cho uoc luong, khong co feedback. */
                RubikProtocol_SendLine(&rubik_protocol, "DONE HOME");
            } else {
                RubikProtocol_SendError(&rubik_protocol, "CONFIG", "home_failed");
            }
            break;

        /* ---------------------------------------------------------------
         * STOP - khoa lenh moi, giu PWM cu; khong phai dung khan cap
         * --------------------------------------------------------------- */
        case RUBIK_CMD_STOP:
            ServoController_Stop(&servo_controller);
            RubikProtocol_SendLine(&rubik_protocol, "OK STOP");
            break;

        /* ---------------------------------------------------------------
         * SERVO <channel> <pulse_us> <duration_ms>
         * Dung de calibration / debug tung kenh PWM truc tiep.
         * --------------------------------------------------------------- */
        case RUBIK_CMD_SERVO:
            if (ServoController_WriteUs(&servo_controller,
                                        command.channel,
                                        command.pulse_us)) {
                RubikProtocol_SendLine(&rubik_protocol, "OK SERVO");
                HAL_Delay(command.duration_ms);
                RubikProtocol_SendLine(&rubik_protocol, "DONE SERVO");
            } else {
                RubikProtocol_SendError(&rubik_protocol, "LIMIT", "servo_range");
            }
            break;

        /* ---------------------------------------------------------------
         * MOVE <face> <turns> <duration_ms>
         * Lenh cu, giu de tuong thich. Thuc chat goi TurnFace.
         * --------------------------------------------------------------- */
        case RUBIK_CMD_MOVE:
            if (ServoController_MoveFace(&servo_controller,
                                         command.face,
                                         command.turns,
                                         command.duration_ms)) {
                RubikProtocol_SendLine(&rubik_protocol, "OK MOVE");
                RubikProtocol_SendLine(&rubik_protocol, "DONE MOVE");
            } else {
                RubikProtocol_SendError(&rubik_protocol, "UNSUPPORTED", "move_sequence");
            }
            break;

        /* ---------------------------------------------------------------
         * ACTUATOR <role> <target> <duration_ms>
         * Di chuyen mot actuator logic den vi tri chi dinh.
         * --------------------------------------------------------------- */
        case RUBIK_CMD_ACTUATOR: {
            ServoRole   role;
            ServoTarget target;

            if (!ServoRole_FromString(command.role, &role)) {
                RubikProtocol_SendError(&rubik_protocol, "BAD_ARG", "role");
                break;
            }
            if (!ServoTarget_FromString(command.target, &target)) {
                RubikProtocol_SendError(&rubik_protocol, "BAD_ARG", "target");
                break;
            }

            RubikProtocol_SendLine(&rubik_protocol, "OK ACTUATOR");
            if (ServoController_WriteRole(&servo_controller, role, target)) {
                HAL_Delay(command.duration_ms);
                RubikProtocol_SendLine(&rubik_protocol, "DONE ACTUATOR");
            } else {
                RubikProtocol_SendError(&rubik_protocol, "LIMIT", "actuator_range");
            }
            break;
        }

        /* ---------------------------------------------------------------
         * CLAMP <role> <open|close>
         * Mo/dong dau kep theo role.
         * --------------------------------------------------------------- */
        case RUBIK_CMD_CLAMP: {
            ServoRole role;

            if (!ServoRole_FromString(command.role, &role)) {
                RubikProtocol_SendError(&rubik_protocol, "BAD_ARG", "clamp_role");
                break;
            }

            /* command.target la "open" hoac "close" */
            if (strcmp(command.target, "open") != 0 &&
                strcmp(command.target, "close") != 0) {
                RubikProtocol_SendError(&rubik_protocol, "BAD_ARG", "clamp_target");
                break;
            }
            bool do_close = (strcmp(command.target, "close") == 0);

            RubikProtocol_SendLine(&rubik_protocol, "OK CLAMP");
            if (ServoController_Clamp(&servo_controller, role, do_close)) {
                HAL_Delay(150u); /* delay ngan de co khi dap ung */
                RubikProtocol_SendLine(&rubik_protocol, "DONE CLAMP");
            } else {
                RubikProtocol_SendError(&rubik_protocol, "BAD_ARG", "clamp_role_invalid");
            }
            break;
        }

        /* ---------------------------------------------------------------
         * TURN <face> <turns> <duration_ms>
         * Xoay mot mat Rubik bang actuator that.
         * --------------------------------------------------------------- */
        case RUBIK_CMD_TURN:
            RubikProtocol_SendLine(&rubik_protocol, "OK TURN");
            if (ServoController_TurnFace(&servo_controller,
                                          command.face,
                                          command.turns,
                                          command.duration_ms)) {
                RubikProtocol_SendLine(&rubik_protocol, "DONE TURN");
            } else {
                RubikProtocol_SendError(&rubik_protocol, "UNSUPPORTED", "turn_sequence");
            }
            break;

        /* ---------------------------------------------------------------
         * SCAN_POSE <face>
         * Dua cube ve tu the de camera chup mat chi dinh.
         * --------------------------------------------------------------- */
        case RUBIK_CMD_SCAN_POSE:
            RubikProtocol_SendLine(&rubik_protocol, "OK SCAN_POSE");
            if (ServoController_ScanPose(&servo_controller, command.face)) {
                RubikProtocol_SendLine(&rubik_protocol, "DONE SCAN_POSE");
            } else {
                RubikProtocol_SendError(&rubik_protocol, "UNSUPPORTED", "scan_sequence");
            }
            break;

        /* ---------------------------------------------------------------
         * Loi parse hoac lenh khong xac dinh
         * --------------------------------------------------------------- */
        case RUBIK_CMD_ERROR:
        default:
            RubikProtocol_SendError(&rubik_protocol, "BAD_CMD", command.error);
            break;
        }
    }

    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
}
/* USER CODE END 3 */

/*
 * Them callback nay vao Core/Src/main.c (ngoai while loop).
 */
/* USER CODE BEGIN 4 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    RubikProtocol_OnRxCplt(&rubik_protocol, huart);
}
/* USER CODE END 4 */
