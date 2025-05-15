#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import numpy as np
import os
import glob
import re
import threading

def natural_sort_key(s):
    """用于自然排序的键函数，确保文件按照人类直觉的顺序排序（如1, 2, 10而不是1, 10, 2）"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

class BatchImageConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SSD1306 OLED 批量图像取模工具")
        self.root.geometry("900x700")
        
        self.image_files = []
        self.current_preview_index = 0
        self.output_path = None
        self.processing_thread = None
        
        self.create_widgets()
    
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 选择图像按钮
        ttk.Button(control_frame, text="选择单个图像", command=self.select_images).pack(fill=tk.X, pady=5)
        ttk.Button(control_frame, text="选择文件夹", command=self.select_folder).pack(fill=tk.X, pady=5)
        
        # 文件列表
        ttk.Label(control_frame, text="已选择的文件:").pack(anchor=tk.W, pady=(10, 0))
        
        list_frame = ttk.Frame(control_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.file_listbox = tk.Listbox(list_frame, height=10)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        
        # 文件操作按钮
        file_buttons_frame = ttk.Frame(control_frame)
        file_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(file_buttons_frame, text="上移", command=self.move_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_buttons_frame, text="下移", command=self.move_down).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_buttons_frame, text="删除", command=self.remove_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_buttons_frame, text="清空", command=self.clear_files).pack(side=tk.LEFT, padx=2)
        
        # 变量名前缀
        ttk.Label(control_frame, text="变量名前缀:").pack(anchor=tk.W, pady=(10, 0))
        self.prefix_var = tk.StringVar(value="frame")
        ttk.Entry(control_frame, textvariable=self.prefix_var).pack(fill=tk.X, pady=5)
        
        # 阈值滑块
        ttk.Label(control_frame, text="阈值:").pack(anchor=tk.W, pady=(10, 0))
        self.threshold_var = tk.IntVar(value=128)
        threshold_slider = ttk.Scale(control_frame, from_=0, to=255, variable=self.threshold_var, 
                                     orient=tk.HORIZONTAL, command=self.update_preview)
        threshold_slider.pack(fill=tk.X, pady=5)
        ttk.Label(control_frame, textvariable=self.threshold_var).pack()
        
        # 反转颜色复选框
        self.invert_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="反转颜色", variable=self.invert_var, 
                         command=self.update_preview).pack(anchor=tk.W, pady=5)
        
        # 输出选项
        options_frame = ttk.LabelFrame(control_frame, text="输出选项", padding="5")
        options_frame.pack(fill=tk.X, pady=10)
        
        self.header_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="生成头文件 (.h)", 
                         variable=self.header_var).pack(anchor=tk.W)
        
        self.array_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="生成指针数组", 
                         variable=self.array_var).pack(anchor=tk.W)
        
        # 转换按钮
        ttk.Button(control_frame, text="转换并保存", command=self.convert_and_save).pack(fill=tk.X, pady=10)
        
        # 右侧预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="预览", padding="10")
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 预览导航
        nav_frame = ttk.Frame(preview_frame)
        nav_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(nav_frame, text="上一个", command=self.prev_image).pack(side=tk.LEFT, padx=5)
        self.preview_label = ttk.Label(nav_frame, text="预览 0/0")
        self.preview_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="下一个", command=self.next_image).pack(side=tk.LEFT, padx=5)
        
        # 图像预览
        self.preview_canvas = tk.Canvas(preview_frame, bg="white", width=256, height=128)
        self.preview_canvas.pack(pady=10)
        
        # 代码预览
        ttk.Label(preview_frame, text="C 代码预览:").pack(anchor=tk.W, pady=(10, 0))
        self.code_preview = tk.Text(preview_frame, height=20, width=60)
        self.code_preview.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", 
                                           length=100, mode="determinate", 
                                           variable=self.progress_var)
        self.progress_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def select_images(self):
        file_paths = filedialog.askopenfilenames(
            title="选择图像文件",
            filetypes=[("图像文件", "*.png;*.bmp;*.jpg;*.jpeg"), ("所有文件", "*.*")]
        )
        
        if file_paths:
            for file_path in file_paths:
                if file_path not in self.image_files:
                    self.image_files.append(file_path)
            
            self.update_file_list()
            self.status_var.set(f"已添加 {len(file_paths)} 个文件")
    
    def select_folder(self):
        folder_path = filedialog.askdirectory(title="选择包含图像的文件夹")
        
        if folder_path:
            # 获取文件夹中的所有图像文件
            extensions = ['.png', '.bmp', '.jpg', '.jpeg']
            new_files = []
            
            for ext in extensions:
                new_files.extend(glob.glob(os.path.join(folder_path, f"*{ext}")))
                new_files.extend(glob.glob(os.path.join(folder_path, f"*{ext.upper()}")))
            
            # 按自然顺序排序
            new_files.sort(key=natural_sort_key)
            
            # 添加到列表中
            added_count = 0
            for file_path in new_files:
                if file_path not in self.image_files:
                    self.image_files.append(file_path)
                    added_count += 1
            
            self.update_file_list()
            self.status_var.set(f"已从文件夹添加 {added_count} 个文件")
    
    def update_file_list(self):
        self.file_listbox.delete(0, tk.END)
        for file_path in self.image_files:
            self.file_listbox.insert(tk.END, os.path.basename(file_path))
        
        if self.image_files:
            self.current_preview_index = 0
            self.update_preview()
    
    def on_file_select(self, event):
        selection = self.file_listbox.curselection()
        if selection:
            self.current_preview_index = selection[0]
            self.update_preview()
    
    def move_up(self):
        selection = self.file_listbox.curselection()
        if selection and selection[0] > 0:
            idx = selection[0]
            self.image_files[idx], self.image_files[idx-1] = self.image_files[idx-1], self.image_files[idx]
            self.update_file_list()
            self.file_listbox.selection_set(idx-1)
            self.current_preview_index = idx-1
            self.update_preview()
    
    def move_down(self):
        selection = self.file_listbox.curselection()
        if selection and selection[0] < len(self.image_files) - 1:
            idx = selection[0]
            self.image_files[idx], self.image_files[idx+1] = self.image_files[idx+1], self.image_files[idx]
            self.update_file_list()
            self.file_listbox.selection_set(idx+1)
            self.current_preview_index = idx+1
            self.update_preview()
    
    def remove_file(self):
        selection = self.file_listbox.curselection()
        if selection:
            idx = selection[0]
            del self.image_files[idx]
            self.update_file_list()
            if self.image_files:
                new_idx = min(idx, len(self.image_files) - 1)
                self.file_listbox.selection_set(new_idx)
                self.current_preview_index = new_idx
                self.update_preview()
    
    def clear_files(self):
        self.image_files = []
        self.update_file_list()
        self.code_preview.delete(1.0, tk.END)
        self.preview_canvas.delete("all")
        self.preview_label.config(text="预览 0/0")
    
    def prev_image(self):
        if self.image_files:
            self.current_preview_index = (self.current_preview_index - 1) % len(self.image_files)
            self.update_preview()
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.current_preview_index)
            self.file_listbox.see(self.current_preview_index)
    
    def next_image(self):
        if self.image_files:
            self.current_preview_index = (self.current_preview_index + 1) % len(self.image_files)
            self.update_preview()
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.current_preview_index)
            self.file_listbox.see(self.current_preview_index)
    
    def update_preview(self, *args):
        if not self.image_files:
            self.preview_label.config(text="预览 0/0")
            return
        
        self.preview_label.config(text=f"预览 {self.current_preview_index + 1}/{len(self.image_files)}")
        
        try:
            # 加载当前选择的图像
            image_path = self.image_files[self.current_preview_index]
            img = Image.open(image_path)
            
            # 转换为灰度图
            if img.mode != 'L':
                img = img.convert('L')
            
            # 获取当前设置
            threshold = self.threshold_var.get()
            invert = self.invert_var.get()
            
            # 二值化处理
            img_array = np.array(img)
            binary_array = np.where(img_array < threshold, 0, 255)
            
            # 如果需要反转颜色
            if invert:
                binary_array = 255 - binary_array
            
            # 创建预览图像
            preview_img = Image.fromarray(binary_array.astype(np.uint8))
            
            # 调整预览图像大小以适应画布
            width, height = preview_img.size
            scale = min(256 / width, 128 / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            preview_img = preview_img.resize((new_width, new_height), Image.NEAREST)
            
            # 显示预览图像
            self.preview_photo = ImageTk.PhotoImage(preview_img)
            self.preview_canvas.config(width=preview_img.width, height=preview_img.height)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_photo)
            
            # 生成并显示代码预览
            self.generate_code_preview()
            
        except Exception as e:
            self.status_var.set(f"预览错误: {e}")
    
    def generate_code_preview(self):
        if not self.image_files:
            return
        
        try:
            image_path = self.image_files[self.current_preview_index]
            
            # 生成变量名
            prefix = self.prefix_var.get() or "frame"
            var_name = f"{prefix}_{self.current_preview_index:03d}"
            
            # 获取当前设置
            threshold = self.threshold_var.get()
            invert = self.invert_var.get()
            
            # 转换图像
            c_array, width, height = self.image_to_horizontal_bitmap(
                image_path, var_name, threshold, invert
            )
            
            if c_array:
                # 显示代码预览
                self.code_preview.delete(1.0, tk.END)
                self.code_preview.insert(tk.END, f"// 图像: {os.path.basename(image_path)}, 尺寸: {width}x{height} 像素\n")
                self.code_preview.insert(tk.END, c_array)
        
        except Exception as e:
            self.status_var.set(f"代码生成错误: {e}")
    
    def image_to_horizontal_bitmap(self, image_path, variable_name, threshold, invert):
        """将图像转换为水平排列位图格式"""
        try:
            # 打开图像
            img = Image.open(image_path)
            
            # 获取图像尺寸
            width, height = img.size
            
            # 转换为灰度图
            if img.mode != 'L':
                img = img.convert('L')
            
            # 转换为NumPy数组以便处理
            img_array = np.array(img)
            
            # 二值化处理
            binary_array = np.where(img_array < threshold, 0, 1)
            
            # 如果需要反转颜色
            if invert:
                binary_array = 1 - binary_array
            
            # 计算每行需要的字节数 (向上取整到8的倍数)
            byte_width = (width + 7) // 8
            
            # 创建字节数组
            bytes_array = []
            
            # 按行处理图像
            for y in range(height):
                for x_byte in range(byte_width):
                    byte_value = 0
                    for bit in range(8):
                        x = x_byte * 8 + bit
                        if x < width:  # 确保在图像范围内
                            # 设置对应位 (MSB先)
                            if binary_array[y, x] == 1:
                                byte_value |= (0x80 >> bit)
                    bytes_array.append(byte_value)
            
            # 格式化为C数组
            c_array = f"const unsigned char {variable_name}[] = {{\n\t"
            for i, byte in enumerate(bytes_array):
                c_array += f"0x{byte:02x}, "
                if (i + 1) % 16 == 0 and i < len(bytes_array) - 1:
                    c_array += "\n\t"
            c_array = c_array.rstrip(", ") + "\n};"
            
            return c_array, width, height
        
        except Exception as e:
            raise Exception(f"处理图像时出错: {e}")
    
    def convert_and_save(self):
        if not self.image_files:
            messagebox.showwarning("警告", "没有选择任何图像文件")
            return
        
        # 选择输出文件
        default_ext = ".h" if self.header_var.get() else ".c"
        self.output_path = filedialog.asksaveasfilename(
            title="保存输出文件",
            defaultextension=default_ext,
            filetypes=[("头文件", "*.h"), ("C文件", "*.c"), ("所有文件", "*.*")]
        )
        
        if not self.output_path:
            return
        
        # 禁用界面控件
        self.disable_controls()
        
        # 在单独的线程中处理图像，避免界面冻结
        self.processing_thread = threading.Thread(
            target=self.process_images_thread,
            daemon=True
        )
        self.processing_thread.start()
    
    def process_images_thread(self):
        try:
            # 准备输出内容
            output_content = "// 此文件由SSD1306 OLED批量图像取模工具生成\n"
            output_content += "// 编码: UTF-8\n\n"
            
            # 获取设置
            prefix = self.prefix_var.get() or "frame"
            threshold = self.threshold_var.get()
            invert = self.invert_var.get()
            generate_header = self.header_var.get()
            generate_array = self.array_var.get()
            
            # 如果生成头文件，添加头文件保护
            if generate_header:
                header_guard = os.path.splitext(os.path.basename(self.output_path))[0].upper() + "_H"
                output_content += f"#ifndef {header_guard}\n"
                output_content += f"#define {header_guard}\n\n"
                output_content += "#include <stdint.h>\n\n"
            
            # 处理所有图像
            image_vars = []
            image_sizes = []
            total_files = len(self.image_files)
            
            for i, image_file in enumerate(self.image_files):
                # 更新进度
                progress = (i / total_files) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda msg=f"处理 {i+1}/{total_files}: {os.path.basename(image_file)}": 
                               self.status_var.set(msg))
                
                # 生成变量名
                var_name = f"{prefix}_{i:03d}"
                
                # 转换图像
                c_array, width, height = self.image_to_horizontal_bitmap(
                    image_file, var_name, threshold, invert
                )
                
                if c_array:
                    # 添加图像尺寸注释
                    output_content += f"// 图像: {os.path.basename(image_file)}, 尺寸: {width}x{height} 像素\n"
                    
                    # 如果是头文件，添加extern声明
                    if generate_header:
                        output_content += f"extern const unsigned char {var_name}[];\n"
                    else:
                        output_content += c_array + "\n\n"
                    
                    image_vars.append(var_name)
                    image_sizes.append((width, height))
            
            # 如果需要生成指针数组
            if generate_array and image_vars:
                if generate_header:
                    output_content += f"\n// 所有图像的指针数组\n"
                    output_content += f"extern const unsigned char* const image_array[{len(image_vars)}];\n"
                    output_content += f"\n// 图像尺寸数组\n"
                    output_content += f"extern const uint16_t image_widths[{len(image_vars)}];\n"
                    output_content += f"extern const uint16_t image_heights[{len(image_vars)}];\n"
                    output_content += f"\n// 图像总数\n"
                    output_content += f"#define IMAGE_COUNT {len(image_vars)}\n"
                else:
                    output_content += f"\n// 所有图像的指针数组\n"
                    output_content += f"const unsigned char* const image_array[{len(image_vars)}] = {{\n\t"
                    for i, var in enumerate(image_vars):
                        output_content += var + ", "
                        if (i + 1) % 5 == 0 and i < len(image_vars) - 1:
                            output_content += "\n\t"
                    output_content += "\n};\n"
                    
                    output_content += f"\n// 图像尺寸数组\n"
                    output_content += f"const uint16_t image_widths[{len(image_vars)}] = {{\n\t"
                    for i, (width, _) in enumerate(image_sizes):
                        output_content += f"{width}, "
                        if (i + 1) % 8 == 0 and i < len(image_sizes) - 1:
                            output_content += "\n\t"
                    output_content += "\n};\n"
                    
                    output_content += f"const uint16_t image_heights[{len(image_vars)}] = {{\n\t"
                    for i, (_, height) in enumerate(image_sizes):
                        output_content += f"{height}, "
                        if (i + 1) % 8 == 0 and i < len(image_sizes) - 1:
                            output_content += "\n\t"
                    output_content += "\n};\n"
                    
                    output_content += f"\n// 图像总数\n"
                    output_content += f"#define IMAGE_COUNT {len(image_vars)}\n"
            
            # 如果是头文件，添加结束的保护
            if generate_header:
                output_content += f"\n#endif // {header_guard}\n"
            
            # 写入输出文件
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
            
            # 更新UI
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.status_var.set(f"已成功保存到 {os.path.basename(self.output_path)}"))
            self.root.after(0, lambda: messagebox.showinfo("完成", f"已成功处理 {total_files} 个图像文件"))
            
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"处理出错: {e}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"处理图像时出错: {e}"))
        
        finally:
            # 重新启用界面控件
            self.root.after(0, self.enable_controls)
    
    def disable_controls(self):
        """禁用界面控件"""
        for child in self.root.winfo_children():
            if isinstance(child, (ttk.Button, ttk.Entry, ttk.Scale, ttk.Checkbutton)):
                child.configure(state="disabled")
    
    def enable_controls(self):
        """重新启用界面控件"""
        for child in self.root.winfo_children():
            if isinstance(child, (ttk.Button, ttk.Entry, ttk.Scale, ttk.Checkbutton)):
                child.configure(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = BatchImageConverterApp(root)
    root.mainloop()