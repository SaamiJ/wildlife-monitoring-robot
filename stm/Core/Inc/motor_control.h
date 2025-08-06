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

#define MOTOR_LEFT_IN1_PIN      GPIO_PIN_4
#define MOTOR_LEFT_IN2_PIN      GPIO_PIN_5
#define MOTOR_GPIO_PORT         GPIOA

// Functions
void setSpeed(int16_t speed);

#endif /* INC_MOTOR_CONTROL_H_ */
