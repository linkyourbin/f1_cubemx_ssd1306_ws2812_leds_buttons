#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog
from PIL import Image, ImageTk, ImageSequence
import numpy as np
import os
import glob
import re
import threading
import time
from datetime import datetime

def natural_sort_key(s):
    """用于自然排序的键函数，确保文件按照人类直觉的顺序排序（如1, 2, 10而不是1, 10, 2）"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

class EditableLabel(ttk.Frame):
    """可编辑的标签组件，双击可编辑"""
    def __init__(self, parent, variable, width=5, **kwargs):
        super().__init__(parent, **kwargs)
        self.variable = variable
        
        # 创建标签和输入框
        self.label = ttk.Label(self, textvariable=variable, width=width)
        self.label.pack(fill=tk.BOTH, expand=True)
        
        # 绑定双击事件
        self.label.bind("<Double-1>", self.start_edit)
        
        # 创建输入框（初始隐藏）
        self.entry = ttk.Entry(self, width=width)
        self.entry.bind("<Return>", self.stop_edit)
        self.entry.bind("<FocusOut>", self.stop_edit)
        self.entry.bind("<Escape>", self.cancel_edit)
        
        # 记录原始值（用于取消编辑）
        self.original_value = None
    
    def start_edit(self, event=None):
        """开始编辑模式"""
        # 保存原始值
        self.original_value = self.variable.get()
        
        # 设置输入框的值并显示
        self.entry.delete(0, tk.END)
        self.entry.insert(0, str(self.original_value))
        self.label.pack_forget()
        self.entry.pack(fill=tk.BOTH, expand=True)
        self.entry.focus_set()
        self.entry.selection_range(0, tk.END)
    
    def stop_edit(self, event=None):
        """结束编辑并保存值"""
        try:
            # 尝试获取并验证新值
            new_value = int(self.entry.get())
            if new_value < 10:
                new_value = 10
            elif new_value > 1000:
                new_value = 1000
            
            # 更新变量
            self.variable.set(new_value)
        except ValueError:
            # 如果输入无效，恢复原始值
            self.variable.set(self.original_value)
        
        # 隐藏输入框，显示标签
        self.entry.pack_forget()
        self.label.pack(fill=tk.BOTH, expand=True)
    
    def cancel_edit(self, event=None):
        """取消编辑，恢复原始值"""
        self.entry.pack_forget()
        self.label.pack(fill=tk.BOTH, expand=True)

class EnhancedImageConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OLED 图像取模工具")
        self.root.geometry("1400x700")
        
        # 设置应用程序图标（如果有的话）
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 数据变量
        self.image_files = []
        self.current_preview_index = 0
        self.output_path = None
        self.processing_thread = None
        self.animation_thread = None
        self.animation_running = False
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        
        # 确保临时目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 创建界面
        self.create_widgets()
        self.create_menu()
        
        # 设置主题
        self.set_theme()
    
    def set_theme(self):
        """设置应用程序主题"""
        style = ttk.Style()
        
        # 尝试使用更现代的主题
        try:
            style.theme_use("alt")  # 或者 "alt", "default", "classic"
        except:
            pass
        
        # 自定义颜色
        style.configure("TButton", padding=6)
        style.configure("TLabelframe", padding=8)
        style.configure("TLabelframe.Label", font=('Helvetica', 10, 'bold'))
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="选择图像文件", command=self.select_images)
        file_menu.add_command(label="选择文件夹", command=self.select_folder)
        file_menu.add_command(label="选择GIF文件", command=self.select_gif)
        file_menu.add_separator()
        file_menu.add_command(label="保存设置", command=self.save_settings)
        file_menu.add_command(label="加载设置", command=self.load_settings)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="清空所有文件", command=self.clear_files)
        edit_menu.add_command(label="反转文件顺序", command=self.reverse_files)
        edit_menu.add_separator()
        edit_menu.add_command(label="设置", command=self.show_settings)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="批量调整图像大小", command=self.batch_resize)
        tools_menu.add_command(label="批量转换为黑白", command=self.batch_convert_bw)
        tools_menu.add_command(label="提取GIF帧", command=self.extract_gif_frames)
        menubar.add_cascade(label="工具", menu=tools_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def create_widgets(self):
        """创建主界面控件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建左右分隔的面板
        panel = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        panel.pack(fill=tk.BOTH, expand=True)
        
        # 左侧控制面板
        left_frame = ttk.Frame(panel, padding="5")
        panel.add(left_frame, weight=1)
        
        # 右侧预览面板
        right_frame = ttk.Frame(panel, padding="5")
        panel.add(right_frame, weight=2)
        
        # 设置左侧控制面板
        self.setup_control_panel(left_frame)
        
        # 设置右侧预览面板
        self.setup_preview_panel(right_frame)
        
        # 底部状态栏和进度条
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 进度条
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(bottom_frame, orient="horizontal", 
                                           length=100, mode="determinate", 
                                           variable=self.progress_var)
        self.progress_bar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(5, 0))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(bottom_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 2))
    
    def setup_control_panel(self, parent):
        """设置左侧控制面板"""
        # 文件选择区域
        file_frame = ttk.LabelFrame(parent, text="文件选择", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        button_frame = ttk.Frame(file_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="选择图像", command=self.select_images).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(button_frame, text="选择文件夹", command=self.select_folder).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(button_frame, text="选择GIF", command=self.select_gif).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        # 文件列表
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.file_listbox = tk.Listbox(list_frame, height=10, selectmode=tk.EXTENDED)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        
        # 文件操作按钮
        file_buttons_frame = ttk.Frame(file_frame)
        file_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(file_buttons_frame, text="上移", command=self.move_up).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(file_buttons_frame, text="下移", command=self.move_down).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(file_buttons_frame, text="删除", command=self.remove_file).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(file_buttons_frame, text="清空", command=self.clear_files).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        # 转换设置区域
        settings_frame = ttk.LabelFrame(parent, text="转换设置", padding="5")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 变量名前缀
        prefix_frame = ttk.Frame(settings_frame)
        prefix_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(prefix_frame, text="变量名前缀:").pack(side=tk.LEFT, padx=5)
        self.prefix_var = tk.StringVar(value="frame")
        ttk.Entry(prefix_frame, textvariable=self.prefix_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 阈值滑块
        threshold_frame = ttk.Frame(settings_frame)
        threshold_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(threshold_frame, text="阈值:").pack(side=tk.LEFT, padx=5)
        self.threshold_var = tk.IntVar(value=128)
        threshold_slider = ttk.Scale(threshold_frame, from_=0, to=255, variable=self.threshold_var, 
                                     orient=tk.HORIZONTAL, command=self.update_preview)
        threshold_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(threshold_frame, textvariable=self.threshold_var, width=3).pack(side=tk.LEFT, padx=5)
        
        # 图像处理选项
        options_frame = ttk.Frame(settings_frame)
        options_frame.pack(fill=tk.X, pady=5)
        
        # 反转颜色复选框
        self.invert_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="反转颜色", variable=self.invert_var, 
                         command=self.update_preview).pack(side=tk.LEFT, padx=5)
        
        # 调整大小复选框
        self.resize_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="调整大小", variable=self.resize_var, 
                         command=self.update_preview).pack(side=tk.LEFT, padx=5)
        
        # 目标尺寸
        size_frame = ttk.Frame(settings_frame)
        size_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(size_frame, text="目标宽度:").pack(side=tk.LEFT, padx=5)
        self.width_var = tk.IntVar(value=128)
        ttk.Entry(size_frame, textvariable=self.width_var, width=5).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(size_frame, text="高度:").pack(side=tk.LEFT, padx=5)
        self.height_var = tk.IntVar(value=64)
        ttk.Entry(size_frame, textvariable=self.height_var, width=5).pack(side=tk.LEFT, padx=2)
        
        # 取模方式
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mode_frame, text="取模方式:").pack(side=tk.LEFT, padx=5)
        self.mode_var = tk.StringVar(value="horizontal")
        ttk.Radiobutton(mode_frame, text="水平排列", variable=self.mode_var, 
                        value="horizontal", command=self.update_preview).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="垂直排列", variable=self.mode_var, 
                        value="vertical", command=self.update_preview).pack(side=tk.LEFT, padx=5)
        
        # 输出选项区域
        output_frame = ttk.LabelFrame(parent, text="输出选项", padding="5")
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 文件类型选项
        file_type_frame = ttk.Frame(output_frame)
        file_type_frame.pack(fill=tk.X, pady=5)
        
        self.header_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(file_type_frame, text="生成头文件 (.h)", 
                         variable=self.header_var).pack(side=tk.LEFT, padx=5)
        
        self.array_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(file_type_frame, text="生成指针数组", 
                         variable=self.array_var).pack(side=tk.LEFT, padx=5)
        
        # 转换按钮
        convert_frame = ttk.Frame(parent)
        convert_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(convert_frame, text="转换并保存", command=self.convert_and_save).pack(fill=tk.X, pady=5)
    
    def setup_preview_panel(self, parent):
        """设置右侧预览面板"""
        # 预览区域
        preview_frame = ttk.LabelFrame(parent, text="图像预览", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 预览导航
        nav_frame = ttk.Frame(preview_frame)
        nav_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(nav_frame, text="上一个", command=self.prev_image).pack(side=tk.LEFT, padx=5)
        self.preview_label = ttk.Label(nav_frame, text="预览 0/0")
        self.preview_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="下一个", command=self.next_image).pack(side=tk.LEFT, padx=5)
        
        # 动画控制
        self.animation_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(nav_frame, text="动画预览", variable=self.animation_var, 
                        command=self.toggle_animation).pack(side=tk.LEFT, padx=20)
        
        # 速度控制
        speed_frame = ttk.Frame(nav_frame)
        speed_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(speed_frame, text="速度:").pack(side=tk.LEFT, padx=5)
        
        # 速度滑块
        self.speed_var = tk.IntVar(value=100)
        ttk.Scale(speed_frame, from_=10, to=500, variable=self.speed_var, 
                 orient=tk.HORIZONTAL, length=100).pack(side=tk.LEFT, padx=5)
        
        # 可编辑的速度标签
        speed_label_frame = ttk.Frame(speed_frame)
        speed_label_frame.pack(side=tk.LEFT, padx=5)
        
        self.speed_label = EditableLabel(speed_label_frame, self.speed_var, width=4)
        self.speed_label.pack(side=tk.LEFT)
        
        # 添加提示文本
        ttk.Label(speed_frame, text="ms (双击修改)").pack(side=tk.LEFT)
        
        # 图像预览画布
        canvas_frame = ttk.Frame(preview_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preview_canvas = tk.Canvas(canvas_frame, bg="white", width=256, height=128)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 图像信息
        self.image_info_var = tk.StringVar(value="")
        ttk.Label(preview_frame, textvariable=self.image_info_var).pack(anchor=tk.W, pady=5)
        
        # 代码预览区域
        code_frame = ttk.LabelFrame(parent, text="代码预览", padding="5")
        code_frame.pack(fill=tk.BOTH, expand=True)
        
        # 代码预览文本框
        code_text_frame = ttk.Frame(code_frame)
        code_text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.code_preview = tk.Text(code_text_frame, height=15, width=60, wrap=tk.NONE)
        self.code_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        code_scrolly = ttk.Scrollbar(code_text_frame, orient="vertical", command=self.code_preview.yview)
        code_scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        self.code_preview.config(yscrollcommand=code_scrolly.set)
        
        code_scrollx = ttk.Scrollbar(code_frame, orient="horizontal", command=self.code_preview.xview)
        code_scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        self.code_preview.config(xscrollcommand=code_scrollx.set)
    
    def select_images(self):
        """选择多个图像文件"""
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
        """选择包含图像的文件夹"""
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
    
    def select_gif(self):
        """选择GIF文件并提取帧"""
        gif_path = filedialog.askopenfilename(
            title="选择GIF文件",
            filetypes=[("GIF文件", "*.gif"), ("所有文件", "*.*")]
        )
        
        if not gif_path:
            return
        
        # 询问是否需要调整大小和转换为黑白
        resize = messagebox.askyesno("调整大小", "是否需要将GIF帧调整为OLED显示屏大小 (128x64)?")
        convert_bw = messagebox.askyesno("转换为黑白", "是否需要将GIF帧转换为黑白图像?")
        
        if convert_bw:
            threshold = simpledialog.askinteger("阈值", "请输入黑白转换阈值 (0-255):", 
                                               minvalue=0, maxvalue=255, initialvalue=128)
            if threshold is None:
                threshold = 128
        else:
            threshold = 128
        
        # 创建临时目录
        temp_dir = os.path.join(self.temp_dir, f"gif_{int(time.time())}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 在单独的线程中处理GIF
        self.disable_controls()
        self.status_var.set(f"正在处理GIF文件: {os.path.basename(gif_path)}...")
        
        threading.Thread(
            target=self.process_gif_thread,
            args=(gif_path, temp_dir, resize, convert_bw, threshold),
            daemon=True
        ).start()
    
    def process_gif_thread(self, gif_path, output_dir, resize=True, convert_bw=False, threshold=128):
        """在单独的线程中处理GIF文件"""
        try:
            # 打开GIF文件
            with Image.open(gif_path) as gif:
                frame_count = 0
                frames = []
                
                # 获取GIF的持续时间
                duration = gif.info.get('duration', 100)
                
                # 遍历每一帧
                while True:
                    try:
                        # 复制当前帧
                        frame = gif.copy()
                        
                        # 调整图像大小
                        if resize:
                            frame = frame.resize((128, 64), Image.LANCZOS)
                        
                        # 转换为黑白模式
                        if convert_bw:
                            frame = frame.convert("L")
                            frame = frame.point(lambda x: 255 if x > threshold else 0, '1')
                        
                        # 保存帧
                        frame_path = os.path.join(output_dir, f"frame_{frame_count:03d}.png")
                        frame.save(frame_path, "PNG")
                        frames.append(frame_path)
                        
                        # 更新进度
                        self.root.after(0, lambda p=(frame_count+1)/gif.n_frames*100: self.progress_var.set(p))
                        self.root.after(0, lambda msg=f"处理GIF帧 {frame_count+1}/{gif.n_frames}": 
                                       self.status_var.set(msg))
                        
                        frame_count += 1
                        gif.seek(frame_count)
                        
                    except EOFError:
                        break
            
            # 保存帧信息
            with open(os.path.join(output_dir, "frame_info.txt"), 'w') as f:
                f.write(f"总帧数: {frame_count}\n")
                f.write(f"每帧持续时间: {duration}ms\n")
            
            # 设置默认动画速度为GIF的帧速率
            if duration > 0:
                self.root.after(0, lambda: self.speed_var.set(duration))
            
            # 添加提取的帧到文件列表
            self.root.after(0, lambda: self.add_gif_frames(frames))
            
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"处理GIF出错: {e}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"处理GIF文件时出错: {e}"))
        
        finally:
            self.root.after(0, self.enable_controls)
            self.root.after(0, lambda: self.progress_var.set(0))
    
    def add_gif_frames(self, frames):
        """添加GIF帧到文件列表"""
        added_count = 0
        for frame_path in frames:
            if frame_path not in self.image_files:
                self.image_files.append(frame_path)
                added_count += 1
        
        self.update_file_list()
        self.status_var.set(f"已从GIF添加 {added_count} 个帧")
        
        # 自动启用动画预览
        if added_count > 1:
            self.animation_var.set(True)
            self.toggle_animation()
    
    def extract_gif_frames(self):
        """从菜单调用的GIF帧提取功能"""
        self.select_gif()
    
    def update_file_list(self):
        """更新文件列表显示"""
        self.file_listbox.delete(0, tk.END)
        for file_path in self.image_files:
            self.file_listbox.insert(tk.END, os.path.basename(file_path))
        
        if self.image_files:
            self.current_preview_index = 0
            self.update_preview()
    
    def on_file_select(self, event):
        """文件列表选择事件处理"""
        selection = self.file_listbox.curselection()
        if selection:
            self.current_preview_index = selection[0]
            self.update_preview()
    
    def move_up(self):
        """将选中的文件向上移动"""
        selection = self.file_listbox.curselection()
        if selection and selection[0] > 0:
            idx = selection[0]
            self.image_files[idx], self.image_files[idx-1] = self.image_files[idx-1], self.image_files[idx]
            self.update_file_list()
            self.file_listbox.selection_set(idx-1)
            self.current_preview_index = idx-1
            self.update_preview()
    
    def move_down(self):
        """将选中的文件向下移动"""
        selection = self.file_listbox.curselection()
        if selection and selection[0] < len(self.image_files) - 1:
            idx = selection[0]
            self.image_files[idx], self.image_files[idx+1] = self.image_files[idx+1], self.image_files[idx]
            self.update_file_list()
            self.file_listbox.selection_set(idx+1)
            self.current_preview_index = idx+1
            self.update_preview()
    
    def remove_file(self):
        """删除选中的文件"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        
        # 删除多个选中的文件
        indices = sorted(selection, reverse=True)
        for idx in indices:
            del self.image_files[idx]
        
        self.update_file_list()
        if self.image_files:
            new_idx = min(indices[0], len(self.image_files) - 1)
            self.file_listbox.selection_set(new_idx)
            self.current_preview_index = new_idx
            self.update_preview()
    
    def clear_files(self):
        """清空所有文件"""
        if messagebox.askyesno("确认", "确定要清空所有文件吗?"):
            self.image_files = []
            self.update_file_list()
            self.code_preview.delete(1.0, tk.END)
            self.preview_canvas.delete("all")
            self.preview_label.config(text="预览 0/0")
            self.image_info_var.set("")
    
    def reverse_files(self):
        """反转文件顺序"""
        if self.image_files:
            self.image_files.reverse()
            self.update_file_list()
            self.status_var.set("已反转文件顺序")
    
    def prev_image(self):
        """显示上一个图像"""
        if self.image_files:
            self.current_preview_index = (self.current_preview_index - 1) % len(self.image_files)
            self.update_preview()
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.current_preview_index)
            self.file_listbox.see(self.current_preview_index)
    
    def next_image(self):
        """显示下一个图像"""
        if self.image_files:
            self.current_preview_index = (self.current_preview_index + 1) % len(self.image_files)
            self.update_preview()
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.current_preview_index)
            self.file_listbox.see(self.current_preview_index)
    
    def toggle_animation(self):
        """切换动画预览状态"""
        if self.animation_var.get():
            self.start_animation()
        else:
            self.stop_animation()
    
    def start_animation(self):
        """开始动画预览"""
        if not self.image_files or len(self.image_files) < 2:
            messagebox.showinfo("提示", "需要至少两个图像文件才能预览动画")
            self.animation_var.set(False)
            return
        
        self.animation_running = True
        self.animation_thread = threading.Thread(target=self.animation_loop, daemon=True)
        self.animation_thread.start()
    
    def stop_animation(self):
        """停止动画预览"""
        self.animation_running = False
        if self.animation_thread:
            self.animation_thread.join(timeout=1.0)
            self.animation_thread = None
    
    def animation_loop(self):
        """动画预览循环"""
        index = self.current_preview_index
        while self.animation_running:
            index = (index + 1) % len(self.image_files)
            self.root.after(0, lambda idx=index: self.preview_frame(idx))
            time.sleep(self.speed_var.get() / 1000)
    
    def preview_frame(self, index):
        """预览指定索引的帧"""
        self.current_preview_index = index
        self.update_preview(skip_code=True)
        self.file_listbox.selection_clear(0, tk.END)
        self.file_listbox.selection_set(index)
        self.file_listbox.see(index)
    
    def update_preview(self, *args, skip_code=False):
        """更新图像预览"""
        if not self.image_files:
            self.preview_label.config(text="预览 0/0")
            self.image_info_var.set("")
            return
        
        self.preview_label.config(text=f"预览 {self.current_preview_index + 1}/{len(self.image_files)}")
        
        try:
            # 加载当前选择的图像
            image_path = self.image_files[self.current_preview_index]
            img = Image.open(image_path)
            
            # 显示图像信息
            width, height = img.size
            file_size = os.path.getsize(image_path) / 1024  # KB
            self.image_info_var.set(f"文件: {os.path.basename(image_path)} | 尺寸: {width}x{height} | 格式: {img.format} | 大小: {file_size:.1f} KB")
            
            # 调整大小
            if self.resize_var.get():
                target_width = self.width_var.get()
                target_height = self.height_var.get()
                img = img.resize((target_width, target_height), Image.LANCZOS)
            
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
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                scale = min(canvas_width / preview_img.width, canvas_height / preview_img.height)
                new_width = int(preview_img.width * scale)
                new_height = int(preview_img.height * scale)
                preview_img = preview_img.resize((new_width, new_height), Image.NEAREST)
            
            # 显示预览图像
            self.preview_photo = ImageTk.PhotoImage(preview_img)
            self.preview_canvas.config(width=preview_img.width, height=preview_img.height)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_photo)
            
            # 生成并显示代码预览
            if not skip_code:
                self.generate_code_preview()
            
        except Exception as e:
            self.status_var.set(f"预览错误: {e}")
    
    def generate_code_preview(self):
        """生成并显示代码预览"""
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
            mode = self.mode_var.get()
            resize = self.resize_var.get()
            target_width = self.width_var.get() if resize else None
            target_height = self.height_var.get() if resize else None
            
            # 转换图像
            c_array, width, height = self.image_to_bitmap(
                image_path, var_name, threshold, invert, mode, 
                target_width, target_height
            )
            
            if c_array:
                # 显示代码预览
                self.code_preview.delete(1.0, tk.END)
                self.code_preview.insert(tk.END, f"// 图像: {os.path.basename(image_path)}, 尺寸: {width}x{height} 像素\n")
                self.code_preview.insert(tk.END, c_array)
        
        except Exception as e:
            self.status_var.set(f"代码生成错误: {e}")
    
    def image_to_bitmap(self, image_path, variable_name, threshold, invert, mode="horizontal", 
                        target_width=None, target_height=None):
        """将图像转换为位图格式"""
        try:
            # 打开图像
            img = Image.open(image_path)
            
            # 调整大小
            if target_width and target_height:
                img = img.resize((target_width, target_height), Image.LANCZOS)
            
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
            
            # 创建字节数组
            bytes_array = []
            
            if mode == "horizontal":
                # 水平排列 (每个字节代表8个水平像素)
                # 计算每行需要的字节数 (向上取整到8的倍数)
                byte_width = (width + 7) // 8
                
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
            else:
                # 垂直排列 (每个字节代表8个垂直像素)
                # 计算每列需要的字节数 (向上取整到8的倍数)
                byte_height = (height + 7) // 8
                
                # 按列处理图像
                for x in range(width):
                    for y_byte in range(byte_height):
                        byte_value = 0
                        for bit in range(8):
                            y = y_byte * 8 + bit
                            if y < height:  # 确保在图像范围内
                                # 设置对应位
                                if binary_array[y, x] == 1:
                                    byte_value |= (1 << bit)
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
        """转换并保存所有图像"""
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
        """在单独的线程中处理所有图像"""
        try:
            # 准备输出内容
            output_content = "// 此文件由OLED图像取模工具生成\n"
            output_content += "// 生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n"
            output_content += "// 编码: UTF-8\n\n"
            
            # 获取设置
            prefix = self.prefix_var.get() or "frame"
            threshold = self.threshold_var.get()
            invert = self.invert_var.get()
            mode = self.mode_var.get()
            resize = self.resize_var.get()
            target_width = self.width_var.get() if resize else None
            target_height = self.height_var.get() if resize else None
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
                c_array, width, height = self.image_to_bitmap(
                    image_file, var_name, threshold, invert, mode,
                    target_width, target_height
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
                    
                    # 添加帧速率信息
                    output_content += f"\n// 动画帧速率 (毫秒/帧)\n"
                    output_content += f"#define FRAME_DELAY {self.speed_var.get()}\n"
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
                    
                    # 添加帧速率信息
                    output_content += f"\n// 动画帧速率 (毫秒/帧)\n"
                    output_content += f"#define FRAME_DELAY {self.speed_var.get()}\n"
            
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
    
    def batch_resize(self):
        """批量调整图像大小"""
        if not self.image_files:
            messagebox.showwarning("警告", "没有选择任何图像文件")
            return
        
        # 询问目标尺寸
        width = simpledialog.askinteger("宽度", "请输入目标宽度:", 
                                       minvalue=1, maxvalue=1024, initialvalue=128)
        if width is None:
            return
        
        height = simpledialog.askinteger("高度", "请输入目标高度:", 
                                        minvalue=1, maxvalue=1024, initialvalue=64)
        if height is None:
            return
        
        # 询问输出目录
        output_dir = filedialog.askdirectory(title="选择输出目录")
        if not output_dir:
            return
        
        # 禁用界面控件
        self.disable_controls()
        
        # 在单独的线程中处理图像
        threading.Thread(
            target=self.batch_resize_thread,
            args=(width, height, output_dir),
            daemon=True
        ).start()
    
    def batch_resize_thread(self, width, height, output_dir):
        """在单独的线程中批量调整图像大小"""
        try:
            total_files = len(self.image_files)
            processed = 0
            
            for i, image_file in enumerate(self.image_files):
                # 更新进度
                progress = (i / total_files) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda msg=f"调整大小 {i+1}/{total_files}: {os.path.basename(image_file)}": 
                               self.status_var.set(msg))
                
                # 打开图像
                img = Image.open(image_file)
                
                # 调整大小
                img = img.resize((width, height), Image.LANCZOS)
                
                # 保存图像
                output_path = os.path.join(output_dir, os.path.basename(image_file))
                img.save(output_path)
                
                processed += 1
            
            # 更新UI
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.status_var.set(f"已成功调整 {processed} 个图像文件的大小"))
            self.root.after(0, lambda: messagebox.showinfo("完成", f"已成功调整 {processed} 个图像文件的大小"))
            
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"处理出错: {e}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"调整图像大小时出错: {e}"))
        
        finally:
            # 重新启用界面控件
            self.root.after(0, self.enable_controls)
    
    def batch_convert_bw(self):
        """批量转换图像为黑白"""
        if not self.image_files:
            messagebox.showwarning("警告", "没有选择任何图像文件")
            return
        
        # 询问阈值
        threshold = simpledialog.askinteger("阈值", "请输入黑白转换阈值 (0-255):", 
                                           minvalue=0, maxvalue=255, initialvalue=128)
        if threshold is None:
            return
        
        # 询问输出目录
        output_dir = filedialog.askdirectory(title="选择输出目录")
        if not output_dir:
            return
        
        # 禁用界面控件
        self.disable_controls()
        
        # 在单独的线程中处理图像
        threading.Thread(
            target=self.batch_convert_bw_thread,
            args=(threshold, output_dir),
            daemon=True
        ).start()
    
    def batch_convert_bw_thread(self, threshold, output_dir):
        """在单独的线程中批量转换图像为黑白"""
        try:
            total_files = len(self.image_files)
            processed = 0
            
            for i, image_file in enumerate(self.image_files):
                # 更新进度
                progress = (i / total_files) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda msg=f"转换黑白 {i+1}/{total_files}: {os.path.basename(image_file)}": 
                               self.status_var.set(msg))
                
                # 打开图像
                img = Image.open(image_file)
                
                # 转换为灰度图
                img = img.convert('L')
                
                # 二值化处理
                img = img.point(lambda x: 255 if x > threshold else 0, '1')
                
                # 保存图像
                output_path = os.path.join(output_dir, os.path.basename(image_file))
                img.save(output_path)
                
                processed += 1
            
            # 更新UI
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.status_var.set(f"已成功转换 {processed} 个图像文件为黑白"))
            self.root.after(0, lambda: messagebox.showinfo("完成", f"已成功转换 {processed} 个图像文件为黑白"))
            
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"处理出错: {e}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"转换图像为黑白时出错: {e}"))
        
        finally:
            # 重新启用界面控件
            self.root.after(0, self.enable_controls)
    
    def save_settings(self):
        """保存当前设置"""
        settings_path = filedialog.asksaveasfilename(
            title="保存设置",
            defaultextension=".ini",
            filetypes=[("设置文件", "*.ini"), ("所有文件", "*.*")]
        )
        
        if not settings_path:
            return
        
        try:
            with open(settings_path, 'w', encoding='utf-8') as f:
                f.write(f"[Settings]\n")
                f.write(f"prefix={self.prefix_var.get()}\n")
                f.write(f"threshold={self.threshold_var.get()}\n")
                f.write(f"invert={1 if self.invert_var.get() else 0}\n")
                f.write(f"resize={1 if self.resize_var.get() else 0}\n")
                f.write(f"width={self.width_var.get()}\n")
                f.write(f"height={self.height_var.get()}\n")
                f.write(f"mode={self.mode_var.get()}\n")
                f.write(f"header={1 if self.header_var.get() else 0}\n")
                f.write(f"array={1 if self.array_var.get() else 0}\n")
                f.write(f"speed={self.speed_var.get()}\n")
            
            self.status_var.set(f"已保存设置到 {os.path.basename(settings_path)}")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存设置时出错: {e}")
    
    def load_settings(self):
        """加载设置"""
        settings_path = filedialog.askopenfilename(
            title="加载设置",
            filetypes=[("设置文件", "*.ini"), ("所有文件", "*.*")]
        )
        
        if not settings_path:
            return
        
        try:
            settings = {}
            with open(settings_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('[') and '=' in line:
                        key, value = line.split('=', 1)
                        settings[key.strip()] = value.strip()
            
            # 应用设置
            if 'prefix' in settings:
                self.prefix_var.set(settings['prefix'])
            
            if 'threshold' in settings:
                self.threshold_var.set(int(settings['threshold']))
            
            if 'invert' in settings:
                self.invert_var.set(bool(int(settings['invert'])))
            
            if 'resize' in settings:
                self.resize_var.set(bool(int(settings['resize'])))
            
            if 'width' in settings:
                self.width_var.set(int(settings['width']))
            
            if 'height' in settings:
                self.height_var.set(int(settings['height']))
            
            if 'mode' in settings:
                self.mode_var.set(settings['mode'])
            
            if 'header' in settings:
                self.header_var.set(bool(int(settings['header'])))
            
            if 'array' in settings:
                self.array_var.set(bool(int(settings['array'])))
                
            if 'speed' in settings:
                self.speed_var.set(int(settings['speed']))
            
            self.status_var.set(f"已加载设置从 {os.path.basename(settings_path)}")
            
            # 更新预览
            self.update_preview()
            
        except Exception as e:
            messagebox.showerror("错误", f"加载设置时出错: {e}")
    
    def show_settings(self):
        """显示设置对话框"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("设置")
        settings_window.geometry("400x300")
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # 创建设置控件
        frame = ttk.Frame(settings_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 临时目录设置
        ttk.Label(frame, text="临时文件目录:").grid(row=0, column=0, sticky=tk.W, pady=5)
        temp_dir_var = tk.StringVar(value=self.temp_dir)
        ttk.Entry(frame, textvariable=temp_dir_var).grid(row=0, column=1, sticky=tk.EW, padx=5)
        ttk.Button(frame, text="浏览", command=lambda: self.browse_temp_dir(temp_dir_var)).grid(row=0, column=2)
        
        # 动画速度范围设置
        ttk.Label(frame, text="动画速度范围:").grid(row=1, column=0, sticky=tk.W, pady=5)
        speed_frame = ttk.Frame(frame)
        speed_frame.grid(row=1, column=1, sticky=tk.EW, padx=5)
        
        ttk.Label(speed_frame, text="最小:").pack(side=tk.LEFT)
        min_speed_var = tk.IntVar(value=10)
        ttk.Entry(speed_frame, textvariable=min_speed_var, width=5).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(speed_frame, text="最大:").pack(side=tk.LEFT, padx=5)
        max_speed_var = tk.IntVar(value=500)
        ttk.Entry(speed_frame, textvariable=max_speed_var, width=5).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(speed_frame, text="ms").pack(side=tk.LEFT, padx=2)
        
        # 其他设置可以根据需要添加
        
        # 确定和取消按钮
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=10, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="确定", 
                  command=lambda: self.apply_settings(settings_window, temp_dir_var, min_speed_var, max_speed_var)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=settings_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def browse_temp_dir(self, var):
        """浏览临时目录"""
        dir_path = filedialog.askdirectory(title="选择临时文件目录")
        if dir_path:
            var.set(dir_path)
    
    def apply_settings(self, window, temp_dir_var, min_speed_var=None, max_speed_var=None):
        """应用设置"""
        self.temp_dir = temp_dir_var.get()
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 更新速度范围
        if min_speed_var and max_speed_var:
            min_speed = min_speed_var.get()
            max_speed = max_speed_var.get()
            
            if min_speed > 0 and max_speed > min_speed:
                # 更新速度滑块的范围
                for child in self.root.winfo_children():
                    if isinstance(child, ttk.Scale) and child.cget("variable") == str(self.speed_var):
                        child.configure(from_=min_speed, to=max_speed)
                        break
        
        window.destroy()
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
OLED 图像取模工具使用说明

1. 基本功能:
   - 支持单个图像和批量图像处理
   - 支持GIF动画帧提取
   - 支持水平和垂直两种取模方式
   - 可生成C源文件或头文件
   - 可生成指针数组用于动画

2. 使用步骤:
   a) 选择图像文件或文件夹
   b) 调整转换设置(阈值、反转颜色等)
   c) 设置输出选项
   d) 点击"转换并保存"按钮

