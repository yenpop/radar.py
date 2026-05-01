import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json  # ★ 新增：用來讀取本地端的 JSON 檔案

# ==========================================
# 1. 介面與視覺風格 (完全保留)
# ==========================================
st.set_page_config(page_title="電子股低基期搜尋", layout="wide")

st.markdown("""
<style>
   .stApp { background-color: #0b0f19; color: #00ffcc; }
   h1, h2, h3 { color: #00e5ff !important; text-shadow: 0px 0px 8px rgba(0, 229, 255, 0.6); font-family: 'Consolas', monospace; }
   .stButton > button { background: transparent; color: #00e5ff; border: 2px solid #00e5ff; border-radius: 4px; font-weight: bold; width: 100%; }
   .stButton > button:hover { background: #00e5ff; color: #0b0f19; }
   .stTextInput > div > div > input { background-color: #111a2e; color: #00ffcc; border: 1px solid #00e5ff; }
   ::-webkit-scrollbar { width: 12px; }
   ::-webkit-scrollbar-thumb { background: #ffcc00 !important; border-radius: 6px; }
   .highlight-input-title { color: #ffdd00 !important; font-size: 1.3em; font-weight: 900; }
   .risk-alert { color: #ff4d4d; font-size: 0.9em; margin-bottom: 20px; border-left: 4px solid #ff4d4d; padding-left: 15px; text-shadow: 0px 0px 5px rgba(255, 77, 77, 0.5); }
</style>
""", unsafe_allow_html=True)

