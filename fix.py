import os
import sys
import logging
import traceback
from fontTools.ttLib import TTFont, TTCollection, newTable
from fontTools.ttLib.tables._n_a_m_e import makeName
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

# 配置日志格式和级别
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

def process_fonts(input_dir, output_dir):
    logging.info("开始处理字体文件...")
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"已创建输出目录：{output_dir}")

    # 获取输入目录中的所有字体文件
    font_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.ttc', '.otf', '.ttf'))]

    if not font_files:
        logging.warning(f"输入目录 {input_dir} 中未找到字体文件。")
        return

    for font_file in font_files:
        font_path = os.path.join(input_dir, font_file)
        try:
            if font_file.lower().endswith('.ttc'):
                # 处理 TTC 文件
                logging.info(f"开始处理 TTC 文件：{font_file}")
                extract_and_fix_fonts_from_ttc(font_path, output_dir)
            else:
                # 处理单个 OTF 和 TTF 文件
                logging.info(f"开始处理字体文件：{font_file}")
                fix_font_tables(font_path, output_dir)
        except Exception as e:
            logging.error(f"处理文件 {font_file} 时出错：{e}")
            logging.debug(traceback.format_exc())

def extract_and_fix_fonts_from_ttc(ttc_path, output_dir):
    try:
        ttc = TTCollection(ttc_path)
        logging.debug(f"TTC 文件包含 {len(ttc)} 个字体。")
    except Exception as e:
        logging.error(f"无法打开 TTC 文件 {ttc_path}：{e}")
        logging.debug(traceback.format_exc())
        return

    for i, font in enumerate(ttc):
        try:
            # 获取字体的全名（nameID=4）
            full_name = font['name'].getDebugName(4)
            if not full_name:
                full_name = f"Font_{i}"

            if "CFF " in font:
                extension = ".otf"
            else:
                extension = ".ttf"

            # 去掉文件名中的空格和无效字符
            new_filename = f"{full_name.replace(' ', '').replace('/', '').replace('\\', '')}{extension}"
            new_filepath = os.path.join(output_dir, new_filename)

            # 保存提取的字体文件
            font.save(new_filepath)
            logging.info(f"已提取并保存: {new_filename}")

            # 对提取的字体文件进行名称表和 cmap 表修复
            fix_font_tables(new_filepath, output_dir, from_extraction=True)
        except Exception as e:
            logging.error(f"处理字体 {full_name} 时出错：{e}")
            logging.debug(traceback.format_exc())

def fix_font_tables(font_path, output_dir, from_extraction=False):
    try:
        # 打开字体文件
        font = TTFont(font_path)
    except Exception as e:
        logging.error(f"无法打开字体文件 {font_path}：{e}")
        logging.debug(traceback.format_exc())
        return

    try:
        # 修复 name 表
        fix_font_name_table(font)

        # 修复 cmap 表
        fix_font_cmap_table(font)

        # 构造新的字体文件路径
        font_name = os.path.basename(font_path)
        if font_name.lower().endswith('.otf'):
            new_font_name = font_name[:-4] + '_fixed.otf'
        elif font_name.lower().endswith('.ttf'):
            new_font_name = font_name[:-4] + '_fixed.ttf'
        else:
            new_font_name = font_name + '_fixed'

        new_font_path = os.path.join(output_dir, new_font_name)

        # 保存修改后的字体文件
        font.save(new_font_path)
        font.close()
        logging.info(f"已修复并保存字体文件：{new_font_name}")
    except Exception as e:
        logging.error(f"修复字体文件 {font_path} 时出错：{e}")
        logging.debug(traceback.format_exc())
    finally:
        # 如果是从 TTC 提取的字体，删除中间文件
        if from_extraction:
            try:
                os.remove(font_path)
                logging.debug(f"已删除中间文件：{font_path}")
            except Exception as e:
                logging.warning(f"无法删除中间文件 {font_path}：{e}")
                logging.debug(traceback.format_exc())

