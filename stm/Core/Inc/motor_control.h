/*
 * motor_control.h
 *
 *  Created on: Aug 6, 2025
 *      Author: Saami Junaidi
 */

#ifndef INC_MOTOR_CONTROL_H_
#define INC_MOTOR_CONTROL_H_

// Includes

#include "main.h"
#include "stm32l4xx_hal.h"

// Defines

#define MOTOR_LEFT_PWM_CH       TIM_CHANNEL_1   // ENA
#define MOTOR_RIGHT_PWM_CH      TIM_CHANNEL_2   // ENB

#define MOTOR_LEFT_IN1_PIN      GPIO_PIN_4     // IN1  (left)
#define MOTOR_LEFT_IN2_PIN      GPIO_PIN_5     // IN2  (left)
#define MOTOR_RIGHT_IN3_PIN     GPIO_PIN_6     // IN3  (right)
#define MOTOR_RIGHT_IN4_PIN		GPIO_PIN_7     // IN4  (right)
#define MOTOR_GPIO_PORT         GPIOA

// Functions
void setSpeed(int16_t speed, uint16_t in_a_pin, uint16_t in_b_pin, uint32_t tim_channel);
void Motor_SetSpeedLeft(int16_t speed);
void Motor_SetSpeedRight(int16_t speed);
void Motor_StopAll(void);

#endif /* INC_MOTOR_CONTROL_H_ */
