/*
 * Insert these blocks into the matching USER CODE regions of Core/Src/main.c.
 * This is for STM32F411CEU6 USART2 (PA2/PA3) and the 8-servo mechanism.
 * Do not replace a CubeMX-generated main.c with this file.
 */

/* USER CODE BEGIN Includes */
#include "rubik_binary_protocol.h"
#include "rubik_motion.h"
/* USER CODE END Includes */

/* USER CODE BEGIN PFP */
/* This function is supplied by the project's PWM/PCA9685 servo driver.
 * It must accept indexes 0..7 and angles 0..180 degrees. */
extern void servoAngle(int servo_index, int angle_deg);
/* USER CODE END PFP */

/* USER CODE BEGIN PV */
static RubikBinaryProtocol rubik_protocol;
/* USER CODE END PV */

/* In main(), after MX_USART2_UART_Init() and after the servo driver init: */
/* USER CODE BEGIN 2 */
RubikMotion_Init(servoAngle);
RubikBinaryProtocol_Init(&rubik_protocol, &huart2);
RubikBinaryProtocol_StartReceive(&rubik_protocol);
/* USER CODE END 2 */

/* Replace the body in USER CODE BEGIN WHILE with this loop. */
/* USER CODE BEGIN WHILE */
while (1)
{
    uint8_t sequence;
    uint8_t command;

    if (RubikBinaryProtocol_TakeCommand(&rubik_protocol, &sequence, &command)) {
        if (!RubikMotion_IsSupported(command)) {
            RubikBinaryProtocol_SendStatus(&rubik_protocol, sequence, RUBIK_UART_ERROR);
            RubikBinaryProtocol_AbortActive(&rubik_protocol);
        } else {
            /* ACK is sent before motion; DONE is sent only after every servo
             * delay in the move has finished. */
            RubikBinaryProtocol_SendStatus(&rubik_protocol, sequence, RUBIK_UART_ACK);
            if (RubikMotion_Execute(command)) {
                RubikBinaryProtocol_MarkCompleted(&rubik_protocol, sequence, command);
                RubikBinaryProtocol_SendStatus(&rubik_protocol, sequence, RUBIK_UART_DONE);
            } else {
                RubikBinaryProtocol_SendStatus(&rubik_protocol, sequence, RUBIK_UART_ERROR);
                RubikBinaryProtocol_AbortActive(&rubik_protocol);
            }
        }
    }

    /* A duplicate sequence received after a lost DONE is answered with DONE,
     * not performed a second time. */
    if (RubikBinaryProtocol_TakeDoneReplay(&rubik_protocol, &sequence)) {
        RubikBinaryProtocol_SendStatus(&rubik_protocol, sequence, RUBIK_UART_DONE);
    }
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
}
/* USER CODE END 3 */

/* USER CODE BEGIN 4 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    RubikBinaryProtocol_OnRxCplt(&rubik_protocol, huart);
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    RubikBinaryProtocol_OnError(&rubik_protocol, huart);
}
/* USER CODE END 4 */
