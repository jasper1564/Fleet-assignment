import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 设置图表的中文字体显示（适配多系统）
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    pass

def analyze_fare_level_truncation(input_filepath, output_filepath, zero_days_threshold=7):
    """
    按票价高低分层，分析销量截断情况。
    验证是否为“收益管理关舱策略”（低价早截断，高价晚截断）。
    """
    print(f"正在读取数据: {input_filepath}...")
    df = pd.read_csv(input_filepath)
    
    # 1. 提取 RD 列并计算产品（舱位级别）的总销量
    rd_cols = [col for col in df.columns if col.startswith('RD') and col[2:].isdigit()]
    rd_cols_sorted = sorted(rd_cols, key=lambda x: int(x[2:]), reverse=True)
    df['Total_Sales'] = df[rd_cols].sum(axis=1)
    
    # 过滤掉完全没销量的无效行和没有票价的行
    valid_df = df[(df['Total_Sales'] > 0) & (df['Fare'].notna())].copy()
    
    # 2. 对票价进行分层 (Fare Leveling)
    # 为了防止跨航线的绝对价格不可比（比如长航线和短航线），
    # 我们按每个行程（Origin, Dest, Flight组合）内的价格进行相对高低划分。
    print("正在按行程内的相对价格对舱位进行分层...")
    itinerary_cols = ['Origin', 'Destination', 'Flight1', 'Flight2', 'Flight3']
    
    def assign_fare_level(group):
        # 使用 qcut (分位数) 将同一个行程内的舱位按价格分为 高、中、低 三档
        # 加上 rank 处理重复价格导致的 qcut 错误
        try:
            # 如果价格完全一样或者数据量太少，退回到简单的分档
            if len(group) < 3 or group['Fare'].nunique() < 3:
                return pd.qcut(group['Fare'].rank(method='first'), 3, labels=['低价舱(Low)', '中价舱(Med)', '高价舱(High)'])
            return pd.qcut(group['Fare'], 3, labels=['低价舱(Low)', '中价舱(Med)', '高价舱(High)'])
        except ValueError:
             # 如果仍然失败，统一标记为未知
            return pd.Series(['未知(Unknown)'] * len(group), index=group.index)

    valid_df['Fare_Level'] = valid_df.groupby(itinerary_cols, group_keys=False).apply(assign_fare_level)
    
    # 3. 计算最后销售日期 (Last Sale RD)
    print("正在计算各舱位最后售出日期及判定截断...")
    rd_cols_closest_first = sorted(rd_cols, key=lambda x: int(x[2:]))
    
    def get_last_sale_day(row):
        for col in rd_cols_closest_first:
            if row[col] > 1e-4:
                return int(col[2:])
        return np.nan

    valid_df['Last_Sale_RD'] = valid_df.apply(get_last_sale_day, axis=1)
    
    # 4. 判定截断
    valid_df['Is_Truncated'] = valid_df['Last_Sale_RD'] >= zero_days_threshold
    
    # 排除分档失败的未知数据
    analysis_df = valid_df[valid_df['Fare_Level'] != '未知(Unknown)']
    
    # ================= 打印统计报告 =================
    print(f"\n--- 票价等级(Fare Level) 截断差异报告 (阈值: RD{zero_days_threshold}) ---")
    summary = []
    for level in ['高价舱(High)', '中价舱(Med)', '低价舱(Low)']:
        subset = analysis_df[analysis_df['Fare_Level'] == level]
        total_n = len(subset)
        if total_n == 0: continue
        trunc_n = subset['Is_Truncated'].sum()
        trunc_rate = trunc_n / total_n
        avg_last_rd = subset['Last_Sale_RD'].mean()
        
        summary.append({
            '票价等级': level,
            '有销量的舱位数': total_n,
            '截断舱位数': trunc_n,
            '截断率': f"{trunc_rate:.1%}",
            '平均最后售出时间(RD)': f"{avg_last_rd:.1f}"
        })
        
    summary_df = pd.DataFrame(summary)
    print(summary_df.to_markdown(index=False))
    
    # ================= 可视化分析 =================
    print("\n正在生成票价等级对比图表...")
    fare_colors = {'高价舱(High)': 'crimson', '中价舱(Med)': 'gold', '低价舱(Low)': 'steelblue'}
    
    # 图 1：不同票价等级的截断率对比柱状图
    plt.figure(figsize=(9, 6))
    summary_df['截断率数值'] = summary_df['截断率'].str.rstrip('%').astype(float) / 100
    
    # 使用纯 matplotlib 的柱状图替换 seaborn
    colors = [fare_colors.get(level) for level in summary_df['票价等级']]
    plt.bar(summary_df['票价等级'], summary_df['截断率数值'], color=colors)
    
    for index, row in summary_df.iterrows():
        plt.text(index, row['截断率数值'] + 0.01, row['截断率'], color='black', ha="center", fontsize=12)
    plt.title('图1：不同票价等级舱位的销量截断率对比')
    plt.ylabel('截断比例')
    plt.ylim(0, max(summary_df['截断率数值']) * 1.2)
    plt.tight_layout()
    plt.savefig('fare_plot_1_truncation_rate.png', dpi=300)
    plt.close()

    # 图 2：截断发生时间的直方图 (替换 KDE，降低内存消耗)
    plt.figure(figsize=(11, 6))
    for level in ['高价舱(High)', '中价舱(Med)', '低价舱(Low)']:
        subset = analysis_df[analysis_df['Fare_Level'] == level]
        if not subset.empty and len(subset) > 1:
            # 使用 matplotlib 的 density=True 直方图来表现分布趋势
            plt.hist(subset['Last_Sale_RD'].dropna(), bins=20, density=True, 
                     histtype='stepfilled', alpha=0.3, color=fare_colors.get(level), label=level)
            plt.hist(subset['Last_Sale_RD'].dropna(), bins=20, density=True, 
                     histtype='step', alpha=1.0, color=fare_colors.get(level), linewidth=1.5)
            
    plt.axvline(x=zero_days_threshold, color='black', linestyle='--', alpha=0.5, label='截断判定线')
    plt.gca().invert_xaxis()
    plt.title('图2：各票价等级的“最后销售时间 (Last Sale RD)” 分布直方图')
    plt.xlabel('最后售出距起飞天数 (RD)')
    plt.ylabel('分布密度')
    plt.legend()
    plt.tight_layout()
    plt.savefig('fare_plot_2_death_time_dist.png', dpi=300)
    plt.close()

    # 图 3：各票价等级平均Booking Curve
    plt.figure(figsize=(12, 6))
    for level in ['高价舱(High)', '中价舱(Med)', '低价舱(Low)']:
        subset = analysis_df[analysis_df['Fare_Level'] == level]
        if not subset.empty:
            cumsum_data = subset[rd_cols_sorted].cumsum(axis=1).mean()
            x_days = [int(col[2:]) for col in rd_cols_sorted]
            plt.plot(x_days, cumsum_data.values, label=f'{level} 平均累积销量', color=fare_colors.get(level), linewidth=2.5)
            
    plt.gca().invert_xaxis()
    plt.title('图3：不同票价等级的生命周期累积销售曲线')
    plt.xlabel('距离起飞天数 (RD)')
    plt.ylabel('平均累积总销量')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('fare_plot_3_booking_curves.png', dpi=300)
    plt.close()

    print("图表生成完毕！重点观察 fare_plot_2 寻找关舱策略证据。")

if __name__ == "__main__":
    analyze_fare_level_truncation(input_filepath="data_fam_products.csv", 
                                  output_filepath="data_fam_fare_level_analyzed.csv",
                                  zero_days_threshold=7)