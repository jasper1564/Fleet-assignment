import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 读取数据
df = pd.read_csv('result_assignment.csv')

# 提取任务前缀并替换为中文显示
df['Airline'] = df['Task'].str.extract(r'^([a-zA-Z_]+)')[0]
df['Airline'] = df['Airline'].replace({
    'AA': 'AA', 
    'BA': 'BA', 
    'super_AA': '超级 AA', 
    'super_BA': '超级 BA'
})

# 设置主题和中文字体支持
sns.set_theme(style="whitegrid")
# 使用常见的受支持的中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'sans-serif'] 
plt.rcParams['axes.unicode_minus'] = False

# 绘制图表
plt.figure(figsize=(10, 6))
sns.countplot(data=df, x='Airline', hue='Assigned_Fleet', palette='Set2')
plt.title('各航司/任务类型的机型分配数量对比', fontsize=16, fontweight='bold')
plt.xlabel('航司 / 任务类型', fontsize=12)
plt.ylabel('分配航班数量', fontsize=12)
plt.legend(title='分配机型', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()

# 保存图表
plt.savefig('bar_chart_chinese.png', dpi=300)
plt.close()