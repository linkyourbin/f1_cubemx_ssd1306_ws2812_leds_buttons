1：ws2812驱动：PWM+DMA
- 配置为800KHz，1.25us
![](config_images/pwm_dma.png)

2：CH1116 SPI1驱动

3: 使用环境为arm-none-eabi-gcc+cmake+ninja+openocd/probe-rs
- openocd和probe-rs的烧录均没问题
- probe-rs的调试还未跑通（没有完全跑通，能进调试，单步有效果，但是不如cortex debug舒服）


