import json
import math
from pathlib import Path
from pyvis.network import Network

ROOT = Path(__file__).resolve().parents[2]
AIRPORT_TIMELINE_INPUT = ROOT / "data" / "model_input" / "network" / "airport_timeline.json"
NETWORK_OUTPUT = ROOT / "results" / "network" / "airport_timeline_network_v3.html"

# 1. 读取 JSON 数据
with open(AIRPORT_TIMELINE_INPUT, 'r', encoding='utf-8') as f:
    airport_data = json.load(f)

# 【改进1】bgcolor 改为白色，font_color 改为黑色
net = Network(height="800px", width="100%", bgcolor="white", font_color="black", directed=True)

# 【改进4】大幅降低 spring_strength (0.01)，增加 damping (0.15)，减弱连线弹性拉扯感
net.repulsion(node_distance=350, central_gravity=0.1, spring_length=350, spring_strength=0.01, damping=0.15)

# 3. 提取航班轨迹与机场吞吐量
airport_events = {}
flight_paths = {}

for airport, events in airport_data.items():
    # 按时间对当前机场的事件进行排序
    sorted_events = sorted(events, key=lambda x: x['time'])
    airport_events[airport] = sorted_events
    
    # 记录航班的全局轨迹以生成连线
    for event in sorted_events:
        flight_id = event['flight_id']
        if flight_id not in flight_paths:
            flight_paths[flight_id] = []
        flight_paths[flight_id].append({
            'airport': airport,
            'time': event['time'],
            'type': event['type']
        })

# 4. 生成节点 (Nodes) 与悬停信息 (Tooltip)
for airport, events in airport_events.items():
    event_count = len(events)
    
    tooltip_text = f"🛫 机场: {airport} | 全天事件总数: {event_count}\n"
    tooltip_text += "=" * 40 + "\n"
    for evt in events:
        time_str = str(evt['time']).rjust(4)
        type_str = evt['type'].ljust(6)
        tooltip_text += f"[{time_str} 分钟] {type_str} - 航班: {evt['flight_id']}\n"
    
    # 【改进3】将基础尺寸调小至 5 (原来是 15)，进一步拉开大小机场的对比度
    node_size = 5 + math.sqrt(event_count) * 5 
    
    net.add_node(
        airport, 
        label=airport, 
        title=tooltip_text,
        size=node_size,
        color="#0078D7", # 白底上用微软蓝/深蓝色更醒目
        # 【改进2】明确增大字号为 24，并添加白色文字描边防止被连线遮挡
        font={"size": 24, "face": "Arial", "strokeWidth": 3, "strokeColor": "white"}
    )

# 5. 生成连线 (Edges)
edges_added = set()

for flight_id, path in flight_paths.items():
    # 对该航班的所有事件按时间全局排序
    path.sort(key=lambda x: x['time'])
    
    prev_airport = None
    for step in path:
        curr_airport = step['airport']
        if prev_airport and prev_airport != curr_airport:
            edge_tuple = (prev_airport, curr_airport)
            if edge_tuple not in edges_added:
                # 白底上的连线改用浅灰色，避免抢走节点的视觉焦点
                net.add_edge(prev_airport, curr_airport, color="#b0b0b0", width=1.5)
                edges_added.add(edge_tuple)
        prev_airport = curr_airport

# 6. 生成物理交互控制面板并输出 HTML
output_file = NETWORK_OUTPUT
output_file.parent.mkdir(parents=True, exist_ok=True)
net.write_html(output_file)

html_text = output_file.read_text(encoding="utf-8")
html_text = html_text.replace("lib/bindings/utils.js", "assets/bindings/utils.js")
output_file.write_text(html_text, encoding="utf-8")

print(f"✅ 可视化文件已更新：请在浏览器中打开 {output_file}")
