# warehouse-system
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# 数据文件
DATA_FILE = "warehouse_data.json"

# 加载数据
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("pn_data", {}), data.get("logs", [])
    return {}, []

# 保存数据
def save_data(pn_data, logs):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"pn_data": pn_data, "logs": logs}, f, ensure_ascii=False, indent=2)

# 初始化 session_state
if "pn_data" not in st.session_state:
    pn_data, logs = load_data()
    st.session_state.pn_data = pn_data
    st.session_state.logs = logs

def add_log(typ, pn, sn, qty, balance):
    st.session_state.logs.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": typ,
        "PN": pn,
        "ID": sn,
        "qty": qty,
        "balance": balance
    })
    save_data(st.session_state.pn_data, st.session_state.logs)

# 页面配置
st.set_page_config(page_title="仓库系统 Pro", page_icon="📦", layout="wide")
st.title("📦 仓库管理系统 Pro（PN + ID）")

menu = st.sidebar.radio("导航", [
    "📋 库存总览",
    "🔍 库存查询",
    "➕ 添加物料",
    "📥 入库",
    "📤 出库",
    "📜 操作流水"
])

# ==================== 添加物料 ====================
if menu == "➕ 添加物料":
    st.subheader("➕ 添加物料（PN 下新增 ID）")
    col1, col2 = st.columns(2)
    pn_input = col1.text_input("物料 PN（型号）*", key="new_pn")
    sn_input = col2.text_input("物料 ID（实物唯一标识）*", key="new_sn")

    col3, col4, col5 = st.columns(3)
    init_stock = col3.number_input("初始库存", min_value=0, value=0)
    min_stock = col4.number_input("最低库存预警", min_value=0, value=1)
    price = col5.number_input("参考单价", min_value=0.0, value=0.0, step=0.5)

    frozen = st.selectbox("冻结状态", ["正常", "冻结"])

    if st.button("✅ 确认添加"):
        if not pn_input or not sn_input:
            st.error("PN 和 ID 均不能为空！")
        else:
            # 检查 ID 是否在整个系统中已存在
            id_exists = False
            for pn, data in st.session_state.pn_data.items():
                if sn_input in data["ids"]:
                    id_exists = True
                    break
            if id_exists:
                st.error(f"ID {sn_input} 已存在，请更换！")
            else:
                # PN 不存在则自动创建
                if pn_input not in st.session_state.pn_data:
                    st.session_state.pn_data[pn_input] = {"ids": {}}
                    st.info(f"自动创建新 PN：{pn_input}")
                # 添加 ID
                st.session_state.pn_data[pn_input]["ids"][sn_input] = {
                    "stock": init_stock,
                    "min_stock": min_stock,
                    "price": price,
                    "frozen": frozen
                }
                add_log("新增物料", pn_input, sn_input, init_stock, init_stock)
                save_data(st.session_state.pn_data, st.session_state.logs)
                st.success(f"成功添加 {pn_input} / {sn_input}")

# ==================== 入库 ====================
elif menu == "📥 入库":
    st.subheader("📥 入库（选择 PN → ID）")
    if not st.session_state.pn_data:
        st.info("暂无任何物料，请先添加")
    else:
        pn_list = list(st.session_state.pn_data.keys())
        selected_pn = st.selectbox("选择 PN", pn_list)

        # 根据选中的 PN 列出该 PN 下的所有 ID
        id_dict = st.session_state.pn_data[selected_pn]["ids"]
        if not id_dict:
            st.warning(f"PN {selected_pn} 下还没有 ID，请先去添加物料")
        else:
            id_list = list(id_dict.keys())
            selected_id = st.selectbox("选择 ID", id_list)
            qty = st.number_input("入库数量", min_value=1, value=1)
            if st.button("📥 确认入库"):
                id_info = id_dict[selected_id]
                id_info["stock"] += qty
                add_log("入库", selected_pn, selected_id, qty, id_info["stock"])
                st.success(f"入库成功！{selected_pn}/{selected_id} 当前库存：{id_info['stock']}")

