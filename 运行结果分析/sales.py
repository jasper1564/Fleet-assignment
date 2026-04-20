import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. 读取数据
# 请确保 'result_sales.csv' 文件与你的 Python 脚本在同一目录下
df = pd.read_csv('result_sales.csv')

# 2. 设置图表主题和中文字体支持
sns.set_theme(style="whitegrid")
# Windows用户通常用 'SimHei'，Mac用户可以用 'Arial Unicode MS'
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'sans-serif'] 
plt.rcParams['axes.unicode_minus'] = False # 正常显示负号

# 3. 创建画布
plt.figure(figsize=(10, 8))

# 4. 绘制散点图
# x轴为最大需求，y轴为实际销量，alpha设置透明度以应对数据点重叠
sns.scatterplot(data=df, x='Max_Demand', y='Sold_Tickets', 
                alpha=0.5, color='#1f77b4', s=30)

# 5. 添加 y=x (销量=需求) 的参考线
# 获取X轴和Y轴的最大值，用于画对角线
max_val = max(df['Max_Demand'].max(), df['Sold_Tickets'].max())
plt.plot([0, max_val], [0, max_val], 'r--', linewidth=2, label='100%售罄线 (销量 = 需求)')

# 6. 设置标题和坐标轴标签
plt.title('产品销量与最大需求关系图', fontsize=18, fontweight='bold', pad=15)
plt.xlabel('最大需求 (Max Demand)', fontsize=14)
plt.ylabel('实际销量 (Sold Tickets)', fontsize=14)

# 7. 添加图例并调整布局
plt.legend(fontsize=12)
plt.tight_layout()

# 8. 显示图表（或替换为 plt.savefig('sales_vs_demand.png', dpi=300) 保存图片）
plt.show()