/*
 * Day la snippet de chen vao Core/Src/main.c do STM32CubeIDE sinh ra.
 * Khong copy file nay de thay the main.c nguyen file.
 */

/* USER CODE BEGIN Includes */
#include "rubik_protocol.h"
#include "servo_controller.h"
/* USER CODE END Includes */

/* USER CODE BEGIN PV */
static RubikProtocol rubik_protocol;
static ServoController servo_controller;
/* USER CODE END PV */

/*
 * Trong main(), sau MX_USARTx_UART_Init() va MX_TIMx_Init().
 * Neu ban dung USART2/TIM3, doi huart1/htim2 thanh handle tuong ung.
 */
/* USER CODE BEGIN 2 */
RubikProtocol_Init(&rubik_protocol, &huart1);
ServoController_Init(&servo_controller, &htim2);
ServoController_Start(&servo_controller);
RubikProtocol_StartReceive(&rubik_protocol);
RubikProtocol_SendLine(&rubik_protocol, "OK BOOT");
/* USER CODE END 2 */

/*
 * Trong while (1), thay noi dung block USER CODE WHILE bang vong lap nay.
 */
/* USER CODE BEGIN WHILE */
while (1)
{
    RubikCommand command;
    if (RubikProtocol_ReadCommand(&rubik_protocol, &command)) {
        switch (command.type) {
        case RUBIK_CMD_PING:
            RubikProtocol_SendLine(&rubik_protocol, "OK PONG");
            break;

        case RUBIK_CMD_HOME:
            RubikProtocol_SendLine(&rubik_protocol, "OK HOME");
            ServoController_Home(&servo_controller);
            HAL_Delay(500);
            RubikProtocol_SendLine(&rubik_protocol, "DONE HOME");
            break;

        case RUBIK_CMD_STOP:
            ServoController_Stop(&servo_controller);
            RubikProtocol_SendLine(&rubik_protocol, "OK STOP");
            break;

        case RUBIK_CMD_SERVO:
            if (ServoController_WriteUs(&servo_controller, command.channel, command.pulse_us)) {
                RubikProtocol_SendLine(&rubik_protocol, "OK SERVO");
                HAL_Delay(command.duration_ms);
                RubikProtocol_SendLine(&rubik_protocol, "DONE SERVO");
            } else {
                RubikProtocol_SendError(&rubik_protocol, "LIMIT", "servo_range");
            }
            break;

        case RUBIK_CMD_MOVE:
            if (ServoController_MoveFace(&servo_controller, command.face, command.turns, command.duration_ms)) {
                RubikProtocol_SendLine(&rubik_protocol, "OK MOVE");
                RubikProtocol_SendLine(&rubik_protocol, "DONE MOVE");
            } else {
                RubikProtocol_SendError(&rubik_protocol, "BAD_ARG", "move");
            }
            break;

        case RUBIK_CMD_ACTUATOR:
            /*
             * Placeholder cho 4 cum truot cheo va cum trung tam.
             * Sau khi chot motor/driver, map command.role + command.target
             * sang stepper/DC/servo sequence that.
             */
            RubikProtocol_SendLine(&rubik_protocol, "OK ACTUATOR");
            HAL_Delay(command.duration_ms);
            RubikProtocol_SendLine(&rubik_protocol, "DONE ACTUATOR");
            break;

        case RUBIK_CMD_CLAMP:
            /*
             * Placeholder cho tool_nw/tool_ne/tool_sw/tool_se open/close.
             */
            RubikProtocol_SendLine(&rubik_protocol, "OK CLAMP");
            RubikProtocol_SendLine(&rubik_protocol, "DONE CLAMP");
            break;

        case RUBIK_CMD_TURN:
            if (ServoController_MoveFace(&servo_controller, command.face, command.turns, command.duration_ms)) {
                RubikProtocol_SendLine(&rubik_protocol, "OK TURN");
                RubikProtocol_SendLine(&rubik_protocol, "DONE TURN");
            } else {
                RubikProtocol_SendError(&rubik_protocol, "BAD_ARG", "turn");
            }
            break;

        case RUBIK_CMD_SCAN_POSE:
            /*
             * Placeholder de dua cube ve tu the chup mat U/R/F/D/L/B.
             */
            RubikProtocol_SendLine(&rubik_protocol, "OK SCAN_POSE");
            RubikProtocol_SendLine(&rubik_protocol, "DONE SCAN_POSE");
            break;

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
 * Them callback nay vao Core/Src/main.c.
 */
/* USER CODE BEGIN 4 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    RubikProtocol_OnRxCplt(&rubik_protocol, huart);
}
/* USER CODE END 4 */

