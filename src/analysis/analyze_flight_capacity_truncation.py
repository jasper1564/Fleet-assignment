import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_PRODUCTS_INPUT = ROOT / "data" / "raw" / "booking" / "itinerary_sales_by_rd.csv"
FLIGHT_TRUNCATION_OUTPUT = ROOT / "data" / "interim" / "truncation" / "flight_truncation_flags.csv"
FLIGHT_LAST_SALE_FIGURE = ROOT / "results" / "figures" / "truncation" / "flight_last_sale_distribution.png"
FLIGHT_BOOKING_CURVE_FIGURE = ROOT / "results" / "figures" / "truncation" / "flight_booking_curves.png"
FLIGHT_CAPACITY_FIGURE = ROOT / "results" / "figures" / "truncation" / "flight_capacity_ceiling.png"

# 设置图表的中文字体显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS'] 
plt.rcParams['axes.unicode_minus'] = False

def analyze_flight_capacity_truncation(input_filepath, output_filepath, zero_days_threshold=14):
    """
    按行程/航班维度汇总销量，分析是否存在座位容量限制导致的物理截断
    """
    print(f"正在读取数据: {input_filepath}...")
    df = pd.read_csv(input_filepath)
    
    # 1. 识别行程的唯一标识列与 RD 列
    # 假设一个完整行程由这五列唯一确定
    itinerary_cols = ['Origin', 'Destination', 'Flight1', 'Flight2', 'Flight3']
    rd_cols = [col for col in df.columns if col.startswith('RD') and col[2:].isdigit()]
    rd_cols_sorted = sorted(rd_cols, key=lambda x: int(x[2:]), reverse=True)
    
    print("正在按行程(航班)维度加总所有Class的销量...")
    # 2. 按行程分组，对所有 RD 列求和，得到航班级别的销量时间线
    flight_df = df.groupby(itinerary_cols)[rd_cols].sum().reset_index()
    
    # 3. 计算航班级别的总销量与最后销售日期
    flight_df['Flight_Total_Sales'] = flight_df[rd_cols].sum(axis=1)
    
    rd_cols_closest_first = sorted(rd_cols, key=lambda x: int(x[2:])) # [RD0, RD1...]
    
    def get_last_sale_day(row):
        if row['Flight_Total_Sales'] <= 0:
            return np.nan
        for col in rd_cols_closest_first:
            # 航班级别的容差可以稍微大一点，这里设为 1e-3
            if row[col] > 1e-3:
                return int(col[2:])
        return np.nan

    print("正在计算航班最后售出日期及判定截断...")
    flight_df['Flight_Last_Sale_RD'] = flight_df.apply(get_last_sale_day, axis=1)
    
    # 4. 判定航班级别截断 (整个航班起飞前 N 天零销量)
    flight_df['Is_Flight_Truncated'] = (flight_df['Flight_Total_Sales'] > 0) & \
                                       (flight_df['Flight_Last_Sale_RD'] >= zero_days_threshold)
    
    # 打印航班级别的统计数据
    total_flights = len(flight_df[flight_df['Flight_Total_Sales'] > 0])
    truncated_flights = flight_df['Is_Flight_Truncated'].sum()
    print(f"\n--- 航班/行程级别分析结果 ---")
    print(f"有效行程总数 (有销量): {total_flights}")
    print(f"疑似触顶截断的行程数 (起飞前 {zero_days_threshold} 天无销量): {truncated_flights}")
    if total_flights > 0:
        print(f"航班截断比例: {(truncated_flights / total_flights) * 100:.2f}%")
        
    # 5. 将航班级别的判定结果合并回原始的细分 Class 数据中
    # 这样你既可以看到汇总结论，也能追溯每个舱位
    merge_cols = itinerary_cols + ['Flight_Total_Sales', 'Flight_Last_Sale_RD', 'Is_Flight_Truncated']
    result_df = df.merge(flight_df[merge_cols], on=itinerary_cols, how='left')
    
    result_df.to_csv(output_filepath, index=False)
    print(f"\n带航班物理截断标记的数据已保存至: {output_filepath}")
    
    # ================= 绘图与可视化 (基于航班级别) =================
    print("正在生成航班级别的分析图表...")
    
    flight_df_valid = flight_df[flight_df['Flight_Total_Sales'] > 0].copy()
    
    # 图 1：航班最后一次销售日期分布
    plt.figure(figsize=(10, 6))
    sns.histplot(data=flight_df_valid, x='Flight_Last_Sale_RD', bins=30, kde=True, color='purple')
    plt.axvline(x=zero_days_threshold, color='red', linestyle='--', label=f'截断判定阈值 (RD={zero_days_threshold})')
    plt.gca().invert_xaxis()
    plt.title('图1：航班(全舱加总)最后售出日期分布')
    plt.xlabel('距离起飞天数 (RD)')
    plt.ylabel('航班/行程数量')
    plt.legend()
    plt.tight_layout()
    FLIGHT_LAST_SALE_FIGURE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(FLIGHT_LAST_SALE_FIGURE, dpi=300)
    plt.close()
    
    # 图 2：航班级别的平均累积销售曲线
    cumsum_df = flight_df_valid[rd_cols_sorted].cumsum(axis=1)
    curve_data = pd.concat([cumsum_df, flight_df_valid['Is_Flight_Truncated']], axis=1)
    
    avg_normal = curve_data[curve_data['Is_Flight_Truncated'] == False][rd_cols_sorted].mean()
    avg_truncated = curve_data[curve_data['Is_Flight_Truncated'] == True][rd_cols_sorted].mean()
    
    x_days = [int(col[2:]) for col in rd_cols_sorted]
    
    plt.figure(figsize=(12, 6))
    if not avg_normal.isna().all():
        plt.plot(x_days, avg_normal.values, label='正常航班', color='green', linewidth=2)
    if not avg_truncated.isna().all():
        plt.plot(x_days, avg_truncated.values, label='疑似售罄航班 (Truncated)', color='red', linewidth=2)
    
    plt.gca().invert_xaxis()
    plt.title('图2：航班级别(全舱加总) 平均累积销售曲线')
    plt.xlabel('距离起飞天数 (RD)')
    plt.ylabel('航班平均累积总销量')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FLIGHT_BOOKING_CURVE_FIGURE, dpi=300)
    plt.close()
    
    # 图 3：散点图 (寻找物理座位数的“天花板”) - 非常重要
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=flight_df_valid, x='Flight_Last_Sale_RD', y='Flight_Total_Sales', 
                    hue='Is_Flight_Truncated', palette={True: 'red', False: 'green'}, alpha=0.6)
    plt.gca().invert_xaxis()
    plt.title('图3：航班最后售出日期 vs 航班最终总销量 (寻找座位天花板)')
    plt.xlabel('最后售出距起飞天数 (RD)')
    plt.ylabel('航班最终总销量')
    plt.axvline(x=zero_days_threshold, color='black', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(FLIGHT_CAPACITY_FIGURE, dpi=300)
    plt.close()

    print("图表生成完毕！共生成3张航班级别的图表。")

if __name__ == "__main__":
    # 文件路径配置
    input_file = RAW_PRODUCTS_INPUT
    output_file = FLIGHT_TRUNCATION_OUTPUT
    
    analyze_flight_capacity_truncation(input_filepath=input_file, 
                                       output_filepath=output_file, 
                                       zero_days_threshold=7)
