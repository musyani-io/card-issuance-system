#include "servo.h"

extern TIM_HandleTypeDef htim1;

static void Servo_SetAngle(uint8_t angle)
{
    uint16_t pulse;

    if(angle > 180)
        angle = 180;

    pulse = 1000 + ((uint32_t)angle * 1000) / 180;

    __HAL_TIM_SET_COMPARE(
        &htim1,
        TIM_CHANNEL_1,
        pulse
    );
}

void CardServo_Init(void)
{
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);

    Servo_SetAngle(90);
}

void CardServo_Open(void)
{
    Servo_SetAngle(180);
}

void CardServo_Close(void)
{
    Servo_SetAngle(0);
}