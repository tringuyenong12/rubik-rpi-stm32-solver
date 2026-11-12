/*
 * PCA9685.h
 *
 *  Created on: Oct 24, 2026
 *      Author: Dell
 */

#ifndef PCA9685_PCA9685_H_
#define PCA9685_PCA9685_H_

#include "stm32f4xx_hal.h" //

extern I2C_HandleTypeDef hi2c1;

#define PCA9685_ADDRESS 0x80
// Datasheet link --> https://cdn-shop.adafruit.com/datasheets/PCA9685.pdf
#define PCA9685_MODE1         0x0         // as in the datasheet page no 10/52
#define PCA9685_PRE_SCALE     0xFE        // as in the datasheet page no 13/52
#define PCA9685_LED0_ON_L     0x6         // as in the datasheet page no 10/52
#define PCA9685_MODE1_SLEEP_BIT      4    // as in the datasheet page no 14/52
#define PCA9685_MODE1_AI_BIT         5    // as in the datasheet page no 14/52
#define PCA9685_MODE1_RESTART_BIT    7    // as in the datasheet page no 14/52


#define min_pulse 102.4f // tuong ung voi 0 do
#define max_pulse 511.9f // tuong ung voi 180 do
#define one_degree_pulse 2.275f

void PCA9685_SetBit(uint8_t Register, uint8_t Bit, uint8_t Value);
void PCA9685_SetPWMFrequency(uint16_t frequency);
void PCA9685_Init(uint16_t frequency);
void PCA9685_SetPWM(uint8_t Channel, uint16_t OnTime, uint16_t OffTime);
void PCA9685_SetServoAngle(uint8_t Channel, float Angle);
void PCA9685_SetServoAngleBonus(uint8_t Channel, float Angle, float Angle_Bonus);

#endif /* PCA9685_PCA9685_H_ */

