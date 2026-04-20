import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_PRODUCTS_INPUT = ROOT / "data" / "raw" / "booking" / "itinerary_sales_by_rd.csv"
UNCONSTRAINED_DEMAND_OUTPUT = ROOT / "data" / "raw" / "demand" / "itinerary_unconstrained_demand.csv"
EM_FIGURE_OUTPUT = ROOT / "results" / "figures" / "demand_recovery" / "em_demand_recovery_comparison.png"

# 设置图表的中文字体显示
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    pass

# ================= 1. 核心数学函数 =================
def norm_pdf(x):
    """标准正态分布的概率密度函数 (PDF)"""
    return math.exp(-x**2 / 2.0) / math.sqrt(2.0 * math.pi)

def norm_cdf(x):
    """标准正态分布的累积分布函数 (CDF)"""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def get_expected_tail_demand(c, mu, sigma):
    """
    E-Step 核心公式：计算截断正态分布的条件期望 E[X | X > c]
    c: 记录到的受限销量
    mu: 当前迭代的均值
    sigma: 当前迭代的标准差
    """
    if sigma <= 0: return c
    alpha = (c - mu) / sigma
    denom = 1.0 - norm_cdf(alpha)
    
    # 防止分母过小（销量远超均值）导致数学错误
    if denom < 1e-5:
        return c * 1.01 
        
    return mu + sigma * (norm_pdf(alpha) / denom)

# ================= 2. EM 算法主体 (带详细日志) =================
def run_em_with_logging(group_name, df_group, max_iter=30, tolerance=0.05):
    """
    对特定的舱位组运行 EM 算法，并打印迭代过程
    """
    actuals = df_group[df_group['Is_Truncated'] == False]['Total_Sales'].values
    truncated = df_group[df_group['Is_Truncated'] == True]['Total_Sales'].values
    
    if len(truncated) == 0:
        return df_group['Total_Sales'].values
        
    if len(actuals) + len(truncated) < 3:
        # 数据极少的情况，给予一个固定的补偿系数
        return np.where(df_group['Is_Truncated'], df_group['Total_Sales'] * 1.1, df_group['Total_Sales'])
    
    # 【初始状态】
    all_observed = np.concatenate([actuals, truncated])
    mu = np.mean(all_observed)
    sigma = np.std(all_observed)
    if sigma == 0: sigma = 1.0
    
    initial_mu = mu
    unconstrained_truncated = np.copy(truncated)
    
    # 记录是否需要为该组打印详细日志 (只挑取数据量大、具代表性的组打印，避免刷屏)
    log_details = (len(truncated) > 500)
    if log_details:
        print(f"\n[{group_name}] 开始 EM 迭代 -> 初始均值: {initial_mu:.2f}, 截断样本数: {len(truncated)}")

    # 【迭代循环】
    for iteration in range(1, max_iter + 1):
        old_mu = mu
        
        # E-Step: 对每一个被截断的数据，推算真实期望
        for i in range(len(truncated)):
            c = truncated[i]
            unconstrained_truncated[i] = get_expected_tail_demand(c, mu, sigma)
            
        # M-Step: 用推算出的新数据，更新正态分布参数
        new_all_data = np.concatenate([actuals, unconstrained_truncated])
        mu = np.mean(new_all_data)
        sigma = np.std(new_all_data)
        if sigma == 0: sigma = 1.0
        
        # 打印迭代过程
        if log_details and (iteration <= 3 or iteration % 5 == 0 or abs(mu - old_mu) < tolerance):
            print(f"  > 迭代 {iteration:2d} | 均值移动至: {mu:.2f} (变动: {mu - old_mu:+.3f})")
            
        # 检查收敛
        if abs(mu - old_mu) < tolerance:
            if log_details:
                print(f"  ✓ 算法收敛！共迭代 {iteration} 次。")
            break
            
    # 将无约束需求组装回原始顺序
    results = []
    trunc_idx = 0
    for is_trunc, sales in zip(df_group['Is_Truncated'], df_group['Total_Sales']):
        if is_trunc:
            results.append(unconstrained_truncated[trunc_idx])
            trunc_idx += 1
        else:
            results.append(sales)
            
    return np.array(results)

