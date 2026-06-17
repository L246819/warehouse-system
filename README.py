# warehouse-system
warehouse_app.py
import streamlit as st
import pandas as pd
from datetime import datetime

if "products" not in st.session_state:
    st.session_state.products = {}
if "logs" not in st.session_state:
    st.session_state.logs = []

def add_log(typ, pid, qty, balance):
    st.session_state.logs.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": typ,
        "pid": pid,
        "qty": qty,
        "balance": balance
    })

st.set_page_config(page_title="迷你仓库系统", page_icon="📦", layout="wide")
st.title("📦 迷你仓库管理系统")

menu = st.sidebar.radio("菜单", ["📋 库存总览", "➕ 添加商品", "📥 入库", "📤 出库", "📜 操作流水"])

if menu == "➕ 添加商品":
    st.subheader("添加新商品")
    with st.form("add_form"):
        pid = st.text_input("商品编号")
        name = st.text_input("商品名称")
        col1, col2 = st.columns(2)
        min_stock = col1.number_input("最低库存预警", min_value=0, value=10)
        price = col2.number_input("参考单价", min_value=0.0, value=0.0, step=0.5)
        if st.form_submit_button("✅ 确认添加"):
            if not pid or not name:
                st.error("编号和名称不能为空")
            else:
                if pid in st.session_state.products:
                    st.session_state.products[pid]["name"] = name
                    st.session_state.products[pid]["min_stock"] = min_stock
                    st.session_state.products[pid]["price"] = price
                    st.warning(f"商品 {pid} 已存在，已更新信息")
                else:
                    st.session_state.products[pid] = {"name": name, "stock": 0, "min_stock": min_stock, "price": price}
                st.success(f"商品 {name} 已保存")

elif menu == "📥 入库":
    st.subheader("商品入库")
    if not st.session_state.products:
        st.info("请先添加商品")
    else:
        pid = st.selectbox("选择商品", list(st.session_state.products.keys()),
                           format_func=lambda x: f"{x} - {st.session_state.products[x]['name']}")
        qty = st.number_input("入库数量", min_value=1, value=1)
        if st.button("📥 确认入库"):
            st.session_state.products[pid]["stock"] += qty
            add_log("入库", pid, qty, st.session_state.products[pid]["stock"])
            st.success(f"入库成功！{st.session_state.products[pid]['name']} 当前库存：{st.session_state.products[pid]['stock']}")

elif menu == "📤 出库":
    st.subheader("商品出库")
    if not st.session_state.products:
        st.info("请先添加商品")
    else:
        pid = st.selectbox("选择商品", list(st.session_state.products.keys()),
                           format_func=lambda x: f"{x} - {st.session_state.products[x]['name']} (库存:{st.session_state.products[x]['stock']})")
        qty = st.number_input("出库数量", min_value=1, value=1)
        if st.button("📤 确认出库"):
            if qty > st.session_state.products[pid]["stock"]:
                st.error(f"库存不足！当前库存：{st.session_state.products[pid]['stock']}")
            else:
                st.session_state.products[pid]["stock"] -= qty
                add_log("出库", pid, qty, st.session_state.products[pid]["stock"])
                st.success(f"出库成功！{st.session_state.products[pid]['name']} 当前库存：{st.session_state.products[pid]['stock']}")
                if st.session_state.products[pid]["stock"] < st.session_state.products[pid]["min_stock"]:
                    st.warning(f"⚠️ {st.session_state.products[pid]['name']} 库存低于安全线！")

elif menu == "📋 库存总览":
    st.subheader("当前库存")
    if not st.session_state.products:
        st.info("暂无商品")
    else:
        data = []
        for pid, info in st.session_state.products.items():
            warn = "⚠️" if info["stock"] < info["min_stock"] else ""
            data.append([pid, info["name"], info["stock"], info["min_stock"], info["price"], warn])
        df = pd.DataFrame(data, columns=["编号", "名称", "库存", "最低预警", "单价", "状态"])
        st.dataframe(df, use_container_width=True, hide_index=True)

elif menu == "📜 操作流水":
    st.subheader("最近操作记录")
    if not st.session_state.logs:
        st.info("暂无记录")
    else:
        df_log = pd.DataFrame(st.session_state.logs)
        st.dataframe(df_log.tail(20), use_container_width=True, hide_index=True)
