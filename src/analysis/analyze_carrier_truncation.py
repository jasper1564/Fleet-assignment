import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_PRODUCTS_INPUT = ROOT / "data" / "raw" / "booking" / "itinerary_sales_by_rd.csv"
CARRIER_TRUNCATION_OUTPUT = ROOT / "data" / "interim" / "truncation" / "carrier_truncation_flags.csv"
CARRIER_RATE_FIGURE = ROOT / "results" / "figures" / "truncation" / "carrier_truncation_rate.png"
CARRIER_RD_FIGURE = ROOT / "results" / "figures" / "truncation" / "carrier_last_sale_rd_distribution.png"
CARRIER_BOOKING_FIGURE = ROOT / "results" / "figures" / "truncation" / "carrier_booking_curves.png"

# 设置图表的中文字体显示（适配多系统）
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    pass # 忽略字体设置错误

def identify_carrier_type(row):
    """
    根据行程中的航班号前缀判断承运人属性
    - A_Only: 所有航班以 AA 开头（或空）
    - B_Only: 所有航班以 BA 开头（或空）
    - Joint_Venture_AB: 包含 AA 和 BA
    - Unknown: 包含除 AA, BA 之外的前缀，或者无有效航班号
    """
    flights = [str(row['Flight1']).strip(), str(row['Flight2']).strip(), str(row['Flight3']).strip()]
    has_aa = False
    has_ba = False
    has_other = False
    
    # 遍历行程中的所有航班
    for f in flights:
        if f == '.' or f == 'nan' or f == '' or f == 'None':
            continue
        # 根据前两个字母判断
        if f.startswith('AA'):
            has_aa = True
        elif f.startswith('BA'):
            has_ba = True
        else:
            has_other = True

    # 逻辑判断
    if has_aa and has_ba:
        return 'Joint_Venture_AB'
    elif has_aa and not has_ba and not has_other:
        return 'A_Only'
    elif has_ba and not has_aa and not has_other:
        return 'B_Only'
    else:
        # 如果存在其他开头的航班，或者完全为空，归类为未知
        return 'Unknown'


