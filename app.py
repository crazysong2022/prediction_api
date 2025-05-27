import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from translation import get_translation, LANGUAGES

# 定义语言列表（用于索引查找）
LANGUAGE_KEYS = list(LANGUAGES.keys())
DEFAULT_LANGUAGE = "English"  # 默认语言设为英文

# 在任何 Streamlit 命令之前初始化语言
# 1. 尝试从 URL 参数获取语言
# 2. 回退到会话状态
# 3. 默认为英文
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

# 创建语言选择器（默认选中英文）
language = st.sidebar.selectbox(
    get_translation("language_selector", st.session_state.language),
    LANGUAGE_KEYS,
    index=LANGUAGE_KEYS.index(st.session_state.language)
)

# 更新语言状态并刷新页面
if language != st.session_state.language:
    st.session_state.language = language
    st.query_params["lang"] = language  # 更新 URL 参数
    st.rerun()  # 强制刷新页面

# 主标题
st.title(get_translation("page_header", st.session_state.language))

# 侧边栏检索条件
st.sidebar.header(get_translation("sidebar_header", st.session_state.language))
keyword = st.sidebar.text_input(
    get_translation("keyword_label", st.session_state.language)
)
tag_filter = st.sidebar.text_input(
    get_translation("tag_filter_label", st.session_state.language)
)
active_option = st.sidebar.selectbox(
    get_translation("active_option_label", st.session_state.language),
    options=[
        get_translation("active_option_all", st.session_state.language),
        get_translation("active_option_active", st.session_state.language),
        get_translation("active_option_inactive", st.session_state.language)
    ]
)
start_date = st.sidebar.date_input(
    get_translation("start_date_label", st.session_state.language),
    value=datetime(2024, 9, 1)
)
end_date = st.sidebar.date_input(
    get_translation("end_date_label", st.session_state.language),
    value=datetime(2025, 12, 31)
)
volume_min = st.sidebar.slider(
    get_translation("volume_min_label", st.session_state.language),
    min_value=0, max_value=10000000, value=1000000, step=100000
)
page_size = st.sidebar.slider(
    get_translation("page_size_label", st.session_state.language),
    min_value=10, max_value=50, value=20
)

# 分页状态
if "page" not in st.session_state:
    st.session_state.page = 0

if st.sidebar.button(get_translation("reset_page_button", st.session_state.language)):
    st.session_state.page = 0

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

# 移除值为None的参数
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

# 客户端关键词和标签过滤
def filter_events(events, keyword, tag_filter):
    filtered = []
    keyword = keyword.lower().strip()
    tag_filter = tag_filter.lower().strip()
    for e in events:
        title = e.get("title", "").lower()
        description = e.get("description", "").lower()
        tags = []
        for tag in e.get("tags", []):
            if isinstance(tag, dict):
                tags.append(tag.get("label", "").lower())
            elif isinstance(tag, str):
                tags.append(tag.lower())
        tags_text = " ".join(tags)
        
        keyword_match = (keyword in title) or (keyword in description) if keyword else True
        tag_match = (tag_filter in tags_text) if tag_filter else True
        if keyword_match and tag_match:
            filtered.append(e)
    return filtered

filtered_events = filter_events(events, keyword, tag_filter)

# 分页按钮
col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    if st.button(get_translation("previous_page", st.session_state.language)) and st.session_state.page > 0:
        st.session_state.page -= 1
with col3:
    if st.button(get_translation("next_page", st.session_state.language)):
        st.session_state.page += 1

st.write(f"{get_translation('current_page', st.session_state.language)} {st.session_state.page + 1}")

if not filtered_events:
    st.warning(get_translation("no_events_found", st.session_state.language))
else:
    def safe_get(event, keys):
        for key in keys:
            if key in event and event[key] is not None:
                return event[key]
        return ""

    rows = []
    for e in filtered_events:
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
    slug_list = [e.get("slug", "") for e in filtered_events]
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

            # 展示市场行情
            st.subheader(get_translation("market_data", st.session_state.language))
            markets = event.get("markets", [])
            if markets:
                def render_market_data(market, lang):
                    """渲染单个市场的数据和可视化图表"""
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # 结果选项和价格可视化
                        st.subheader(get_translation("market_outcomes", lang))
                        outcomes = eval(market.get("outcomes", "[]"))
                        prices = eval(market.get("outcomePrices", "[]"))
                        
                        if outcomes and prices:
                            # 创建结果选项的条形图
                            outcomes_df = pd.DataFrame({
                                get_translation("market_outcomes", lang): outcomes,
                                get_translation("market_prices", lang): [float(p) for p in prices]
                            })
                            st.bar_chart(outcomes_df, x=get_translation("market_outcomes", lang), y=get_translation("market_prices", lang))
                            
                            # 显示具体价格数值
                            for outcome, price in zip(outcomes, prices):
                                st.write(f"- {outcome}: {float(price):.3f}")
                        else:
                            st.info("No outcome data available")
                        
                        # 成交量趋势图
                        st.subheader(get_translation("volume_trend", lang))
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
                        # 市场基本信息卡片
                        st.markdown("### " + get_translation("market_info", lang))
                        st.write(f"**{get_translation('start_date', lang)}:** {market.get('startDate', '-')}")
                        st.write(f"**{get_translation('end_date', lang)}:** {market.get('endDate', '-')}")
                        st.write(f"**{get_translation('volume', lang)}:** {market.get('volume', '-')}")
                        
                        # 状态指示器
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
                        
                        # 图标显示
                        icon_url = market.get("icon", "")
                        if icon_url:
                            st.image(icon_url, width=100, caption=get_translation("market_icon", lang))
                
                # 渲染所有市场
                for idx, market in enumerate(markets):
                    with st.expander(market.get("question", f"{get_translation('market', st.session_state.language)} {idx+1}")):
                        render_market_data(market, st.session_state.language)
            else:
                st.info(get_translation("no_market_data", st.session_state.language))
        else:
            st.error("No event found with this slug.")











