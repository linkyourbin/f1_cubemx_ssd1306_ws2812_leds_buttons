1：`ws2812`驱动：`PWM+DMA`
- 配置为`800KHz，1.25us`
![](config_images/pwm_dma.png)

2：`CH1116 SPI1`驱动

3: 使用环境为`arm-none-eabi-gcc+cmake+ninja+openocd/probe-rs`
- `openocd`和`probe-rs`的烧录均没问题
- `probe-rs`的调试还未跑通（没有完全跑通，能进调试，单步有效果，但是不如cortex debug舒服）

4：一些随手使用AI生成的小工具在`gif2pngbmp`文件夹下
- `gif2pngbmp/2in1.py`这个文件可以直接运行，主要功能
  - 1：如果是`GIF`，则先转换为`bmp`或`png`之后，再进行取模
  - 2：`png`或`bmp`则直接取模
  - 3：具体功能需要直接运行后查看，因为这是一个`GUI`版本的工具，只是还未打包发布
