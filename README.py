import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from PIL import Image
from pyzbar.pyzbar import decode
import io

# ---------- 数据持久化 ----------
DATA_FILE = "warehouse_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("pn_data", {}), data.get("logs", [])
    return {}, []

def save_data(pn_data, logs):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"pn_data": pn_data, "logs": logs}, f, ensure_ascii=False, indent=2)

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

# ---------- 扫码辅助函数 ----------
def scan_barcode(image):
    """从 PIL Image 中解析出条码/二维码内容"""
    try:
        barcodes = decode(image)
        if barcodes:
            return barcodes[0].data.decode("utf-8")
    except Exception as e:
        st.error(f"扫码解析失败: {e}")
    return None

# ---------- 页面配置 ----------
st.set_page_config(page_title="仓库系统 Pro", page_icon="📦", layout="wide")
st.title("📦 仓库管理系统 Pro（扫码版）")

menu = st.sidebar.radio("导航", [
    "📋 库存总览",
    "🔍 库存查询",
    "➕ 添加物料",
    "📥 入库",
    "📤 出库",
    "📜 操作流水"
])

# ================== 添加物料 ==================
if menu == "➕ 添加物料":
    st.subheader("➕ 添加物料（PN 下新增 ID）")
    col1, col2 = st.columns(2)
    pn_input = col1.text_input("物料 PN（型号）*")
    sn_input = col2.text_input("物料 ID（实物唯一标识）*")

    col3, col4, col5 = st.columns(3)
    init_stock = col3.number_input("初始库存", min_value=0, value=0)
    min_stock = col4.number_input("最低库存预警", min_value=0, value=1)
    price = col5.number_input("参考单价", min_value=0.0, value=0.0, step=0.5)
    frozen = st.selectbox("冻结状态", ["正常", "冻结"])

    if st.button("✅ 确认添加"):
        if not pn_input or not sn_input:
            st.error("PN 和 ID 均不能为空！")
        else:
            id_exists = False
            for pn, data in st.session_state.pn_data.items():
                if sn_input in data["ids"]:
                    id_exists = True
                    break
            if id_exists:
                st.error(f"ID {sn_input} 已存在！")
            else:
                if pn_input not in st.session_state.pn_data:
                    st.session_state.pn_data[pn_input] = {"ids": {}}
                st.session_state.pn_data[pn_input]["ids"][sn_input] = {
                    "stock": init_stock,
                    "min_stock": min_stock,
                    "price": price,
                    "frozen": frozen
                }
                add_log("新增物料", pn_input, sn_input, init_stock, init_stock)
                save_data(st.session_state.pn_data, st.session_state.logs)
                st.success(f"成功添加 {pn_input} / {sn_input}")

# ================== 入库（带扫码） ==================
elif menu == "📥 入库":
    st.subheader("📥 入库（扫码或手动选择）")
    if not st.session_state.pn_data:
        st.info("暂无物料，请先添加")
    else:
        # 扫码区域
        with st.expander("📷 扫码识别物料（点击打开）"):
            camera_image = st.camera_input("拍摄条码/二维码")
            scanned_text = None
            if camera_image is not None:
                img = Image.open(camera_image)
                scanned_text = scan_barcode(img)
                if scanned_text:
                    st.success(f"扫描结果：{scanned_text}")
                else:
                    st.warning("未识别到条码/二维码，请重试")

        # 正常手动选择
        pn_list = list(st.session_state.pn_data.keys())
        selected_pn = st.selectbox("选择 PN", pn_list, key="in_pn")

        id_dict = st.session_state.pn_data[selected_pn]["ids"]
        if not id_dict:
            st.warning(f"PN {selected_pn} 下暂无 ID")
        else:
            id_list = list(id_dict.keys())
            # 如果扫到了码，且码内容在 id_list 中，则自动选中
            default_id = 0
            if scanned_text and scanned_text in id_list:
                default_id = id_list.index(scanned_text)
                st.info(f"已自动定位到扫描物料：{scanned_text}")
            selected_id = st.selectbox("选择 ID", id_list, index=default_id, key="in_id")

            qty = st.number_input("入库数量", min_value=1, value=1)
            if st.button("📥 确认入库"):
                id_info = id_dict[selected_id]
                id_info["stock"] += qty
                add_log("入库", selected_pn, selected_id, qty, id_info["stock"])
                st.success(f"入库成功！{selected_pn}/{selected_id} 当前库存：{id_info['stock']}")

