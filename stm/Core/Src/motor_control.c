/*
 * motor_control.c
 *
 *  Created on: Aug 6, 2025
 *      Author: Saami Junaidi
 */

#include "motor_control.h"

void setSpeed(int16_t speed, uint16_t in_a_pin, uint16_t in_b_pin, uint32_t tim_channel)
{
    if (speed >= 0) {
        HAL_GPIO_WritePin(MOTOR_GPIO_PORT, in_a_pin, GPIO_PIN_SET);
        HAL_GPIO_WritePin(MOTOR_GPIO_PORT, in_b_pin, GPIO_PIN_RESET);
    } else {
        HAL_GPIO_WritePin(MOTOR_GPIO_PORT, in_a_pin, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(MOTOR_GPIO_PORT, in_b_pin, GPIO_PIN_SET);
        speed = -speed;
    }

    if (speed > 1000) { speed = 1000; }

    __HAL_TIM_SET_COMPARE(&htim1, tim_channel, speed);

}

void Motor_SetSpeedLeft(int16_t speed)
{
	setSpeed(speed, MOTOR_LEFT_IN1_PIN, MOTOR_LEFT_IN2_PIN, TIM_CHANNEL_1);
}

void Motor_SetSpeedRight(int16_t speed)
{
	setSpeed(speed, MOTOR_RIGHT_IN3_PIN, MOTOR_RIGHT_IN4_PIN, TIM_CHANNEL_2);
}

void Motor_StopAll(void)
{
    /* Coast both motors: INx low, PWM = 0 */
    HAL_GPIO_WritePin(MOTOR_GPIO_PORT, MOTOR_LEFT_IN1_PIN|MOTOR_LEFT_IN2_PIN|
                                         MOTOR_RIGHT_IN3_PIN|MOTOR_RIGHT_IN4_PIN, GPIO_PIN_SET);
    __HAL_TIM_SET_COMPARE(&htim1, MOTOR_LEFT_PWM_CH, 0);
    __HAL_TIM_SET_COMPARE(&htim1, MOTOR_RIGHT_PWM_CH, 0);
}