def fix_font_name_table(font):
    try:
        # 获取或创建 name 表
        if 'name' not in font:
            font['name'] = newTable('name')
        name_table = font['name']

        # 设置平台和编码映射
        source_platformID = 1  # Macintosh
        target_platformID = 3  # Windows
        target_platEncID = 1   # Unicode BMP (UCS-2)

        # 语言 ID 映射（Macintosh 到 Windows）
        langID_mapping = {
            0x0: 0x0409,    # Mac 英语 -> Windows 英语（美国）
            0x7: 0x0804,    # Mac 简体中文 -> Windows 简体中文
            0x9: 0x0404,    # Mac 繁体中文 -> Windows 繁体中文
            0xb: 0x0411,    # Mac 日语 -> Windows 日语
            0x11: 0x0411,   # 一些字体可能使用 0x11 表示日语
            0x12: 0x0412,   # Mac 韩语 -> Windows 韩语
        }

        # 创建一个新的名称记录列表，避免在遍历的同时修改原始列表
        new_name_records = []

        # 遍历现有的 name 表名称记录
        for record in name_table.names:
            if record.platformID == source_platformID:
                # 使用 toUnicode() 获取 Unicode 字符串
                try:
                    string = record.toUnicode()
                except UnicodeDecodeError:
                    logging.warning(f"无法解码的名称记录：nameID={record.nameID}，跳过。")
                    continue

                source_langID = record.langID

                # 针对 langID=0xFFFF（语言独立），保留原始的 langID
                if source_langID == 0xFFFF:
                    target_langID = 0xFFFF
                else:
                    # 根据语言 ID 映射获取目标语言 ID，如果没有映射则使用源语言 ID
                    target_langID = langID_mapping.get(source_langID, source_langID)

                # 检查是否已存在对应的 Windows 平台名称记录
                exists = False
                for existing_record in name_table.names:
                    if (existing_record.nameID == record.nameID and
                        existing_record.platformID == target_platformID and
                        existing_record.platEncID == target_platEncID and
                        existing_record.langID == target_langID):
                        exists = True
                        break
                if not exists:
                    # 将字符串编码为 utf-16be
                    encoded_string = string.encode('utf-16-be')
                    # 创建新的名称记录
                    new_record = makeName(encoded_string, record.nameID,
                                        target_platformID, target_platEncID, target_langID)
                    # 添加到新的名称记录列表
                    new_name_records.append(new_record)

        # 将新的名称记录添加到 name 表
        name_table.names.extend(new_name_records)
        logging.debug(f"已修复 name 表，共添加了 {len(new_name_records)} 个名称记录。")
    except Exception as e:
        logging.error(f"修复 name 表时出错：{e}")
        logging.debug(traceback.format_exc())

def fix_font_cmap_table(font):
    try:
        cmap_table = font['cmap']

        # 检查是否存在 cmap_format_4（Platform ID 为 3，Encoding ID 为 1）
        has_format_4 = False
        for subtable in cmap_table.tables:
            if subtable.platformID == 3 and subtable.platEncID == 1 and subtable.format == 4:
                has_format_4 = True
                break

        if not has_format_4:
            # 创建新的 cmap_format_4 子表
            new_subtable = CmapSubtable.newSubtable(4)
            new_subtable.platformID = 3  # Microsoft
            new_subtable.platEncID = 1   # Unicode BMP (UCS-2)
            new_subtable.language = 0
            new_subtable.cmap = {}

            # 获取字体中的所有有效字形名称
            valid_glyph_names = set(font.getGlyphOrder())
            num_glyphs = len(valid_glyph_names)
            logging.info(f"字体中包含 {num_glyphs} 个字形。")

            # 合并所有 Unicode 子表的映射到新的子表中，过滤掉码位大于 0xFFFF 的字符
            for subtable in cmap_table.tables:
                if subtable.isUnicode():
                    for codepoint, glyphName in subtable.cmap.items():
                        if codepoint <= 0xFFFF:
                            # 确保 glyphName 是字符串类型
                            if not isinstance(glyphName, str):
                                glyphName = str(glyphName)
                                logging.warning(f"字形名称非字符串，已转换为字符串：{glyphName}")

                            # 检查字形名称是否在字体中
                            if glyphName in valid_glyph_names:
                                # 获取字形索引并检查范围
                                glyphID = font.getGlyphID(glyphName)
                                if 0 <= glyphID <= 65535:
                                    new_subtable.cmap[codepoint] = glyphName
                                else:
                                    logging.warning(f"字形 '{glyphName}' 的索引 {glyphID} 超出有效范围（0-65535），跳过此映射。")
                            else:
                                logging.warning(f"未找到字形名称 '{glyphName}'，跳过此映射。")
                        else:
                            logging.warning(f"码位 {codepoint} 超出 0xFFFF，跳过此映射。")
            # 添加新的子表到 cmap 表
            cmap_table.tables.append(new_subtable)
            logging.info("已添加 cmap_format_4 子表，提高 Windows 兼容性。")
        else:
            logging.info("cmap_format_4 子表已存在，无需添加。")

        # 移除 cmap_format_2 子表（可选）
        original_subtable_count = len(cmap_table.tables)
        cmap_table.tables = [
            t for t in cmap_table.tables
            if not (t.platformID == 1 and t.platEncID == 1 and t.format == 2)
        ]
        removed_subtables = original_subtable_count - len(cmap_table.tables)
        if removed_subtables > 0:
            logging.debug(f"已移除 {removed_subtables} 个 cmap_format_2 子表。")
    except Exception as e:
        logging.error(f"修复 cmap 表时出错：{e}")
        logging.debug(traceback.format_exc())

if __name__ == '__main__':
    input_dir = 'input'
    output_dir = 'output'

    # 确保输入目录存在
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
        logging.info(f"已创建输入目录：{input_dir}")
        logging.info("请将字体文件放入 input 文件夹中后重新运行程序")
        sys.exit(1)

    process_fonts(input_dir, output_dir)