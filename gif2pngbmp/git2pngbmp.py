import os
from PIL import Image

def process_gif(gif_path, output_png_dir, output_bmp_dir, is_bw=False, threshold=128):
    """
    处理GIF文件，调整大小并保存各帧为PNG和BMP格式
    
    参数:
    gif_path (str): 输入GIF文件路径
    output_png_dir (str): 输出PNG文件的目录
    output_bmp_dir (str): 输出BMP文件的目录
    is_bw (bool): 是否转换为黑白模式
    threshold (int): 黑白转换阈值 (0-255)
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_png_dir, exist_ok=True)
        os.makedirs(output_bmp_dir, exist_ok=True)
        
        # 打开GIF文件
        with Image.open(gif_path) as gif:
            frame_count = 0
            
            # 获取GIF的持续时间（用于动画）
            duration = gif.info.get('duration', 100)
            
            # 遍历每一帧
            while True:
                # 调整图像大小为128x64
                frame = gif.copy()
                frame = frame.resize((128, 64), Image.Resampling.LANCZOS)
                
                # 转换为黑白模式（如果需要）
                if is_bw:
                    # 先转换为灰度图
                    frame = frame.convert("L")
                    # 使用阈值进行二值化
                    frame = frame.point(lambda x: 255 if x > threshold else 0, '1')
                
                # 保存为PNG格式
                png_path = os.path.join(output_png_dir, f"frame_{frame_count:03d}.png")
                frame.save(png_path, "PNG")
                
                # 保存为BMP格式
                bmp_path = os.path.join(output_bmp_dir, f"frame_{frame_count:03d}.bmp")
                frame.save(bmp_path, "BMP")
                
                # 打印进度
                print(f"已处理帧 {frame_count+1}", end='\r')
                
                frame_count += 1
                
                # 尝试移动到下一帧
                try:
                    gif.seek(frame_count)
                except EOFError:
                    break
        
        print(f"\n处理完成! 共{frame_count}帧，每帧持续时间: {duration}ms")
        print(f"PNG文件保存在: {output_png_dir}")
        print(f"BMP文件保存在: {output_bmp_dir}")
        
        # 保存帧持续时间信息（用于动画）
        with open(os.path.join(output_png_dir, "frame_info.txt"), 'w') as f:
            f.write(f"总帧数: {frame_count}\n")
            f.write(f"每帧持续时间: {duration}ms\n")
    
    except Exception as e:
        print(f"处理过程中发生错误: {e}")

if __name__ == "__main__":
    # 用户需要修改这些路径
    input_gif = "C:/Users/Admin/Desktop/f1_cubemx_test/gif2pngbmp/chiikawa.gif"  # 输入的GIF文件路径
    png_directory = "C:/Users/Admin/Desktop/f1_cubemx_test/gif2pngbmp/png_output"  # 输出PNG文件的目录
    bmp_directory = "C:/Users/Admin/Desktop/f1_cubemx_test/gif2pngbmp/bmp_output"  # 输出BMP文件的目录
    
    # 是否转换为黑白模式
    convert_to_bw = True
    
    # 黑白转换阈值 (0-255)，值越低图像越白
    threshold_value = 128
    
    process_gif(input_gif, png_directory, bmp_directory, convert_to_bw, threshold_value)    
    
    
    
    
    
    
    
    