import pandas as pd
import matplotlib.pyplot as plt
import re

# 设置图表字体，以支持中文字符显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS'] 
plt.rcParams['axes.unicode_minus'] = False

def plot_advanced_scatter(file_path):
    print("正在读取和处理数据...")
    # 1. 读取数据
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"错误: 找不到文件 {file_path}。")
        return

    # 2. 提取座位数
    def extract_capacity(fleet_str):
        if pd.isna(fleet_str):
            return 0
        match = re.search(r'Y(\d+)', str(fleet_str))
        if match:
            return int(match.group(1))
        return 0

    df['Capacity'] = df['Assigned_Fleets'].apply(extract_capacity)
    df['Max_Demand'] = pd.to_numeric(df['Max_Demand'], errors='coerce').fillna(0)
    df['Sold_Tickets'] = pd.to_numeric(df['Sold_Tickets'], errors='coerce').fillna(0)

    # 3. 按航段聚合数据
    agg_df = df.groupby('Legs').agg(
        Total_Demand=('Max_Demand', 'sum'),
        Total_Sold=('Sold_Tickets', 'sum'),
        Seat_Capacity=('Capacity', 'first')
    ).reset_index()

    # 清洗异常值：过滤掉座位数为 0 的无效航段
    agg_df = agg_df[agg_df['Seat_Capacity'] > 0].copy()

    # 4. 衍生指标：计算客座率 (Load Factor)
    agg_df['Load_Factor'] = agg_df['Total_Sold'] / agg_df['Seat_Capacity']
    # 限制最高客座率为 1.0 (防止超售数据导致颜色比例失衡)
    agg_df['Load_Factor'] = agg_df['Load_Factor'].clip(upper=1.0)

    print(f"数据聚合完成，共有 {len(agg_df)} 个有效航段参与绘图...")

    # 5. 开始绘制高级气泡图
    fig, ax = plt.subplots(figsize=(12, 10))

    # 绘制气泡 (Scatter)
    scatter = ax.scatter(
        x=agg_df['Total_Sold'], 
        y=agg_df['Total_Demand'], 
        s=agg_df['Seat_Capacity'] * 1.5,   
        c=agg_df['Load_Factor'],           
        cmap='coolwarm',                   
        alpha=0.7,                         
        edgecolors='white',                
        linewidth=0.5
    )

    # 6. 画出关键的 y = x 参考线 (销量 = 需求)
    max_val = max(agg_df['Total_Demand'].max(), agg_df['Total_Sold'].max())
    line_yx, = ax.plot([0, max_val * 1.05], [0, max_val * 1.05], 
                       color='black', linestyle='--', alpha=0.6, 
                       label='销量 = 需求 (理想状态)')

    # 7. 添加颜色条 (Colorbar) 解释颜色含义
    cbar = plt.colorbar(scatter, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label('客座率 (Load Factor)', fontsize=12, labelpad=10)
    cbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])
    cbar.set_ticklabels(['0%', '25%', '50%', '75%', '满载 (100%)'])

    # 8. 添加大小图例 (Legend for size) 解释圈圈大小含义
    legend_sizes = [50, 150, 300] 
    for size in legend_sizes:
        ax.scatter([], [], s=size * 1.5, c='gray', alpha=0.6, edgecolors='white', label=f'{size} 座')
    
    # 整合所有图例
    ax.legend(title="图例说明", loc='upper left', scatterpoints=1, frameon=True, fontsize=10)

    # 9. 设置图表格式
    ax.set_title('航班需求、销量与座位数综合气泡图', fontsize=18, pad=20)
    ax.set_xlabel('总销量 (Sold Tickets)', fontsize=14)
    ax.set_ylabel('总需求 (Max Demand)', fontsize=14)
    
    # 设置坐标轴从 0 开始
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    
    ax.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    
    # 呈现图表
    plt.show()

if __name__ == "__main__":
    csv_file_path = 'result_comprehensive_analysis.csv'
    plot_advanced_scatter(csv_file_path)