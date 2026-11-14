#ifndef UART_TEST_HAL_H_
#define UART_TEST_HAL_H_
#include <stdint.h>
typedef struct { uint32_t ErrorCode; } UART_HandleTypeDef;
typedef struct { unsigned unused; } I2C_HandleTypeDef;
typedef enum { HAL_OK, HAL_ERROR, HAL_BUSY, HAL_TIMEOUT } HAL_StatusTypeDef;
#define HAL_UART_ERROR_NONE 0U
static inline void __DMB(void) {}
static inline uint32_t __get_PRIMASK(void) { return 0; }
static inline void __disable_irq(void) {}
static inline void __set_PRIMASK(uint32_t mask) { (void)mask; }
HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *, uint8_t *, uint16_t);
HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *, uint8_t *, uint16_t, uint32_t);
HAL_StatusTypeDef HAL_UART_AbortReceive(UART_HandleTypeDef *);
uint32_t HAL_GetTick(void);
void HAL_Delay(uint32_t);
void HAL_UART_ErrorCallback(UART_HandleTypeDef *);
#endif