# ================= 3. 数据处理与可视化流程 =================
def main(input_filepath, output_filepath):
    print("🚀 正在加载原始数据...")
    df = pd.read_csv(input_filepath)
    
    rd_cols = [col for col in df.columns if col.startswith('RD') and col[2:].isdigit()]
    df['Total_Sales'] = df[rd_cols].sum(axis=1)
    
    # 清洗：排除无效行
    valid_mask = (df['Total_Sales'] > 0) & (df['Class'].notna())
    df_valid = df[valid_mask].copy()
    
    # 判定截断：使用基于业务逻辑推断的 RD7 阈值
    rd_cols_closest_first = sorted(rd_cols, key=lambda x: int(x[2:]))
    def get_last_sale_day(row):
        for col in rd_cols_closest_first:
            if row[col] > 1e-4: return int(col[2:])
        return np.nan
        
    df_valid['Last_Sale_RD'] = df_valid.apply(get_last_sale_day, axis=1)
    df_valid['Is_Truncated'] = df_valid['Last_Sale_RD'] >= 7
    
    print("\n🧠 启动 EM 期望最大化算法...")
    print("--------------------------------------------------")
    df_valid['Unconstrained_Demand'] = np.nan
    
    # 【核心】按不同的舱位 (Class) 分组执行 EM 算法
    # 因为不同舱位的需求分布 (钟形曲线) 是完全不同的，必须独立拟合
    for class_name, group in df_valid.groupby('Class'):
        restored_demand = run_em_with_logging(f"舱位 {class_name}", group)
        df_valid.loc[group.index, 'Unconstrained_Demand'] = restored_demand
        
    print("--------------------------------------------------")
    
    # 合并结果
    df['Is_Truncated'] = df_valid['Is_Truncated']
    df['Unconstrained_Demand'] = df_valid['Unconstrained_Demand']
    
    # ================= 统计修复成果 =================
    total_original = df['Total_Sales'].sum()
    total_unconstrained = df['Unconstrained_Demand'].sum()
    recovered_demand = total_unconstrained - total_original
    
    print("\n🎉 EM 无约束化计算完成！")
    print(f"📉 原始总销量 (受限记录): {total_original:,.1f}")
    print(f"📈 还原后真需求 (无约束): {total_unconstrained:,.1f}")
    print(f"🔍 成功找回隐形需求:   {recovered_demand:,.1f} (+{(recovered_demand/total_original)*100:.1f}%)")
    
    df.to_csv(output_filepath, index=False)
    print(f"\n💾 带真实需求预测的完整数据已保存至: {output_filepath}")
    
    # ================= 绘制对比直方图 =================
    print("📊 正在生成需求修复对比图表...")
    plt.figure(figsize=(10, 6))
    
    # 只提取被截断的那部分数据进行对比
    truncated_data = df_valid[df_valid['Is_Truncated'] == True]
    
    # 使用 matplotlib 原生直方图 (无内存问题)
    plt.hist(truncated_data['Total_Sales'], bins=40, alpha=0.5, color='gray', label='截断时的表象销量 (Constrained)', density=True)
    plt.hist(truncated_data['Unconstrained_Demand'], bins=40, alpha=0.5, color='dodgerblue', label='EM算法还原的真实需求 (Unconstrained)', density=True)
    
    # 绘制均值线
    mean_orig = truncated_data['Total_Sales'].mean()
    mean_uncon = truncated_data['Unconstrained_Demand'].mean()
    plt.axvline(mean_orig, color='dimgray', linestyle='dashed', linewidth=2, label=f'表象均值: {mean_orig:.1f}')
    plt.axvline(mean_uncon, color='blue', linestyle='dashed', linewidth=2, label=f'真实均值: {mean_uncon:.1f}')
    
    plt.title('图1：受限销量 vs 真实需求 (被截断数据的全貌)')
    plt.xlabel('产品销量/需求量')
    plt.ylabel('频率密度')
    plt.legend()
    plt.xlim(0, max(truncated_data['Unconstrained_Demand']) * 1.1) # 适配右移的长尾
    plt.tight_layout()
    EM_FIGURE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(EM_FIGURE_OUTPUT, dpi=300)
    plt.close()
    print("✅ 对比图已保存为 em_iterative_result.png")

if __name__ == "__main__":
    main(RAW_PRODUCTS_INPUT, UNCONSTRAINED_DEMAND_OUTPUT)
