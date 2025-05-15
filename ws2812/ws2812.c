#include "main.h"
#include "ws2812.h"
#include "stm32f1xx_hal_tim.h"
#include "tim.h"
#include <stdint.h>

#define Code0   25
#define Code1   66
#define CodeReset   0

void ws2812_update(void){
    static uint16_t data1[] = {
        Code0, Code0,Code0, Code0,Code0, Code0,Code0, Code0,
        Code0, Code0,Code0, Code0,Code0, Code0,Code0, Code0,
        Code0, Code0,Code0, Code0,Code0, Code0,Code0, Code0,
    };

    static uint16_t data2[] = {
        Code0, Code0,Code0, Code0,Code0, Code0,Code0, Code0,
        Code0, Code0,Code0, Code0,Code0, Code0,Code0, Code0,
        Code0, Code0,Code0, Code0,Code0, Code0,Code0, Code0,
    };

    static uint16_t reset[] = {
        CodeReset,CodeReset,CodeReset,CodeReset,CodeReset,CodeReset,CodeReset,CodeReset,
        CodeReset,CodeReset,CodeReset,CodeReset,CodeReset,CodeReset,CodeReset,CodeReset,
        CodeReset,CodeReset,CodeReset,CodeReset,CodeReset,CodeReset,CodeReset,CodeReset,
    };

    // HAL_TIM_PWM_Start_DMA(&htim3, TIM_CHANNEL_3, (uint32_t *)data1, sizeof(data1)/sizeof(uint16_t));
    // HAL_TIM_PWM_Start_DMA(&htim3, TIM_CHANNEL_4, (uint32_t *)data2, sizeof(data2)/sizeof(uint16_t));

    HAL_TIM_PWM_Start_DMA(&htim3, TIM_CHANNEL_3, (uint32_t *)reset, sizeof(reset)/sizeof(uint16_t));
    HAL_TIM_PWM_Start_DMA(&htim3, TIM_CHANNEL_4, (uint32_t *)reset, sizeof(reset)/sizeof(uint16_t));
}