def analyze_carrier_truncation(input_filepath, output_filepath, zero_days_threshold=7):
    """
    分析不同承运人属性（A, B, 合营）下的销量截断情况
    """
    print(f"正在读取数据: {input_filepath}...")
    df = pd.read_csv(input_filepath)
    
    # 1. 识别行程特征与 RD 列
    itinerary_cols = ['Origin', 'Destination', 'Flight1', 'Flight2', 'Flight3']
    rd_cols = [col for col in df.columns if col.startswith('RD') and col[2:].isdigit()]
    rd_cols_sorted = sorted(rd_cols, key=lambda x: int(x[2:]), reverse=True)
    
    print("正在按行程维度加总销量...")
    flight_df = df.groupby(itinerary_cols)[rd_cols].sum().reset_index()
    
    print("正在判定承运人属性 (A, B, 或合营)...")
    flight_df['Carrier_Type'] = flight_df.apply(identify_carrier_type, axis=1)
    
    # 2. 计算航班总销量与最后销售日期
    flight_df['Total_Sales'] = flight_df[rd_cols].sum(axis=1)
    rd_cols_closest_first = sorted(rd_cols, key=lambda x: int(x[2:]))
    
    def get_last_sale_day(row):
        if row['Total_Sales'] <= 0:
            return np.nan
        for col in rd_cols_closest_first:
            if row[col] > 1e-3:
                return int(col[2:])
        return np.nan

    print("正在计算截断点...")
    flight_df['Last_Sale_RD'] = flight_df.apply(get_last_sale_day, axis=1)
    
    # 3. 判定截断 (此处使用你提到的 7 天阈值)
    flight_df['Is_Truncated'] = (flight_df['Total_Sales'] > 0) & \
                                (flight_df['Last_Sale_RD'] >= zero_days_threshold)
    
    # 过滤掉无效行程（完全没销量或未知承运人）
    valid_flights = flight_df[(flight_df['Total_Sales'] > 0) & (flight_df['Carrier_Type'] != 'Unknown')]
    
    # ================= 打印统计报告 =================
    print(f"\n--- 承运人截断差异报告 (阈值: RD{zero_days_threshold}) ---")
    summary = []
    for carrier in ['A_Only', 'B_Only', 'Joint_Venture_AB']:
        subset = valid_flights[valid_flights['Carrier_Type'] == carrier]
        total_n = len(subset)
        if total_n == 0:
            continue
        trunc_n = subset['Is_Truncated'].sum()
        trunc_rate = trunc_n / total_n
        avg_last_rd = subset[subset['Is_Truncated'] == True]['Last_Sale_RD'].mean()
        
        summary.append({
            '承运方': carrier,
            '总行程数': total_n,
            '截断行程数': trunc_n,
            '截断率': f"{trunc_rate:.1%}",
            '截断发生平均时间点(RD)': f"{avg_last_rd:.1f}" if pd.notna(avg_last_rd) else "N/A"
        })
        
    summary_df = pd.DataFrame(summary)
    print(summary_df.to_markdown(index=False))
    
    # 5. 保存结果
    merge_cols = itinerary_cols + ['Carrier_Type', 'Total_Sales', 'Last_Sale_RD', 'Is_Truncated']
    result_df = df.merge(flight_df[merge_cols], on=itinerary_cols, how='left')
    result_df.to_csv(output_filepath, index=False)
    print(f"\n数据已保存至: {output_filepath}")

    # ================= 强力可视化：寻找 B 公司数据断层铁证 =================
    print("\n正在生成承运人对比分析图表...")
    
    # 设置图表颜色映射
    carrier_colors = {'A_Only': 'dodgerblue', 'B_Only': 'darkorange', 'Joint_Venture_AB': 'forestgreen'}
    
    # 图1：截断率对比柱状图
    plt.figure(figsize=(10, 6))
    summary_df['截断率数值'] = summary_df['截断率'].str.rstrip('%').astype(float) / 100
    sns.barplot(data=summary_df, x='承运方', y='截断率数值', palette=carrier_colors)
    for index, row in summary_df.iterrows():
        plt.text(index, row['截断率数值'] + 0.01, row['截断率'], color='black', ha="center", fontsize=12)
    plt.title('图1：不同承运方的销量截断率对比 (核心证据)')
    plt.ylabel('截断行程比例')
    plt.ylim(0, max(summary_df['截断率数值']) * 1.2) # 留出标签空间
    plt.tight_layout()
    CARRIER_RATE_FIGURE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(CARRIER_RATE_FIGURE, dpi=300)
    plt.close()
    
    # 图2：截断发生时间的核密度分布图 (KDE) - 极其关键！
    # 如果 B 公司是因为系统问题断了，它的峰值会非常集中且尖锐
    plt.figure(figsize=(12, 6))
    for carrier in ['A_Only', 'B_Only', 'Joint_Venture_AB']:
        subset = valid_flights[(valid_flights['Carrier_Type'] == carrier) & (valid_flights['Is_Truncated'] == True)]
        if not subset.empty and len(subset) > 1: # 需要足够数据点画 KDE
            sns.kdeplot(data=subset, x='Last_Sale_RD', label=carrier, color=carrier_colors.get(carrier), linewidth=2, fill=True, alpha=0.1)
    
    plt.axvline(x=zero_days_threshold, color='red', linestyle='--', alpha=0.5, label='判定阈值')
    plt.gca().invert_xaxis()
    plt.title('图2：各承运方截断行程的“死亡时间”分布 (Last Sale RD)')
    plt.xlabel('最后售出距起飞天数 (RD)')
    plt.ylabel('分布密度')
    plt.legend()
    plt.tight_layout()
    plt.savefig(CARRIER_RD_FIGURE, dpi=300)
    plt.close()
    
    # 图3：各阵营的 Booking Curve 对比
    plt.figure(figsize=(14, 7))
    for carrier in ['A_Only', 'B_Only', 'Joint_Venture_AB']:
        subset = valid_flights[valid_flights['Carrier_Type'] == carrier]
        if not subset.empty:
            cumsum_data = subset[rd_cols_sorted].cumsum(axis=1).mean()
            x_days = [int(col[2:]) for col in rd_cols_sorted]
            plt.plot(x_days, cumsum_data.values, label=f'{carrier} (平均曲线)', color=carrier_colors.get(carrier), linewidth=2.5)
            
    plt.gca().invert_xaxis()
    plt.title('图3：各承运方的平均生命周期累积销售曲线 (Booking Curve)')
    plt.xlabel('距离起飞天数 (RD)')
    plt.ylabel('平均累积总销量')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(CARRIER_BOOKING_FIGURE, dpi=300)
    plt.close()
    
    print("生成完毕！重点关注 carrier_plot_1 和 carrier_plot_2 寻找数据丢失证据。")

if __name__ == "__main__":
    analyze_carrier_truncation(input_filepath=RAW_PRODUCTS_INPUT, 
                               output_filepath=CARRIER_TRUNCATION_OUTPUT, 
                               zero_days_threshold=7)
