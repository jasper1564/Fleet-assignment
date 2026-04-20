import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_PRODUCTS_INPUT = ROOT / "data" / "raw" / "booking" / "itinerary_sales_by_rd.csv"
ITINERARY_TRUNCATION_OUTPUT = ROOT / "data" / "interim" / "truncation" / "itinerary_truncation_flags.csv"
LAST_SALE_FIGURE = ROOT / "results" / "figures" / "truncation" / "itinerary_last_sale_distribution.png"
BOOKING_CURVE_FIGURE = ROOT / "results" / "figures" / "truncation" / "itinerary_booking_curves.png"
SCATTER_FIGURE = ROOT / "results" / "figures" / "truncation" / "itinerary_sales_vs_last_sale_rd.png"

# 设置图表的中文字体显示（避免中文乱码）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS'] 
plt.rcParams['axes.unicode_minus'] = False

def analyze_sales_truncation(input_filepath, output_filepath, zero_days_threshold=14):
    """
    分析产品销量截断现象
    
    :param input_filepath: 原始CSV数据路径
    :param output_filepath: 分析结果保存路径
    :param zero_days_threshold: 判定截断的阈值（起飞前连续多少天销量为0被认为是截断）
    """
    print(f"正在读取数据: {input_filepath}...")
    df = pd.read_csv(input_filepath)
    
    # 1. 提取所有 RD 列，并按天数从大到小排序 (e.g., RD330, RD269 ... RD0)
    # 这代表了时间流逝的方向：距离起飞天数越来越少
    rd_cols = [col for col in df.columns if col.startswith('RD') and col[2:].isdigit()]
    rd_cols_sorted = sorted(rd_cols, key=lambda x: int(x[2:]), reverse=True)
    
    # 2. 计算每个产品的总销量
    print("正在计算总销量与寻找最后销售日期...")
    df['Total_Sales'] = df[rd_cols].sum(axis=1)
    
    # 3. 寻找最后一次产生销量的日期 (Last_Sale_RD)
    # 我们从 RD0 (最近) 往回找，找到第一个销量 > 0 的 RD
    rd_cols_closest_first = sorted(rd_cols, key=lambda x: int(x[2:])) # [RD0, RD1, RD2...]
    
    def get_last_sale_day(row):
        # 排除完全没有销量的废弃产品
        if row['Total_Sales'] <= 0:
            return np.nan
        for col in rd_cols_closest_first:
            # 考虑到浮点数精度，设置一个极小值阈值
            if row[col] > 1e-4:
                return int(col[2:])
        return np.nan

    df['Last_Sale_RD'] = df.apply(get_last_sale_day, axis=1)
    
    # 4. 判定截断 (Flagging)
    # 逻辑：总销量大于0，且最后一次产生销量的日期 >= zero_days_threshold
    # 例如 threshold=14，意味着 RD0 到 RD13 全是 0，最后一次销售停留在 RD14 或更早
    df['Is_Truncated'] = (df['Total_Sales'] > 0) & (df['Last_Sale_RD'] >= zero_days_threshold)
    
    # 输出基本统计信息
    total_products = len(df[df['Total_Sales'] > 0])
    truncated_products = df['Is_Truncated'].sum()
    print(f"\n--- 分析结果统计 ---")
    print(f"有效产品总数 (有销量): {total_products}")
    print(f"疑似截断产品数 (起飞前 {zero_days_threshold} 天及以内无销量): {truncated_products}")
    if total_products > 0:
        print(f"截断比例: {(truncated_products / total_products) * 100:.2f}%")
    
    # 5. 保存结果到新的 CSV
    df.to_csv(output_filepath, index=False)
    print(f"\n带有截断标记的数据已保存至: {output_filepath}")
    
    # ================= 绘图与可视化 =================
    print("正在生成可视化分析图表...")
    
    # 过滤掉完全没卖出去的产品，避免干扰图表
    df_valid = df[df['Total_Sales'] > 0].copy()
    
    # 图 1：最后一次销售发生的日期分布 (判断在起飞前多少天售罄最常见)
    plt.figure(figsize=(10, 6))
    sns.histplot(data=df_valid, x='Last_Sale_RD', bins=30, kde=True, color='skyblue')
    plt.axvline(x=zero_days_threshold, color='red', linestyle='--', label=f'截断判定阈值 (RD={zero_days_threshold})')
    plt.gca().invert_xaxis() # X轴反转，符合业务直觉：从左到右靠近起飞
    plt.title('图1：产品最后一次销售日期 (Last Sale RD) 分布')
    plt.xlabel('距离起飞天数 (RD)')
    plt.ylabel('产品数量')
    plt.legend()
    plt.tight_layout()
    LAST_SALE_FIGURE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(LAST_SALE_FIGURE, dpi=300)
    plt.close()
    
    # 图 2：正常产品 vs 截断产品的平均累积销售曲线 (Booking Curve)
    # 计算累计销量
    cumsum_df = df_valid[rd_cols_sorted].cumsum(axis=1)
    # 将累计数据与截断标记合并
    curve_data = pd.concat([cumsum_df, df_valid['Is_Truncated']], axis=1)
    
    # 计算均值
    avg_normal_curve = curve_data[curve_data['Is_Truncated'] == False][rd_cols_sorted].mean()
    avg_truncated_curve = curve_data[curve_data['Is_Truncated'] == True][rd_cols_sorted].mean()
    
    # 提取 X 轴天数
    x_days = [int(col[2:]) for col in rd_cols_sorted]
    
    plt.figure(figsize=(12, 6))
    if not avg_normal_curve.isna().all():
        plt.plot(x_days, avg_normal_curve.values, label='正常产品 (Normal)', color='green', linewidth=2)
    if not avg_truncated_curve.isna().all():
        plt.plot(x_days, avg_truncated_curve.values, label='疑似截断产品 (Truncated)', color='red', linewidth=2)
    
    plt.gca().invert_xaxis() # X轴反转：330 -> 0
    plt.title('图2：平均生命周期累积销售曲线 (Booking Curve)')
    plt.xlabel('距离起飞天数 (RD)')
    plt.ylabel('平均累积销量')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(BOOKING_CURVE_FIGURE, dpi=300)
    plt.close()
    
    # 图 3：散点图：最后销售日期 vs 总销量 (观察是否存在天花板效应)
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df_valid, x='Last_Sale_RD', y='Total_Sales', 
                    hue='Is_Truncated', palette={True: 'red', False: 'green'}, alpha=0.6)
    plt.gca().invert_xaxis()
    plt.title('图3：最后销售日期 vs 最终总销量')
    plt.xlabel('最后销售距起飞天数 (RD)')
    plt.ylabel('最终总销量')
    plt.axvline(x=zero_days_threshold, color='black', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(SCATTER_FIGURE, dpi=300)
    plt.close()

    print("图表生成完毕！共生成3张图片。")

if __name__ == "__main__":
    # 输入文件为用户上传的csv，输出为加了标签的新csv
    input_file = RAW_PRODUCTS_INPUT
    output_file = ITINERARY_TRUNCATION_OUTPUT
    
    # 你可以修改判定阈值，默认设置起飞前14天及以内无销量即判定为截断
    analyze_sales_truncation(input_filepath=input_file, 
                             output_filepath=output_file, 
                             zero_days_threshold=7)