3. 动画预览:
   - 勾选"动画预览"复选框可预览动画效果
   - 使用速度滑块调整动画播放速度
   - 双击速度数值可直接输入精确值
   - 动画预览仅在有多个图像文件时可用

4. GIF处理:
   - 选择GIF文件后会自动提取所有帧
   - 可选择是否调整大小和转换为黑白
   - 提取的帧会添加到文件列表中

5. 批量工具:
   - 批量调整图像大小
   - 批量转换为黑白
   - 提取GIF帧

6. 快捷键:
   - Ctrl+O: 选择图像文件
   - Ctrl+F: 选择文件夹
   - Ctrl+G: 选择GIF文件
   - Ctrl+S: 保存设置
   - Ctrl+L: 加载设置
   - F1: 显示帮助
        """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("600x400")
        help_window.transient(self.root)
        
        text = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, help_text)
        text.config(state=tk.DISABLED)
        
        scrollbar = ttk.Scrollbar(text, command=text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.config(yscrollcommand=scrollbar.set)
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
OLED 图像取模工具

版本: 1.1.0
日期: 2023-05-15

这是一个用于OLED显示屏的图像取模工具，可以将图像转换为C数组格式，
适用于SSD1306等OLED显示屏。

支持功能:
- 单个和批量图像处理
- GIF动画帧提取
- 水平和垂直取模方式
- 动画预览（支持双击直接修改速度）
- 批量图像处理工具

作者: linkyourbin
        """
        
        messagebox.showinfo("关于", about_text)
    
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
    app = EnhancedImageConverterApp(root)
    root.mainloop()