#include "stm32f1xx_hal.h"
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

UART_HandleTypeDef huart1;
TIM_HandleTypeDef htim2;

static char rx_line[96];
static uint8_t rx_byte;
static size_t rx_len = 0;
static volatile bool line_ready = false;

static void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_TIM2_Init(void);
static void send_line(const char *line);
static void process_line(char *line);
static void servo_write_us(uint32_t channel, uint16_t pulse_us);

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART1_UART_Init();
    MX_TIM2_Init();

    HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_2);
    HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_3);
    HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_4);
    HAL_UART_Receive_IT(&huart1, &rx_byte, 1);

    send_line("OK BOOT");

    while (1) {
        if (line_ready) {
            line_ready = false;
            process_line(rx_line);
            rx_len = 0;
            memset(rx_line, 0, sizeof(rx_line));
        }
    }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1) {
        if (rx_byte == '\n' || rx_byte == '\r') {
            if (rx_len > 0) {
                rx_line[rx_len] = '\0';
                line_ready = true;
            }
        } else if (rx_len < sizeof(rx_line) - 1) {
            rx_line[rx_len++] = (char)rx_byte;
        } else {
            rx_len = 0;
            send_line("ERR BAD_CMD line_too_long");
        }
        HAL_UART_Receive_IT(&huart1, &rx_byte, 1);
    }
}

static void process_line(char *line)
{
    char *cmd = strtok(line, " ");
    if (cmd == NULL) {
        send_line("ERR BAD_CMD empty");
        return;
    }

    if (strcmp(cmd, "PING") == 0) {
        send_line("OK PONG");
        return;
    }

    if (strcmp(cmd, "HOME") == 0) {
        send_line("OK HOME");
        for (uint32_t ch = 0; ch < 4; ch++) {
            servo_write_us(ch, 1500);
        }
        HAL_Delay(500);
        send_line("DONE HOME");
        return;
    }

    if (strcmp(cmd, "STOP") == 0) {
        send_line("OK STOP");
        return;
    }

    if (strcmp(cmd, "SERVO") == 0) {
        char *channel_s = strtok(NULL, " ");
        char *pulse_s = strtok(NULL, " ");
        char *duration_s = strtok(NULL, " ");
        if (channel_s == NULL || pulse_s == NULL || duration_s == NULL) {
            send_line("ERR BAD_ARG servo_args");
            return;
        }

        uint32_t channel = (uint32_t)strtoul(channel_s, NULL, 10);
        uint16_t pulse_us = (uint16_t)strtoul(pulse_s, NULL, 10);
        uint32_t duration_ms = (uint32_t)strtoul(duration_s, NULL, 10);
        if (channel > 3 || pulse_us < 500 || pulse_us > 2500) {
            send_line("ERR LIMIT servo_range");
            return;
        }

        send_line("OK SERVO");
        servo_write_us(channel, pulse_us);
        HAL_Delay(duration_ms);
        send_line("DONE SERVO");
        return;
    }

    if (strcmp(cmd, "MOVE") == 0) {
        char *face = strtok(NULL, " ");
        char *turns_s = strtok(NULL, " ");
        char *duration_s = strtok(NULL, " ");
        if (face == NULL || turns_s == NULL || duration_s == NULL) {
            send_line("ERR BAD_ARG move_args");
            return;
        }

        int turns = atoi(turns_s);
        uint32_t duration_ms = (uint32_t)strtoul(duration_s, NULL, 10);
        if (strchr("URFDLB", face[0]) == NULL || face[1] != '\0') {
            send_line("ERR BAD_ARG face");
            return;
        }
        if (!(turns == 1 || turns == -1 || turns == 2)) {
            send_line("ERR BAD_ARG turns");
            return;
        }

        send_line("OK MOVE");
        /* TODO: map face/turns to the real servo sequence after mechanical design is fixed. */
        HAL_Delay(duration_ms);
        send_line("DONE MOVE");
        return;
    }

    send_line("ERR BAD_CMD unknown");
}

static void send_line(const char *line)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)line, strlen(line), HAL_MAX_DELAY);
    HAL_UART_Transmit(&huart1, (uint8_t *)"\n", 1, HAL_MAX_DELAY);
}

static void servo_write_us(uint32_t channel, uint16_t pulse_us)
{
    uint32_t tim_channel = TIM_CHANNEL_1;
    if (channel == 1) {
        tim_channel = TIM_CHANNEL_2;
    } else if (channel == 2) {
        tim_channel = TIM_CHANNEL_3;
    } else if (channel == 3) {
        tim_channel = TIM_CHANNEL_4;
    }
    __HAL_TIM_SET_COMPARE(&htim2, tim_channel, pulse_us);
}

static void MX_TIM2_Init(void)
{
    TIM_OC_InitTypeDef sConfigOC = {0};

    htim2.Instance = TIM2;
    htim2.Init.Prescaler = 71;
    htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim2.Init.Period = 19999;
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    HAL_TIM_PWM_Init(&htim2);

    sConfigOC.OCMode = TIM_OCMODE_PWM1;
    sConfigOC.Pulse = 1500;
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
    HAL_TIM_PWM_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_1);
    HAL_TIM_PWM_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_2);
    HAL_TIM_PWM_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_3);
    HAL_TIM_PWM_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_4);
}

static void MX_USART1_UART_Init(void)
{
    huart1.Instance = USART1;
    huart1.Init.BaudRate = 115200;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart1.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&huart1);
}

static void MX_GPIO_Init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
}

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
    HAL_RCC_OscConfig(&RCC_OscInitStruct);

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                                  RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2);
}

void SysTick_Handler(void)
{
    HAL_IncTick();
}

void USART1_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart1);
}

void TIM2_IRQHandler(void)
{
    HAL_TIM_IRQHandler(&htim2);
}

void Error_Handler(void)
{
    __disable_irq();
    while (1) {
    }
}

