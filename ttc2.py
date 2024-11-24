from fontTools.ttLib import TTFont, TTCollection
import os

def extract_fonts(font_path):
    # 打开TTC文件
    ttc = TTCollection(font_path)
    print(f"发现 {len(ttc)} 个字体")
    
    # 处理每个字体
    for i in range(len(ttc)):
        try:
            # 获取当前字体
            font = ttc[i]
            
            # 检查字体格式
            is_otf = 'CFF ' in font
            extension = 'otf' if is_otf else 'ttf'
            
            # 尝试获取字体名称
            font_name = None
            for record in font['name'].names:
                if record.nameID == 4:  # nameID 4 是完整字体名称
                    try:
                        font_name = record.string.decode('utf-16-be').strip()
                        break
                    except:
                        try:
                            font_name = record.string.decode('utf-8').strip()
                            break
                        except:
                            continue
            
            # 生成输出文件名
            output_name = f"PingFang_{i}.{extension}"
            if font_name:
                # 替换非法文件名字符
                font_name = "".join(c for c in font_name if c not in r'<>:"/\|?*')
                output_name = f"{font_name}.{extension}"
            
            # 保存字体
            font.save(output_name)
            print(f"已保存字体 {i+1}/{len(ttc)}: {output_name}")
            
        except Exception as e:
            print(f"处理第 {i+1} 个字体时出错: {str(e)}")

def main():
    font_path = "Iosevka-Regular.ttc"
    if not os.path.exists(font_path):
        print("错误：找不到字体文件 Iosevka-Regular.ttc")
        return
    
    try:
        extract_fonts(font_path)
        print("字体分离完成！")
    except Exception as e:
        print(f"处理字体时出错: {str(e)}")

if __name__ == "__main__":
    main()