import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from translation import get_translation, LANGUAGES

# 定义语言列表（用于索引查找）
LANGUAGE_KEYS = list(LANGUAGES.keys())
DEFAULT_LANGUAGE = "English"  # 默认语言设为英文

# 在任何 Streamlit 命令之前初始化语言
query_lang = st.query_params.get("lang", [DEFAULT_LANGUAGE])[0]
if query_lang in LANGUAGES:
    default_language = query_lang
else:
    default_language = st.session_state.get("language", DEFAULT_LANGUAGE)

# 设置会话状态（在 set_page_config 之前）
st.session_state.language = default_language

# 设置页面配置（必须是第一个 Streamlit 命令）
st.set_page_config(
    page_title=get_translation("page_title", st.session_state.language),
    layout="wide"
)

# 主标题
st.title(get_translation("page_header", st.session_state.language))

# ====== 侧边栏部分 ======
with st.sidebar:
    st.markdown("## 🌍 HABITATS 栖息地")
    st.markdown("---")

    # 展开面板1："预测市场"
    with st.expander("预测市场", expanded=False):  # 默认收起
        language = st.selectbox(
            get_translation("language_selector", st.session_state.language),
            LANGUAGE_KEYS,
            index=LANGUAGE_KEYS.index(st.session_state.language),
            key="predict_market_lang_selectbox"
        )
        if language != st.session_state.language:
            st.session_state.language = language
            st.query_params["lang"] = language
            st.rerun()

        st.header(get_translation("sidebar_header", st.session_state.language))
        active_option = st.selectbox(
            get_translation("active_option_label", st.session_state.language),
            options=[
                get_translation("active_option_all", st.session_state.language),
                get_translation("active_option_active", st.session_state.language),
                get_translation("active_option_inactive", st.session_state.language)
            ]
        )

        start_date = st.date_input(
            get_translation("start_date_label", st.session_state.language),
            value=datetime(2024, 9, 1)
        )
        end_date = st.date_input(
            get_translation("end_date_label", st.session_state.language),
            value=datetime(2025, 12, 31)
        )

        volume_min = st.slider(
            get_translation("volume_min_label", st.session_state.language),
            min_value=0, max_value=10000000, value=1000000, step=100000
        )

        page_size = st.slider(
            get_translation("page_size_label", st.session_state.language),
            min_value=10, max_value=50, value=20
        )

        if "page" not in st.session_state:
            st.session_state.page = 0
        if st.button(get_translation("reset_page_button", st.session_state.language)):
            st.session_state.page = 0

    # 展开面板2："RWA 资产代币化"
    with st.expander("RWA 资产代币化", expanded=False):
        st.markdown("#### 请选择资产类型")

        ASSET_TYPES = {
            "稳定币": "stablecoin",
            "美国国债": "treasury_bonds",
            "全球债券": "global_bonds",
            "大宗商品": "commodities",
            "股票": "stocks",
            "房地产": "real_estate"
        }

        selected_asset = st.radio(
            "资产类型",
            options=list(ASSET_TYPES.keys()),
            index=0,
            key="rwa_asset_selector"
        )

        if st.button("进入资产详情"):
            st.session_state.view = "rwa"
            st.session_state.rwa_asset = ASSET_TYPES[selected_asset]
            st.rerun()

# 构造API参数
params = {
    "limit": str(page_size),
    "offset": str(st.session_state.page * page_size),
    "active": None,
    "start_date_min": datetime.combine(start_date, datetime.min.time()).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "end_date_max": datetime.combine(end_date, datetime.max.time()).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "volume_min": str(volume_min)
}

if active_option == get_translation("active_option_active", st.session_state.language):
    params["active"] = "true"
elif active_option == get_translation("active_option_inactive", st.session_state.language):
    params["active"] = "false"
else:
    params.pop("active")

params = {k: v for k, v in params.items() if v is not None}

@st.cache_data(show_spinner=False)
def fetch_events(params):
    url = "https://gamma-api.polymarket.com/events"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list):
            return data
    return []

events = fetch_events(params)

# ====== 显示 RWA 或预测市场内容 ======

# 如果用户选择了 RWA 模块
if st.session_state.get("view") == "rwa":
    try:
        from rwa import (
            show_stablecoin,
            show_treasury_bonds,
            show_global_bonds,
            show_commodities,
            show_stocks,
            show_real_estate
        )

        rwa_asset = st.session_state.get("rwa_asset", "stablecoin")

        if rwa_asset == "stablecoin":
            show_stablecoin()
        elif rwa_asset == "treasury_bonds":
            show_treasury_bonds()
        elif rwa_asset == "global_bonds":
            show_global_bonds()
        elif rwa_asset == "commodities":
            show_commodities()
        elif rwa_asset == "stocks":
            show_stocks()
        elif rwa_asset == "real_estate":
            show_real_estate()

        if st.button("返回预测市场"):
            st.session_state.view = "predict_market"
            st.rerun()

    except ImportError:
        st.error("无法加载 RWA 模块，请确保 rwa.py 存在并可导入。")

