import pandas as pd

def update_demand_values(processed_path, q2_path, output_path):
    """
    根据产品特征匹配，将 q2 文件中的 corrected_demand 替换到 processed 文件的 total_demand 中。
    通过预先去重 q2 数据，防止合并后行数膨胀。
    """
    print("正在读取文件...")
    df_processed = pd.read_csv(processed_path)
    df_q2 = pd.read_csv(q2_path)

    # 1. 准备连接键 (Matching Keys)
    # 定义用于识别唯一产品的列名组合
    match_keys = ['Org', 'Des', 'Flight1', 'Flight2', 'Flight3', 'Fare']
    
    # 提取 q2 数据并重命名列名以匹配 processed 文件
    df_q2_subset = df_q2[[
        'Origin', 'Destination', 'Flight1', 'Flight2', 'Flight3', 'Fare', 'corrected_demand'
    ]].rename(columns={
        'Origin': 'Org',
        'Destination': 'Des'
    })

    # --- 重要步骤：处理重复项 ---
    # 如果 q2 中同一个产品有多个 corrected_demand，合并会导致行数变多
    # 这里我们按 match_keys 分组并取均值（或者取第一个 first()），确保每个产品唯一
    before_count = len(df_q2_subset)
    df_q2_unique = df_q2_subset.groupby(match_keys, as_index=False)['corrected_demand'].mean()
    after_count = len(df_q2_unique)
    
    if before_count > after_count:
        print(f"提示：q2 文件中存在 {before_count - after_count} 条重复的产品记录，已执行均值聚合。")

    # 2. 执行左连接 (Left Join)
    # validate='many_to_one' 确保左表的每一行最多匹配右表的一行，防止行数增加
    print("正在根据产品信息进行匹配...")
    merged_df = pd.merge(
        df_processed, 
        df_q2_unique, 
        on=match_keys, 
        how='left',
        validate='many_to_one' 
    )

    # 3. 替换数值
    print("正在更新需求数值...")
    # 使用 corrected_demand 覆盖 Total_Demand，若无匹配则保留原值
    merged_df['Total_Demand'] = merged_df['corrected_demand'].fillna(merged_df['Total_Demand'])

    # 4. 清理并保存
    final_df = merged_df.drop(columns=['corrected_demand'])

    # 保存结果
    final_df.to_csv(output_path, index=False)
    print(f"处理完成！结果已保存至: {output_path}")
    print(f"原始行数: {len(df_processed)}")
    print(f"最终行数: {len(final_df)}")
    
    if len(df_processed) != len(final_df):
        print("警告：最终行数与原始行数不一致，请检查数据！")

if __name__ == "__main__":
    processed_file = 'processed_products.csv'
    q2_file = 'q2_corrected_demand.csv'
    output_file = 'updated_processed_products.csv'

    try:
        update_demand_values(processed_file, q2_file, output_file)
    except Exception as e:
        print(f"发生错误: {e}")