# ==================== 出库 ====================
elif menu == "📤 出库":
    st.subheader("📤 出库（选择 PN → ID）")
    if not st.session_state.pn_data:
        st.info("暂无物料")
    else:
        pn_list = list(st.session_state.pn_data.keys())
        selected_pn = st.selectbox("选择 PN", pn_list)
        id_dict = st.session_state.pn_data[selected_pn]["ids"]
        if not id_dict:
            st.warning(f"PN {selected_pn} 下没有 ID")
        else:
            # 显示 ID 列表，同时展示库存和冻结状态
            id_display = [f"{sn} (库存:{info['stock']}, 状态:{info['frozen']})" for sn, info in id_dict.items()]
            selected_id_display = st.selectbox("选择 ID", id_display)
            selected_id = selected_id_display.split(" ")[0]  # 提取实际 ID

            id_info = id_dict[selected_id]
            qty = st.number_input("出库数量", min_value=1, value=1)
            if st.button("📤 确认出库"):
                if id_info["frozen"] == "冻结":
                    st.error(f"{selected_pn}/{selected_id} 已被冻结，无法出库！")
                elif qty > id_info["stock"]:
                    st.error(f"库存不足！当前库存：{id_info['stock']}")
                else:
                    id_info["stock"] -= qty
                    add_log("出库", selected_pn, selected_id, qty, id_info["stock"])
                    st.success(f"出库成功！{selected_pn}/{selected_id} 当前库存：{id_info['stock']}")
                    if id_info["stock"] < id_info["min_stock"]:
                        st.warning(f"⚠️ {selected_id} 库存低于安全线 ({id_info['min_stock']})！")

# ==================== 库存总览 ====================
elif menu == "📋 库存总览":
    st.subheader("📋 全部库存（按 PN 分组）")
    if not st.session_state.pn_data:
        st.info("暂无物料")
    else:
        for pn, data in st.session_state.pn_data.items():
            with st.expander(f"📌 PN：{pn}  （共 {len(data['ids'])} 个 ID）"):
                if not data["ids"]:
                    st.caption("暂无 ID")
                else:
                    rows = []
                    for sn, info in data["ids"].items():
                        rows.append([
                            sn,
                            info["stock"],
                            info["min_stock"],
                            info["price"],
                            info["frozen"],
                            "⚠️" if info["stock"] < info["min_stock"] else "✅"
                        ])
                    df = pd.DataFrame(rows, columns=["ID", "库存", "最低预警", "单价", "冻结", "状态"])
                    st.dataframe(df, use_container_width=True, hide_index=True)

# ==================== 库存查询 ====================
elif menu == "🔍 库存查询":
    st.subheader("🔍 查询（支持按 PN 或按 ID）")
    if not st.session_state.pn_data:
        st.info("暂无物料")
    else:
        search_mode = st.radio("查询方式", ["按 PN 查看所有 ID", "按 ID 精确查询"])
        if search_mode == "按 PN 查看所有 ID":
            search_pn = st.text_input("输入 PN（型号）")
            if search_pn:
                if search_pn in st.session_state.pn_data:
                    data = st.session_state.pn_data[search_pn]
                    st.success(f"找到 PN：{search_pn}，共 {len(data['ids'])} 个 ID")
                    rows = []
                    for sn, info in data["ids"].items():
                        rows.append([sn, info["stock"], info["min_stock"], info["price"], info["frozen"]])
                    df = pd.DataFrame(rows, columns=["ID", "库存", "最低预警", "单价", "冻结"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.error("该 PN 不存在")
        else:  # 按 ID 精确查询
            search_id = st.text_input("输入 ID（实物唯一标识）")
            if search_id:
                found = False
                for pn, data in st.session_state.pn_data.items():
                    if search_id in data["ids"]:
                        info = data["ids"][search_id]
                        st.success(f"找到物料：{pn} / {search_id}")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("所属 PN", pn)
                        col2.metric("当前库存", info["stock"])
                        col3.metric("冻结状态", info["frozen"])
                        col1.metric("最低预警", info["min_stock"])
                        col2.metric("参考单价", f"{info['price']:.2f}")
                        if info["stock"] < info["min_stock"]:
                            st.warning("⚠️ 库存低于安全线")
                        found = True
                        break
                if not found:
                    st.error(f"未找到 ID 为 {search_id} 的物料")

# ==================== 操作流水 ====================
elif menu == "📜 操作流水":
    st.subheader("📜 最近操作记录")
    if not st.session_state.logs:
        st.info("暂无记录")
    else:
        df_log = pd.DataFrame(st.session_state.logs)
        # 调整列顺序，让时间在最前
        cols = ["time", "type", "PN", "ID", "qty", "balance"]
        df_log = df_log[cols]
        st.dataframe(df_log.tail(30), use_container_width=True, hide_index=True)