# 默认显示预测市场内容
else:
    if not events:
        st.warning(get_translation("no_events_found", st.session_state.language))
    else:
        def safe_get(event, keys):
            for key in keys:
                if key in event and event[key] is not None:
                    return event[key]
            return ""

        rows = []
        for e in events:
            row = {
                get_translation("title", st.session_state.language): safe_get(e, ["title"]),
                get_translation("start_date", st.session_state.language): safe_get(e, ["startDate"]),
                get_translation("end_date", st.session_state.language): safe_get(e, ["endDate"]),
                get_translation("volume", st.session_state.language): safe_get(e, ["volume"])
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        st.dataframe(df)

        # 选择事件进行详情查看
        st.subheader(get_translation("select_event", st.session_state.language))
        slug_list = [e.get("slug", "") for e in events]
        selected_slug = st.selectbox(
            get_translation("select_event_slug", st.session_state.language),
            slug_list
        )

        if selected_slug:
            detail_url = "https://gamma-api.polymarket.com/events"
            detail_params = {"slug": selected_slug}
            detail_resp = requests.get(detail_url, params=detail_params)
            detail_data = detail_resp.json()
            if isinstance(detail_data, list) and len(detail_data) > 0:
                event = detail_data[0]
                st.markdown(f"### {event['title']}")
                if event.get("image"):
                    st.image(event["image"], width=300)
                st.write(f"**{get_translation('description', st.session_state.language)}：** {event.get('description', '')}")
                st.write(f"**{get_translation('category', st.session_state.language)}：** {safe_get(event, ['category', 'categories'])}")
                st.write(f"**{get_translation('start_date', st.session_state.language)}：** {event.get('startDate', '')}")
                st.write(f"**{get_translation('end_date', st.session_state.language)}：** {event.get('endDate', '')}")
                st.write(f"**{get_translation('volume', st.session_state.language)}：** {event.get('volume', '')}")
                tags = event.get("tags", [])
                if tags:
                    st.write(f"**{get_translation('tags', st.session_state.language)}：** " + ", ".join([tag.get("label", "") for tag in tags]))
                markets = event.get("markets", [])
                if markets:
                    def render_market_data(market, lang):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            outcomes = eval(market.get("outcomes", "[]"))
                            prices = eval(market.get("outcomePrices", "[]"))
                            if outcomes and prices:
                                outcomes_df = pd.DataFrame({
                                    get_translation("market_outcomes", lang): outcomes,
                                    get_translation("market_prices", lang): [float(p) for p in prices]
                                })
                                st.bar_chart(outcomes_df, x=get_translation("market_outcomes", lang), y=get_translation("market_prices", lang))
                                for outcome, price in zip(outcomes, prices):
                                    st.write(f"- {outcome}: {float(price):.3f}")
                            else:
                                st.info("No outcome data available")
                            volume_data = {
                                get_translation("volume_24hr", lang): market.get("volume24hr", 0),
                                get_translation("volume_1wk", lang): market.get("volume1wk", 0),
                                get_translation("volume_1mo", lang): market.get("volume1mo", 0),
                                get_translation("volume_1yr", lang): market.get("volume1yr", 0)
                            }
                            volume_df = pd.DataFrame(list(volume_data.items()), columns=[
                                get_translation("time_period", lang),
                                get_translation("volume", lang)
                            ])
                            st.line_chart(volume_df.set_index(get_translation("time_period", lang)))
                        with col2:
                            st.markdown("### " + get_translation("market_info", lang))
                            st.write(f"**{get_translation('start_date', lang)}:** {market.get('startDate', '-')}")
                            st.write(f"**{get_translation('end_date', lang)}:** {market.get('endDate', '-')}")
                            st.write(f"**{get_translation('volume', lang)}:** {market.get('volume', '-')}")
                            status = "status_open" if market.get("closed", False) is False else "status_closed"
                            status_text = get_translation(status, lang)
                            status_color = "green" if status == "status_open" else "red"
                            st.markdown(f"""
                            <div style="margin-top: 1rem; padding: 0.5rem; border-radius: 0.5rem; 
                                        background-color: {'#e8f5e9' if status == 'status_open' else '#ffebee'}; 
                                        color: {status_color}; text-align: center;">
                                <b>{get_translation('status', lang)}:</b> {status_text}
                            </div>
                            """, unsafe_allow_html=True)
                            icon_url = market.get("icon", "")
                            if icon_url:
                                st.image(icon_url, width=100, caption=get_translation("market_icon", lang))
                    for idx, market in enumerate(markets):
                        with st.expander(market.get("question", f"{get_translation('market', st.session_state.language)} {idx+1}")):
                            render_market_data(market, st.session_state.language)
            else:
                st.error("No event found with this slug.")