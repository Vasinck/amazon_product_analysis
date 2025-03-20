import pandas as pd
from typing import List

def extract_my_product_name(
    file_path: str, 
    save_to_file: bool = False, 
    output_file: str = "流量词列表.txt"
) -> List[str]:
    """
    从Excel文件中提取第一列(流量词)数据
    
    参数:
        file_path (str): Excel文件的路径
        save_to_file (bool, optional): 是否将提取的流量词保存到文本文件，默认为False
        output_file (str, optional): 输出文本文件的路径，默认为"流量词列表.txt"
        
    返回:
        List[str]: 包含所有流量词的列表
        
    异常:
        FileNotFoundError: 当指定的文件不存在时抛出
        Exception: 当读取或处理文件时发生其他错误时抛出
    """
    try:
        # 使用pandas读取Excel文件
        df = pd.read_excel(file_path)
        
        # 获取第一列名称(流量词)
        first_column_name = df.columns[0]
        
        # 提取第一列(流量词)的所有数据
        traffic_words = df[first_column_name].tolist()
        
        # 如果需要保存到文件
        if save_to_file:
            with open(output_file, "w", encoding="utf-8") as f:
                for word in traffic_words:
                    if pd.notna(word):  # 检查是否为NaN值
                        f.write(f"{word}\n")
            print(f"流量词已保存到 '{output_file}' 文件")
        
        return traffic_words
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 '{file_path}'")
        raise
    except Exception as e:
        print(f"错误: {e}")
        raise

# 如果直接运行此脚本（而不是作为模块导入）
if __name__ == "__main__":
    # 示例用法
    file_path = "红白蓝五星窗户灯词库_更新_20250318_151413.xlsx"
    words = extract_my_product_name(file_path)
    
    print(words)