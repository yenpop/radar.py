import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time

# ==========================================
# 1. 介面與資料庫設定 (強制高亮黃色滑動條 CSS)
# ==========================================
st.set_page_config(page_title="電子股低基期搜尋", layout="wide")

# --- 科技風 (Cyberpunk) UI CSS 注入 ---
st.markdown("""
<style>
    .stApp {
        background-color: #0b0f19;
        color: #00ffcc;
    }
    h1, h2, h3 {
        color: #00e5ff !important;
        text-shadow: 0px 0px 8px rgba(0, 229, 255, 0.6);
        font-family: 'Consolas', 'Courier New', monospace;
        letter-spacing: 1px;
    }
    .stButton > button {
        background: transparent;
        color: #00e5ff;
        border: 2px solid #00e5ff;
        border-radius: 4px;
        box-shadow: 0 0 8px rgba(0,229,255,0.4) inset, 0 0 8px rgba(0,229,255,0.4);
        transition: all 0.3s ease;
        font-weight: bold;
        letter-spacing: 2px;
    }
    .stButton > button:hover {
        background: #00e5ff;
        color: #0b0f19;
        box-shadow: 0 0 15px rgba(0,229,255,0.8) inset, 0 0 15px rgba(0,229,255,0.8);
    }
    .stTextInput > div > div > input {
        background-color: #111a2e;
        color: #00ffcc;
        border: 1px solid #00e5ff;
        border-radius: 4px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #ffdd00 !important;
        box-shadow: 0 0 10px rgba(255, 221, 0, 0.6) !important;
    }
    .stAlert {
        background-color: #111a2e !important;
        border-left: 4px solid #00e5ff !important;
        color: #e0e6ed !important;
    }
    hr {
        border-color: #00e5ff;
        opacity: 0.3;
    }
    .risk-alert {
        color: #ff4d4d; 
        font-size: 0.9em;
        font-family: 'Consolas', monospace;
        margin-top: -10px;
        margin-bottom: 20px;
        text-shadow: 0px 0px 5px rgba(255, 77, 77, 0.5);
    }
    .highlight-input-title {
        color: #ffdd00 !important; 
        font-size: 1.3em;
        font-weight: 900;
        text-shadow: 0px 0px 12px rgba(255, 221, 0, 0.9);
        margin-bottom: 8px;
        margin-top: 10px;
        letter-spacing: 1px;
        display: block;
    }
    /* 【重點修改】純黃色顯眼滑動條，確保在任何螢幕都清楚可見 */
    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }
    ::-webkit-scrollbar-track {
        background: #111a2e;
        border-radius: 6px;
    }
    ::-webkit-scrollbar-thumb {
        background: #ffcc00 !important; /* 強制改為純粹的亮黃色 */
        border-radius: 6px;
        border: 2px solid #111a2e;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #ffea00 !important; /* 滑鼠移過去變得更亮 */
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_reliable_db():
    db = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        twse_url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        twse_res = requests.get(twse_url, headers=headers, timeout=5).json()
        for item in twse_res:
            code = str(item.get("Code", "")).strip()
            if code.isdigit() and len(code) == 4:
                db[code] = {"name": str(item.get("Name", "")).strip(), "suffix": ".TW"}
    except: pass
        
    try:
        tpex_url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
        tpex_res = requests.get(tpex_url, headers=headers, timeout=5).json()
        for item in tpex_res:
            code = str(item.get("SecuritiesCompanyCode", "")).strip()
            if code.isdigit() and len(code) == 4:
                db[code] = {"name": str(item.get("CompanyName", "")).strip(), "suffix": ".TWO"}
    except: pass

    if not db:
        try:
            url = "https://raw.githubusercontent.com/Asunny1701/TaiwanStockList/master/stock_list.csv"
            df = pd.read_csv(url)
            for _, row in df.iterrows():
                code = str(row['stock_id']).strip()
                name = str(row['stock_name']).strip()
                if code.isdigit() and len(code) == 4:
                    suffix = ".TW" if int(code) < 4000 or int(code) >= 9000 else ".TWO"
                    db[code] = {"name": name, "suffix": suffix}
        except: pass

    if not db:
        db = {"2330": {"name": "台積電", "suffix": ".TW"}, "4951": {"name": "精測", "suffix": ".TWO"}, "1597": {"name": "直得", "suffix": ".TW"}}
        
    return db

stock_map = get_reliable_db()

# ==========================================
# 2. 核心邏輯：全紀錄診斷引擎 (條件 100% 不變)
# ==========================================
def analyze_all_stocks(sid, df, stock_name):
    if df is None or df.empty or len(df) < 60:
        return None 
    
    try:
        close = df['Close'].squeeze()
        high = df['High'].squeeze()
        vol = df['Volume'].squeeze()
        
        curr_price = float(close.iloc[-1])
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma20_prev = close.rolling(20).mean().iloc[-5]
        
        p1 = float(high.iloc[vol.iloc[-20:].argmax() - 20])
        p2 = float(high.iloc[-60:].max())
        
        is_compressed = (max(ma5, ma10, ma20) - min(ma5, ma10, ma20)) / min(ma5, ma10, ma20) < 0.025
        is_quiet = vol.iloc[-1] < vol.rolling(20).mean().iloc[-1] * 1.3
        is_stable = ma20 >= ma20_prev * 0.998 and curr_price >= ma20 * 0.98
        space = ((p1 - curr_price) / curr_price) * 100
        is_room_ok = 5 <= space <= 25

        reasons = []
        if not is_compressed: reasons.append("均線未糾結")
        if not is_quiet: reasons.append("量大已發動")
        if not is_stable: reasons.append("趨勢下彎/跌破支撐")
        if not is_room_ok: reasons.append(f"空間不符({space:.1f}%)")

        status = "✅ 完美潛伏" if not reasons else "❌ " + "、".join(reasons)

        commentary = []
        if curr_price > p1:
            commentary.append("🔥 已突破近期大量高點(轉強)")
        elif curr_price < ma20:
            commentary.append("⚠️ 跌破月線支撐(偏弱)")
        else:
            commentary.append("➖ 月線上震盪")
            
        if is_quiet:
            commentary.append("量縮整理中")
        else:
            commentary.append("近期出量波動")
            
        short_desc = "，".join(commentary)

        action_advice = ""
        if not reasons:
            action_advice = "🎯 絕佳進場點：建議分批佈局，並以月線作為防守底線。"
        elif not is_quiet:
            if curr_price >= ma20:
                action_advice = "👀 主力洗盤中：主力試單或震盪洗盤，切勿追高！加入自選股，等待『極度量縮』且回測均線有守時再進場。"
            else:
                action_advice = "⚠️ 帶量下跌：有破底風險，主力可能正在出貨，建議觀望。"
        elif not is_room_ok and space < 5:
            action_advice = "🧱 壓力區臨近：上檔潛在獲利空間不足，容易遇到解套賣壓，建議暫避。"
        elif not is_stable:
            action_advice = "🛑 趨勢轉弱：已跌破月線或趨勢下彎，資金效率低，暫不宜承接。"
        else:
            action_advice = "⏳ 均線尚未糾結，需耐心等待技術面沉澱。"

        yahoo_url = f"https://tw.stock.yahoo.com/quote/{sid}/technical-analysis"
        
        return {
            "代碼": f"{yahoo_url}?code={sid}",
            "名稱": f"{yahoo_url}?name={stock_name}",
            "狀態": status,
            "現況短評": short_desc,
            "現價": round(curr_price, 2),
            "第一壓力": round(p1, 2),
            "終極壓力": round(p2, 2),
            "預計空間": f"{round(space, 1)}%",
            "操作指南": action_advice 
        }
    except Exception as e:
        return None

# ==========================================
# 3. 表格點擊設定與寬度設定
# ==========================================
table_config = {
    "代碼": st.column_config.LinkColumn("代碼", display_text=r"code=(.*)", width="small"),
    "名稱": st.column_config.LinkColumn("名稱", display_text=r"name=(.*)", width="small"), 
    "狀態": st.column_config.TextColumn("狀態", width="small"), 
    "現價": st.column_config.NumberColumn("現價", width="small", format="%.2f"),
    "第一壓力": st.column_config.NumberColumn("第一壓力", width="small", format="%.2f"),
    "終極壓力": st.column_config.NumberColumn("終極壓力", width="small", format="%.2f"),
    "預計空間": st.column_config.TextColumn("預計空間", width="small")
}

# ==========================================
# 4. 主畫面介面 
# ==========================================
st.title("🖥️ 電子股低基期搜尋")
st.markdown('<div class="risk-alert">SYSTEM WARNING // 系統數據與AI短評僅供程式邏輯驗證與參考，絕非任何形式之投資建議，交易請自負盈虧並嚴控風險。</div>', unsafe_allow_html=True)

st.info("💡 提示：系統已套用科技風視覺，點擊表格中的 **「代碼」或「名稱」** 可直達 Yahoo 技術分析。")

col_left, col_right = st.columns([1, 1.5], gap="large")

# --- 左側視窗：單股診斷 (保留操作指南文字顯示) ---
with col_left:
    st.subheader("🎯 個股快速診斷")
    
    st.markdown('<span class="highlight-input-title">⚡ 輸入代號或名稱即時診斷：</span>', unsafe_allow_html=True)
    target_sid = st.text_input("隱藏的標籤", placeholder="例如: 4951 或 直得", label_visibility="collapsed")

    if target_sid:
        target_sid = target_sid.strip()
        
        if not target_sid.isdigit():
            found_code = None
            for code, info in stock_map.items():
                if target_sid in info["name"]:
                    found_code = code
                    break
            if found_code:
                target_sid = found_code
            else:
                st.error(f"❌ 找不到包含「{target_sid}」的股票，請確認名稱。")
                st.stop()

        info = stock_map.get(target_sid, {"name": "未知", "suffix": ".TW"})
        suffix = info["suffix"]
        stock_name = info["name"]
        
        with st.spinner(f'系統連線中: {stock_name} ({target_sid})...'):
            try:
                data = yf.Ticker(f"{target_sid}{suffix}").history(period="75d")
                report = analyze_all_stocks(target_sid, data, stock_name)
                
                if report:
                    if "✅" in report["狀態"]:
                        st.success(f"🎉 **完美達標！**\n\n{report['狀態']}")
                    else:
                        st.warning(f"⚠️ **未達標原因：**\n\n{report['狀態']}")
                    
                    st.info(f"📊 **AI 盤勢短評：** {report['現況短評']}")
                    # 左側依然保留給你看的戰術指導
                    st.error(f"⚔️ **戰術指導：** {report['操作指南']}")
                    
                    df_left = pd.DataFrame([report])[["代碼", "名稱", "現價", "第一壓力", "終極壓力", "預計空間"]]
                    st.dataframe(df_left, column_config=table_config, hide_index=True, use_container_width=True)
                else:
                    st.error("❌ 找不到資料或上市未滿 60 天")
            except Exception as e:
                st.error("❌ Yahoo Finance 資料節點無回應，請稍後重試。")

# --- 右側視窗：700 檔強效獵殺 ---
with col_right:
    st.subheader("🚀 700 檔強效獵殺 (僅顯示完美潛伏)")
    if st.button("啟動核心掃描程序", use_container_width=True):
        all_codes = [str(c) for r in [range(2301,2399), range(2401,2499), range(3001,3100), range(3101,3299), range(6101,6299)] for c in r]
        
        results = []
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        table_placeholder = st.empty()

        total_codes = len(all_codes)
        for idx, sid in enumerate(all_codes):
            progress_val = (idx + 1) / total_codes
            
            info = stock_map.get(sid)
            if not info:
                progress_bar.progress(progress_val)
                continue
                
            stock_name = info["name"]
            suffix = info["suffix"]

            progress_bar.progress(progress_val)
            status_text.text(f"📡 掃描進度: {idx+1}/{total_codes} (正在分析: {sid} {stock_name})")
            
            try:
                df = yf.Ticker(f"{sid}{suffix}").history(period="75d")
                report = analyze_all_stocks(sid, df, stock_name)
                
                if report and "✅" in report["狀態"]:
                    # 【重點修改】過濾掉「現況短評」與「操作指南」，讓右側表格純淨化
                    display_report = {k:v for k,v in report.items() if k not in ["現況短評", "操作指南"]}
                    results.append(display_report)
                    table_placeholder.dataframe(pd.DataFrame(results), column_config=table_config, hide_index=True, use_container_width=True)
                
                if idx % 5 == 0: time.sleep(0.2)
                    
            except:
                continue

        status_text.success(f"✅ 掃描任務完成！共尋獲 {len(results)} 檔完美潛伏標的。")