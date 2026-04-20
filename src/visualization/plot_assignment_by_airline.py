import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSIGNMENT_INPUT = ROOT / "results" / "runs" / "root_current" / "assignment.csv"
FIGURE_OUTPUT = ROOT / "results" / "figures" / "post_analysis" / "assignment_by_airline.png"

# 读取数据
df = pd.read_csv(ASSIGNMENT_INPUT)

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
FIGURE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(FIGURE_OUTPUT, dpi=300)
plt.close()
