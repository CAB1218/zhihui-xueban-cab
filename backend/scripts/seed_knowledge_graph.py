"""
Neo4j 知识图谱种子数据脚本
为 智慧学伴 平台写入数学和物理的示例知识节点与关系
"""
import sys
import os

# 添加 backend 到路径以便导入服务
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.graph_service import graph_service


# 数学知识节点
MATH_NODES = [
    {
        "id": "math_function_basic",
        "name": "函数基础",
        "subject": "数学",
        "description": "函数的概念、定义域、值域、图像等基本知识",
        "cognitive_level": {"记忆": 0.8, "理解": 0.7, "应用": 0.5, "分析": 0.3, "评价": 0.2, "创造": 0.1},
    },
    {
        "id": "math_quadratic_function",
        "name": "二次函数",
        "subject": "数学",
        "description": "二次函数的图像、性质、解析式求解及应用",
        "cognitive_level": {"记忆": 0.6, "理解": 0.8, "应用": 0.9, "分析": 0.6, "评价": 0.3, "创造": 0.2},
    },
    {
        "id": "math_triangle_function",
        "name": "三角函数",
        "subject": "数学",
        "description": "正弦、余弦、正切函数的定义、图像与性质",
        "cognitive_level": {"记忆": 0.5, "理解": 0.7, "应用": 0.8, "分析": 0.6, "评价": 0.3, "创造": 0.2},
    },
    {
        "id": "math_derivative",
        "name": "导数",
        "subject": "数学",
        "description": "导数的概念、计算法则、几何意义及实际应用",
        "cognitive_level": {"记忆": 0.4, "理解": 0.7, "应用": 0.9, "分析": 0.8, "评价": 0.4, "创造": 0.3},
    },
    {
        "id": "math_integral",
        "name": "积分",
        "subject": "数学",
        "description": "不定积分、定积分的概念、计算及应用",
        "cognitive_level": {"记忆": 0.3, "理解": 0.6, "应用": 0.9, "分析": 0.8, "评价": 0.4, "创造": 0.3},
    },
    {
        "id": "math_limit",
        "name": "极限",
        "subject": "数学",
        "description": "极限的定义、运算法则及在导数中的应用",
        "cognitive_level": {"记忆": 0.5, "理解": 0.8, "应用": 0.6, "分析": 0.7, "评价": 0.3, "创造": 0.2},
    },
]

# 物理知识节点
PHYSICS_NODES = [
    {
        "id": "physics_newton_law",
        "name": "牛顿运动定律",
        "subject": "物理",
        "description": "牛顿第一、二、三定律的内容、表达式及应用",
        "cognitive_level": {"记忆": 0.7, "理解": 0.8, "应用": 0.9, "分析": 0.7, "评价": 0.4, "创造": 0.2},
    },
    {
        "id": "physics_energy",
        "name": "能量守恒",
        "subject": "物理",
        "description": "动能、势能、机械能守恒定律及应用",
        "cognitive_level": {"记忆": 0.6, "理解": 0.8, "应用": 0.9, "分析": 0.7, "评价": 0.4, "创造": 0.3},
    },
    {
        "id": "physics_electric_field",
        "name": "电场",
        "subject": "物理",
        "description": "电场强度、电势、电容的基本概念及计算",
        "cognitive_level": {"记忆": 0.5, "理解": 0.7, "应用": 0.8, "分析": 0.7, "评价": 0.3, "创造": 0.2},
    },
    {
        "id": "physics_magnetic_field",
        "name": "磁场",
        "subject": "物理",
        "description": "磁感应强度、安培力、洛伦兹力及电磁感应",
        "cognitive_level": {"记忆": 0.4, "理解": 0.7, "应用": 0.8, "分析": 0.7, "评价": 0.3, "创造": 0.2},
    },
    {
        "id": "physics_circuit",
        "name": "电路分析",
        "subject": "物理",
        "description": "欧姆定律、串并联电路、基尔霍夫定律",
        "cognitive_level": {"记忆": 0.6, "理解": 0.8, "应用": 0.9, "分析": 0.8, "评价": 0.4, "创造": 0.2},
    },
]

# 节点间关系（双向创建）
RELATIONSHIPS = [
    # 数学内部关系
    ("math_limit", "math_derivative", "PREREQUISITE", "前置知识"),
    ("math_derivative", "math_integral", "PREREQUISITE", "前置知识"),
    ("math_function_basic", "math_quadratic_function", "RELATED", "相关概念"),
    ("math_function_basic", "math_triangle_function", "RELATED", "相关概念"),
    ("math_quadratic_function", "math_derivative", "RELATED", "应用实例"),
    ("math_triangle_function", "math_derivative", "RELATED", "求导对象"),
    # 物理内部关系
    ("physics_newton_law", "physics_energy", "RELATED", "理论基础"),
    ("physics_electric_field", "physics_circuit", "RELATED", "电路中的电场"),
    ("physics_magnetic_field", "physics_electric_field", "RELATED", "电磁统一"),
    ("physics_circuit", "physics_energy", "RELATED", "电能转换"),
    # 跨学科关系
    ("math_derivative", "physics_newton_law", "APPLICATION", "运动学应用"),
    ("math_integral", "physics_energy", "APPLICATION", "做功与能量计算"),
    ("math_function_basic", "physics_circuit", "APPLICATION", "I-V 特性曲线"),
]


async def seed():
    print("=== 开始写入知识图谱种子数据 ===")

    # 创建数学节点
    print("\n-- 创建数学节点 --")
    for node in MATH_NODES:
        try:
            result = await graph_service.create_node(node)
            print(f"  ✓ {node['name']} ({node['id']})")
        except Exception as e:
            print(f"  ✗ {node['name']}: {e}")

    # 创建物理节点
    print("\n-- 创建物理节点 --")
    for node in PHYSICS_NODES:
        try:
            result = await graph_service.create_node(node)
            print(f"  ✓ {node['name']} ({node['id']})")
        except Exception as e:
            print(f"  ✗ {node['name']}: {e}")

    # 创建关系
    print("\n-- 创建节点关系 --")
    for from_id, to_id, rel_type, label in RELATIONSHIPS:
        try:
            result = await graph_service.create_relationship(
                from_id, to_id, rel_type, label
            )
            print(f"  ✓ {from_id} --[{label}]--> {to_id}")
        except Exception as e:
            print(f"  ✗ {from_id} --[{label}]--> {to_id}: {e}")

    # 验证写入结果
    print("\n-- 验证写入结果 --")
    stats = await graph_service.get_square_stats()
    total = sum(s.get("node_count", 0) for s in stats)
    print(f"  总节点数: {total}")
    for s in stats:
        if s.get("node_count", 0) > 0:
            print(f"  {s['name']}: {s['node_count']} 个节点")

    print("\n=== 种子数据写入完成 ===")


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed())
