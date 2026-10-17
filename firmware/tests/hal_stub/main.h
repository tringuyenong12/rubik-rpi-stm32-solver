#ifndef TEST_MAIN_H
#define TEST_MAIN_H
#include <stdint.h>

#define TIM_CHANNEL_1 0u
#define TIM_CHANNEL_2 4u
#define TIM_CHANNEL_3 8u
#define TIM_CHANNEL_4 12u

typedef struct {
    uint32_t ARR;
    uint32_t CCR[4];
    unsigned running[4];
} TIM_TypeDef;
typedef struct { TIM_TypeDef *Instance; } TIM_HandleTypeDef;
typedef struct { void *Instance; } UART_HandleTypeDef;
typedef enum { HAL_OK = 0, HAL_ERROR = 1 } HAL_StatusTypeDef;

void test_set_compare(TIM_HandleTypeDef *timer, uint32_t channel, uint32_t value);
#define __HAL_TIM_SET_COMPARE(timer, channel, value) test_set_compare(timer, channel, value)
#define __HAL_TIM_GET_AUTORELOAD(timer) ((timer)->Instance->ARR)
HAL_StatusTypeDef HAL_TIM_PWM_Start(TIM_HandleTypeDef *timer, uint32_t channel);
HAL_StatusTypeDef HAL_TIM_PWM_Stop(TIM_HandleTypeDef *timer, uint32_t channel);
void HAL_Delay(uint32_t ms);
#endif