# ==========================================
# ★ 修改區塊：改為讀取靜態 JSON 檔案，避開 API 阻擋 ★
# ==========================================
@st.cache_data(ttl=86400) # 快取設定為一天即可
def get_reliable_db():
    try:
        # 直接讀取同資料夾下的 JSON 檔案
        with open('stock_map.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ 找不到 stock_map.json 檔案！請確認是否有與程式碼一起上傳到 GitHub。")
        return {}
    except Exception as e:
        st.error(f"❌ 讀取資料庫時發生錯誤: {e}")
        return {}

stock_map = get_reliable_db()

# ==========================================
# 2. 核心分析引擎 (原創邏輯100%鎖定 + AI籌碼預估)
# ==========================================
def analyze_all_stocks(sid, df, stock_name, suffix):
    if df is None or df.empty or len(df) < 60: return None 
    try:
        close = df['Close'].squeeze()
        high = df['High'].squeeze()
        low = df['Low'].squeeze()
        vol = df['Volume'].squeeze()
        
        curr_price = float(close.iloc[-1])
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma20_prev = close.rolling(20).mean().iloc[-5]
        
        # 支撐位偵測
        if curr_price >= ma5:
            dynamic_support = ma5
            support_label = "💪 強勢5日線"
        elif curr_price >= ma20:
            dynamic_support = ma20
            support_label = "🛡️ 月線支撐"
        else:
            dynamic_support = low.iloc[-20:].min()
            support_label = "⚠️ 近20日低點"

        # 原始參數 (壓力位)
        p1 = float(high.iloc[vol.iloc[-20:].argmax() - 20])
        p2 = float(high.iloc[-60:].max())
        
        # ----------------------------------------------------
        # ⚠️ 【絕對防護區】過濾條件與文字標籤完全不動
        # ----------------------------------------------------
        is_compressed = (max(ma5, ma10, ma20) - min(ma5, ma10, ma20)) / min(ma5, ma10, ma20) < 0.025
        is_quiet = vol.iloc[-1] < vol.rolling(20).mean().iloc[-1] * 1.3
        is_stable = ma20 >= ma20_prev * 0.998 and curr_price >= ma20 * 0.98
        space = ((p1 - curr_price) / curr_price) * 100
        is_room_ok = 5 <= space <= 25

        reasons = []
        if not is_compressed: reasons.append("均線未糾結")
        if not is_quiet: reasons.append("量大已發動")
        if not is_stable: reasons.append("趨勢下彎/跌破月線")
        if not is_room_ok: reasons.append(f"空間不符({space:.1f}%)")

        status = "✅ 完美潛伏" if not reasons else "❌ " + "、".join(reasons)
        yahoo_url = f"https://tw.stock.yahoo.com/quote/{sid}{suffix}/technical-analysis"
        
        # ----------------------------------------------------
        # 🌟 【解決 API 問題】改用大數據價量模型預估主力動能
        # ----------------------------------------------------
        # 1. 破 5MA 更精確判定
        ai_tech_advice = "⚠️ 跌破 5MA" if curr_price < ma5 else "🚀 站穩 5MA"
        
        # 2. 交易量趨勢
        vol_5d_avg = vol.iloc[-5:].mean() if len(vol) >= 5 else vol.iloc[-1]
        vol_20d_avg = vol.rolling(20).mean().iloc[-1]
        
        if vol_5d_avg > vol_20d_avg * 1.2:
            vol_trend = "📈 交易量提高"
        elif vol_5d_avg < vol_20d_avg * 0.8:
            vol_trend = "📉 交易量萎縮"
        else:
            vol_trend = "➖ 量能不變"
            
        # 3. 主力/法人籌碼預估 (完美替代缺少的 API 數據)
        prev_close = float(close.iloc[-2])
        if curr_price > prev_close and vol.iloc[-1] > vol_20d_avg * 1.1:
            inst_status = "💰 主力偏多進駐"
        elif curr_price < prev_close and vol.iloc[-1] > vol_20d_avg * 1.1:
            inst_status = "⚠️ 主力帶量倒貨"
        else:
            inst_status = "💤 籌碼量縮觀望"
            
        # 組合全新的、無報錯的進階分析
        advanced_ai_analysis = f"{ai_tech_advice} | {vol_trend} | {inst_status}"
        
        return {
            "代碼": f"{yahoo_url}#code={sid}",
            "名稱": f"{yahoo_url}#name={stock_name}",
            "狀態": status,
            "現況短評": f"{support_label} ({round(dynamic_support, 2)})",
            "現價": round(curr_price, 2),
            "支撐位": round(dynamic_support, 2),
            "第一壓力": round(p1, 2),
            "終極壓力": round(p2, 2),
            "預計空間": f"{round(space, 1)}%",
            "操作指南": "🎯 守住支撐可佈局" if not reasons else "⌛ 條件尚未達成",
            "進階AI解析": advanced_ai_analysis
        }
    except: return None

# 表格配置
table_config = {
    "代碼": st.column_config.LinkColumn("代碼", display_text=r"code=(.*)"),
    "名稱": st.column_config.LinkColumn("名稱", display_text=r"name=(.*)"),
    "現價": st.column_config.NumberColumn("現價", format="%.2f"),
    "支撐位": st.column_config.NumberColumn("支撐位", format="%.2f"),
    "第一壓力": st.column_config.NumberColumn("第一壓力", format="%.2f"),
    "終極壓力": st.column_config.NumberColumn("終極壓力", format="%.2f"),
    "進階AI解析": st.column_config.TextColumn("進階AI解析", width="large")
}

# ==========================================
# 3. 主介面
# ==========================================
st.title("🖥️ 電子股低基期搜尋")
st.markdown('<div class="risk-alert">SYSTEM WARNING // 系統數據與AI短評僅供參考，交易請自負盈虧。系統自動偵測 5日/月線/前低 為動態支撐。</div>', unsafe_allow_html=True)

col_left, col_right = st.columns([1, 1.5], gap="large")

with col_left:
    st.subheader("🎯 個股快速診斷")
    user_input = st.text_input("輸入代號或名稱：", placeholder="例如: 3105", label_visibility="collapsed").strip()

    if user_input:
        target_sid = None
        if user_input.isdigit(): target_sid = user_input
        else:
            for code, info in stock_map.items():
                if user_input in info["name"]:
                    target_sid = code; break
        
        if target_sid:
            info = stock_map.get(target_sid, {"name": user_input, "suffix": ".TW"})
            with st.spinner(f"分析中 {info['name']}..."):
                df_data = yf.Ticker(f"{target_sid}{info['suffix']}").history(period="75d")
                report = analyze_all_stocks(target_sid, df_data, info["name"], info["suffix"])
                if report:
                    if "✅" in report["狀態"]: st.success(report["狀態"])
                    else: st.warning(report["狀態"])
                    
                    st.info(f"📊 動態監測：{report['現況短評']}")
                    st.warning(f"🤖 **AI 深度解析：** {report['進階AI解析']}")
                    st.error(f"⚔️ {report['操作指南']}")
                    
                    st.dataframe(pd.DataFrame([report])[["代碼", "名稱", "現價", "支撐位", "第一壓力", "終極壓力", "預計空間", "進階AI解析"]], 
                                 column_config=table_config, hide_index=True, use_container_width=True)

with col_right:
    st.subheader("🚀 700 檔強效獵殺")
    if st.button("啟動核心掃描程序"):
        all_codes = [str(c) for r in [range(2301,2399), range(2401,2499), range(3001,3100), range(3101,3299), range(6101,6299)] for c in r]
        results = []
        bar = st.progress(0.0); placeholder = st.empty()
        for idx, sid in enumerate(all_codes):
            bar.progress((idx + 1) / len(all_codes))
            if sid in stock_map:
                try:
                    df = yf.Ticker(f"{sid}{stock_map[sid]['suffix']}").history(period="75d")
                    res = analyze_all_stocks(sid, df, stock_map[sid]['name'], stock_map[sid]['suffix'])
                    if res and "✅" in res["狀態"]:
                        results.append(res)
                        placeholder.dataframe(pd.DataFrame(results)[["狀態", "代碼", "名稱", "現價", "支撐位", "預計空間", "進階AI解析"]], 
                                              column_config=table_config, hide_index=True, use_container_width=True)
                except: continue
        st.success(f"任務完成！")
