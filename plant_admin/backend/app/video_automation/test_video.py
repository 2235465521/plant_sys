# -*- coding: utf-8 -*-
"""测试脚本：直接运行以测试视频自动生成逻辑。"""
import os
import sys
from pathlib import Path

# 将项目根目录加入 python path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.video_automation.db_reader import get_plant_data_for_video
from app.video_automation.frame_renderer import get_6_slide_images
from app.video_automation.video_compiler import compile_plant_video


def run_test():
    plant_id = 3
    print(f"正在读取植物 ID: {plant_id} 的数据...")
    data = get_plant_data_for_video(plant_id)
    if not data:
        print("错误：未找到该植物数据。")
        return
        
    print(f"植物名称: {data.get('vernacular_name')}")
    print(f"包含的图片: {data.get('image_server_paths')}")
    
    print("正在渲染 6 张 Slide 帧...")
    slides = get_6_slide_images(data)
    print(f"渲染成功，共 {len(slides)} 帧。")
    
    # 输出到当前目录的 test.mp4
    output_path = str(Path(__file__).resolve().parent / "test_plant_3.mp4")
    print(f"正在编译视频，输出路径: {output_path} ...")
    
    success, msg = compile_plant_video(slides, output_path)
    if success:
        print(f"成功！视频已生成。文件大小: {os.path.getsize(output_path)} 字节")
    else:
        print(f"失败：{msg}")


if __name__ == "__main__":
    run_test()