# ================== 出库（带扫码） ==================
elif menu == "📤 出库":
    st.subheader("📤 出库（扫码或手动选择）")
    if not st.session_state.pn_data:
        st.info("暂无物料")
    else:
        with st.expander("📷 扫码识别物料"):
            camera_image = st.camera_input("拍摄条码/二维码", key="out_camera")
            scanned_text = None
            if camera_image is not None:
                img = Image.open(camera_image)
                scanned_text = scan_barcode(img)
                if scanned_text:
                    st.success(f"扫描结果：{scanned_text}")
                else:
                    st.warning("未识别到条码")

        pn_list = list(st.session_state.pn_data.keys())
        selected_pn = st.selectbox("选择 PN", pn_list, key="out_pn")
        id_dict = st.session_state.pn_data[selected_pn]["ids"]
        if not id_dict:
            st.warning(f"PN {selected_pn} 下暂无 ID")
        else:
            id_list = list(id_dict.keys())
            default_id = 0
            if scanned_text and scanned_text in id_list:
                default_id = id_list.index(scanned_text)
                st.info(f"已定位到扫描物料：{scanned_text}")
            selected_id = st.selectbox("选择 ID", id_list, index=default_id, key="out_id")

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
                        st.warning(f"⚠️ {selected_id} 库存低于安全线！")

# ================== 库存总览 ==================
elif menu == "📋 库存总览":
    st.subheader("📋 全部库存（按 PN 分组）")
    if not st.session_state.pn_data:
        st.info("暂无物料")
    else:
        for pn, data in st.session_state.pn_data.items():
            with st.expander(f"📌 PN：{pn}（{len(data['ids'])} 个 ID）"):
                if not data["ids"]:
                    st.caption("暂无 ID")
                else:
                    rows = []
                    for sn, info in data["ids"].items():
                        rows.append([
                            sn, info["stock"], info["min_stock"],
                            info["price"], info["frozen"],
                            "⚠️" if info["stock"] < info["min_stock"] else "✅"
                        ])
                    df = pd.DataFrame(rows, columns=["ID", "库存", "最低预警", "单价", "冻结", "状态"])
                    st.dataframe(df, use_container_width=True, hide_index=True)

# ================== 库存查询（带扫码） ==================
elif menu == "🔍 库存查询":
    st.subheader("🔍 查询（扫码或手动输入）")
    if not st.session_state.pn_data:
        st.info("暂无物料")
    else:
        # 扫码查询 ID
        with st.expander("📷 扫码查询（扫描物料 ID）"):
            cam = st.camera_input("扫描条码/二维码", key="search_cam")
            scanned = None
            if cam is not None:
                img = Image.open(cam)
                scanned = scan_barcode(img)
                if scanned:
                    st.success(f"扫描结果：{scanned}")
                else:
                    st.warning("未识别")

        search_mode = st.radio("查询方式", ["按 PN 查看所有 ID", "按 ID 精确查询"])
        if search_mode == "按 PN 查看所有 ID":
            search_pn = st.text_input("输入 PN")
            if search_pn:
                if search_pn in st.session_state.pn_data:
                    data = st.session_state.pn_data[search_pn]
                    st.success(f"找到 PN：{search_pn}，共 {len(data['ids'])} 个 ID")
                    rows = [[sn, info["stock"], info["min_stock"], info["price"], info["frozen"]] 
                            for sn, info in data["ids"].items()]
                    df = pd.DataFrame(rows, columns=["ID", "库存", "最低预警", "单价", "冻结"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.error("该 PN 不存在")
        else:
            # 如果扫到了码，直接填入输入框
            search_id = st.text_input("输入 ID", value=scanned if scanned else "")
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

# ================== 操作流水 ==================
elif menu == "📜 操作流水":
    st.subheader("📜 最近操作记录")
    if not st.session_state.logs:
        st.info("暂无记录")
    else:
        df_log = pd.DataFrame(st.session_state.logs)
        cols = ["time", "type", "PN", "ID", "qty", "balance"]
        df_log = df_log[cols]
        st.dataframe(df_log.tail(30), use_container_width=True, hide_index=True)
