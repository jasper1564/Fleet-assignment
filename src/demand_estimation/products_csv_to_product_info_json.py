import pandas as pd
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RF_PRODUCTS_INPUT = ROOT / "data" / "interim" / "passenger_choice" / "products_with_rf_demand.csv"
RF_PRODUCT_INFO_OUTPUT = ROOT / "data" / "model_input" / "demand" / "product_info_rf_predicted.json"

def generate_json_from_csv(input_csv, output_json):
    """
    从合并后的 CSV 文件生成嵌套字典
    键: ProductID
    值: {"Fare": float, "Total_Demand": float}
    """
    print(f"正在读取文件: {input_csv}...")
    try:
        # 读取 CSV 文件
        df = pd.read_csv(input_csv)
        
        # 验证必要的列是否存在
        required_cols = ['ProductID', 'Fare', 'Total_Demand']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"CSV 文件中缺失必要列: {col}")

        print("正在构建嵌套字典结构...")
        # 构建嵌套字典格式
        # set_index('ProductID') 将 ID 设为键
        # [['Fare', 'Total_Demand']] 选取需要的列
        # to_dict('index') 会生成 {index: {column: value}} 的格式
        product_dict = df.set_index('ProductID')[['Fare', 'Total_Demand']].to_dict('index')

        # 将字典写入 JSON 文件
        print(f"正在保存到: {output_json}...")
        with open(output_json, 'w', encoding='utf-8') as f:
            # indent=4 保持美观的缩进格式
            json.dump(product_dict, f, ensure_ascii=False, indent=4)

        print("生成成功！")
        print(f"共处理产品数量: {len(product_dict)}")
        
        # 打印示例以供检查
        first_key = list(product_dict.keys())[0]
        print(f"示例输出 ({first_key}): {product_dict[first_key]}")

    except FileNotFoundError:
        print(f"错误: 找不到文件 {input_csv}")
    except Exception as e:
        print(f"处理过程中出错: {e}")

if __name__ == "__main__":
    # 输入文件
    input_file = RF_PRODUCTS_INPUT
    # 目标 JSON 文件
    output_file = RF_PRODUCT_INFO_OUTPUT
    
    generate_json_from_csv(input_file, output_file)
