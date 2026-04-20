import pandas as pd
import json

def update_demand():
    # 1. 读取两个 CSV 文件
    print("正在读取数据文件...")
    try:
        df_products = pd.read_csv('processed_products.csv')
        df_fam = pd.read_csv('data_fam_unconstrained.csv')
    except FileNotFoundError as e:
        print(f"文件读取失败，请检查文件路径和名称是否正确: {e}")
        return

    print(f"processed_products.csv 行数: {len(df_products)}")
    print(f"data_fam_unconstrained.csv 行数: {len(df_fam)}")

    # 2. 判断更新策略
    if len(df_products) == len(df_fam):
        # 策略A：行数完全一致，假设数据行顺序没有被打乱
        # 这种方式最安全，能避免同一航班拥有完全相同票价但舱位不同导致的匹配混淆
        print("检测到行数完全一致，正在逐行将 Unconstrained_Demand 更新到 Total_Demand...")
        df_products['Total_Demand'] = df_fam['Unconstrained_Demand']
        df_final = df_products
    else:
        # 策略B：行数不一致时，通过共有字段(出发地、目的地、航班1/2/3、票价)进行左连接关联匹配
        print("检测到行数不一致，正在根据 起降地、航班号和票价 进行精准列匹配...")
        
        # 为避免不同文件浮点数精度问题导致匹配不上，将 Fare 保留 4 位小数作为匹配键
        df_products['Fare_key'] = df_products['Fare'].astype(float).round(4)
        df_fam['Fare_key'] = df_fam['Fare'].astype(float).round(4)
        
        # 提取 data_fam 中用来匹配的列和所需数据
        df_fam_subset = df_fam[['Origin', 'Destination', 'Flight1', 'Flight2', 'Flight3', 'Fare_key', 'Unconstrained_Demand']].copy()
        
        # 将列名重命名，与 processed_products 保持一致
        df_fam_subset.rename(columns={
            'Origin': 'Org',
            'Destination': 'Des'
        }, inplace=True)
        
        # 去除可能存在的重复项以防合并后数据量膨胀
        df_fam_subset = df_fam_subset.drop_duplicates(subset=['Org', 'Des', 'Flight1', 'Flight2', 'Flight3', 'Fare_key'])
        
        # 执行左连接合并 (Left Join)
        df_final = pd.merge(
            df_products,
            df_fam_subset,
            on=['Org', 'Des', 'Flight1', 'Flight2', 'Flight3', 'Fare_key'],
            how='left'
        )
        
        # 用新需求(Unconstrained_Demand)覆盖旧需求(Total_Demand)
        # 如果某些行没有匹配上，则利用 fillna 保持其原有的 Total_Demand 数据不变
        df_final['Total_Demand'] = df_final['Unconstrained_Demand'].fillna(df_final['Total_Demand'])
        
        # 清理过程中的辅助列
        df_final.drop(columns=['Fare_key', 'Unconstrained_Demand'], inplace=True)

    # === 新增修复：统一处理缺失值，将所有需求中的缺失值(NaN)替换为 0 ===
    df_final['Total_Demand'] = df_final['Total_Demand'].fillna(0)

    # 3. 保存为新的 CSV 文件
    output_file = 'updated_processed_products.csv'
    df_final.to_csv(output_file, index=False)
    print(f"处理完成！新的数据已保存至当前目录下的: {output_file}")

    # 4. 导出为 JSON 字典文件
    print("正在生成与 product_info 同格式的 JSON 字典...")
    try:
        # 确保数据为数值型以符合 JSON 格式预期，如果强制转换出现缺失值同样替换为0
        df_final['Fare'] = pd.to_numeric(df_final['Fare'], errors='coerce').fillna(0)
        df_final['Total_Demand'] = pd.to_numeric(df_final['Total_Demand'], errors='coerce').fillna(0)
        
        # 将 ProductID 设为索引，选取需要的列，并将其转为嵌套字典结构 (orient='index')
        product_dict = df_final.set_index('ProductID')[['Fare', 'Total_Demand']].to_dict(orient='index')
        
        # 写入 JSON 文件
        json_output_file = 'updated_product_info.json'
        with open(json_output_file, 'w', encoding='utf-8') as f:
            json.dump(product_dict, f, indent=4)
        print(f"JSON 字典文件生成完成！已保存至: {json_output_file}")
    except KeyError as e:
        print(f"JSON 导出失败：数据中找不到指定的列 {e}")

if __name__ == "__main__":
    update_demand()