import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEDULE_INPUT = ROOT / "data" / "raw" / "schedule" / "flight_schedule.csv"
PRODUCTS_INPUT = ROOT / "data" / "raw" / "booking" / "itinerary_sales_by_rd.csv"
PROCESSED_SCHEDULE_OUTPUT = ROOT / "data" / "interim" / "network" / "processed_schedule.csv"
PROCESSED_PRODUCTS_OUTPUT = ROOT / "data" / "interim" / "products" / "products_with_total_demand.csv"
PRODUCT_LEG_MAPPING_OUTPUT = ROOT / "data" / "interim" / "network" / "product_leg_mapping.csv"

# ==========================================
# 0. 读取原始数据
# ==========================================
print("正在读取原始数据...")
# 请确保这两个文件与你的 Python 脚本在同一个文件夹下
try:
    df_schedule = pd.read_csv(SCHEDULE_INPUT)
    df_products = pd.read_csv(PRODUCTS_INPUT)
except FileNotFoundError as e:
    print(f"错误：找不到文件。请确保原始CSV文件存在。详细信息: {e}")
    exit()

# ==========================================
# 任务 1：航班时刻的数值化与时长计算
# ==========================================
print("\n开始执行任务 1：航班时刻转换...")

def time_to_minutes(t):
    if pd.isna(t):
        return np.nan
    t_str = str(t).replace(':', '').replace('.0', '').strip()
    t_str = t_str.zfill(4) 
    try:
        return int(t_str[:2]) * 60 + int(t_str[2:])
    except ValueError:
        return np.nan

def offset_to_minutes(off):
    if pd.isna(off):
        return 0
    off_str = str(int(off)).strip()
    sign = -1 if off_str.startswith('-') else 1
    off_str = off_str.replace('-', '').zfill(4)
    try:
        return sign * (int(off_str[:2]) * 60 + int(off_str[2:]))
    except ValueError:
        return 0

# 计算本地分钟数和偏移量
df_schedule['dep_min_local'] = df_schedule['deptime'].apply(time_to_minutes)
df_schedule['arr_min_local'] = df_schedule['arrtime'].apply(time_to_minutes)
df_schedule['dep_offset_min'] = df_schedule['depoff'].apply(offset_to_minutes)
df_schedule['arr_offset_min'] = df_schedule['arroff'].apply(offset_to_minutes)

# 统一转换为 UTC 时间并限制在 0-1439 范围内
df_schedule['DepTime_UTC'] = (df_schedule['dep_min_local'] - df_schedule['dep_offset_min']) % 1440
df_schedule['ArrTime_UTC'] = (df_schedule['arr_min_local'] - df_schedule['arr_offset_min']) % 1440

# 计算飞行时长与跨夜标签
def calculate_duration(row):
    if pd.isna(row['DepTime_UTC']) or pd.isna(row['ArrTime_UTC']):
        return np.nan
    if row['ArrTime_UTC'] >= row['DepTime_UTC']:
        return row['ArrTime_UTC'] - row['DepTime_UTC']
    else:
        return row['ArrTime_UTC'] + 1440 - row['DepTime_UTC']

df_schedule['Duration'] = df_schedule.apply(calculate_duration, axis=1)
df_schedule['Overnight'] = df_schedule.apply(
    lambda row: 1 if row['ArrTime_UTC'] < row['DepTime_UTC'] else 0, 
    axis=1
)

# 清理辅助列（可选，如果你想保留也可以注释掉这行）
df_schedule = df_schedule.drop(columns=['dep_min_local', 'arr_min_local', 'dep_offset_min', 'arr_offset_min'])

# ==========================================
# 任务 2：潜在需求的总量聚合
# ==========================================
print("开始执行任务 2：需求总量聚合...")

# 识别所有以 RD 开头的列并求和
rd_columns = [col for col in df_products.columns if col.startswith('RD')]
df_products['Total_Demand'] = df_products[rd_columns].sum(axis=1)

# 重命名并保留指定列
df_products = df_products.rename(columns={'Origin': 'Org', 'Destination': 'Des'})
columns_to_keep = ['Org', 'Des', 'Flight1', 'Flight2', 'Flight3', 'Fare', 'Total_Demand']
df_products = df_products[columns_to_keep]

# 重置索引并生成 ProductID
df_products = df_products.reset_index(drop=True)
df_products.insert(0, 'ProductID', 'P' + df_products.index.astype(str).str.zfill(6))

# ==========================================
# 任务 3：构建产品与航段的映射关系表 (⚠️已修复提取逻辑)
# ==========================================
print("开始执行任务 3：构建映射表并清理航班号后缀...")
df_melted = pd.melt(
    df_products, 
    id_vars=['ProductID'], 
    value_vars=['Flight1', 'Flight2', 'Flight3'], 
    value_name='Raw_FlightNo'
)

invalid_placeholders = ['.', '', ' ', None]
df_mapping = df_melted[~df_melted['Raw_FlightNo'].isin(invalid_placeholders)].copy()
df_mapping = df_mapping.dropna(subset=['Raw_FlightNo'])

# 核心修复：把 "AA0040BERBOD" 剥离成 "AA0040"
# 正则解释：提取行首的 2个大写字母 + 后面的任意数字。这能完美抓取正常的航班号。
df_mapping['FlightNo'] = df_mapping['Raw_FlightNo'].str.extract(r'^([A-Z]{2}\d+)')

# 保留需要的列
df_mapping = df_mapping[['ProductID', 'FlightNo']].sort_values('ProductID').reset_index(drop=True)

# ==========================================
# 任务 4：经停航班的“打包”标记
# ==========================================
print("开始执行任务 4：经停航班打包...")
flight_counts = df_schedule['flight'].value_counts()
multi_leg_flights = set(flight_counts[flight_counts > 1].index)
df_schedule['Super_Flight_ID'] = df_schedule['flight'].apply(
    lambda x: f"Super_{x}" if x in multi_leg_flights else x
)

# ==========================================
# 5. 导出数据（关键步骤！）
# ==========================================
print("\n正在将处理后的数据保存为新的 CSV 文件...")

# 写入硬盘，index=False 表示不保存行索引号
PROCESSED_SCHEDULE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
PROCESSED_PRODUCTS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
PRODUCT_LEG_MAPPING_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
df_schedule.to_csv(PROCESSED_SCHEDULE_OUTPUT, index=False, encoding='utf-8-sig')
df_products.to_csv(PROCESSED_PRODUCTS_OUTPUT, index=False, encoding='utf-8-sig')
df_mapping.to_csv(PRODUCT_LEG_MAPPING_OUTPUT, index=False, encoding='utf-8-sig')

print("\n🎉 数据清洗全部完成！输出文件如下：")
print(f"1. {PROCESSED_SCHEDULE_OUTPUT.relative_to(ROOT)}")
print(f"2. {PROCESSED_PRODUCTS_OUTPUT.relative_to(ROOT)}")
print(f"3. {PRODUCT_LEG_MAPPING_OUTPUT.relative_to(ROOT)}")

# 打印一下预览让你在控制台直接看到变化
print("\n--- df_schedule 预览 (前3行) ---")
print(df_schedule[['flight', 'DepTime_UTC', 'ArrTime_UTC', 'Duration', 'Overnight', 'Super_Flight_ID']].head(3))
