/*
 * motor_control.c
 *
 *  Created on: Aug 6, 2025
 *      Author: Saami Junaidi
 */

#include "motor_control.h"

void setSpeed(int16_t speed)
{
	if (speed >= 0)
	{
        HAL_GPIO_WritePin(MOTOR_GPIO_PORT, MOTOR_LEFT_IN1_PIN, GPIO_PIN_SET);
        HAL_GPIO_WritePin(MOTOR_GPIO_PORT, MOTOR_LEFT_IN2_PIN, GPIO_PIN_RESET);
	}
	else
	{
        HAL_GPIO_WritePin(MOTOR_GPIO_PORT, MOTOR_LEFT_IN1_PIN, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(MOTOR_GPIO_PORT, MOTOR_LEFT_IN2_PIN, GPIO_PIN_SET);
        speed = -speed;
	}

    if (speed > 1000) { speed = 1000; }

    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, speed);

}
