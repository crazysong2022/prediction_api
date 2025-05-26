import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Polymarket数据筛选工具", page_icon="🔍", layout="centered")
st.title("Polymarket问题与事件Slug采集工具")

# 侧边栏参数设置
with st.sidebar:
    st.header("API配置")
    start_date = st.date_input("开始日期", pd.to_datetime("2023-01-01"))
    end_date = st.date_input("结束日期", pd.to_datetime("2024-12-31"))
    limit = st.slider("返回数据条数", 1, 500, 50)
    fetch_data = st.button("开始采集", key="fetch_button")

# 格式化日期参数
start_date_str = f"{start_date.strftime('%Y-%m-%d')}T00:00:00Z"
end_date_str = f"{end_date.strftime('%Y-%m-%d')}T23:59:59Z"

API_URL = "https://gamma-api.polymarket.com/markets"
query_params = {
    "start_date_min": start_date_str,
    "end_date_min": end_date_str,
    "limit": str(limit)
}

# 缓存请求结果
@st.cache_data(ttl=3600)
def fetch_target_data():
    try:
        response = requests.get(API_URL, params=query_params)
        response.raise_for_status()
        data = response.json()
        # 提取目标字段：questions和events.slug
        result = []
        for item in data:
            question = item.get("question", "")
            # 处理events数组，获取第一个event的slug（根据数据结构调整）
            event_slug = item.get("events", [{}])[0].get("slug", "")
            result.append({"问题": question, "事件Slug": event_slug})
        return pd.DataFrame(result)
    except Exception as e:
        st.error(f"数据采集失败: {str(e)}")
        return pd.DataFrame()

# 主逻辑
if fetch_data:
    with st.spinner("正在筛选数据..."):
        df = fetch_target_data()
        if not df.empty:
            st.success(f"成功采集到 {len(df)} 条数据")
            st.subheader("数据预览")
            st.dataframe(df[["问题", "事件Slug"]], use_container_width=True, height=400)
            
            # 数据导出功能
            csv_data = df.to_csv(index=False)
            st.download_button(
                "下载CSV文件",
                data=csv_data,
                file_name=f"polymarket_questions_slug_{pd.Timestamp.now():%Y%m%d_%H%M%S}.csv",
                mime="text/csv"
            )
        else:
            st.warning("未找到匹配的数据，请调整日期范围或重试")

st.markdown("---")
st.caption("仅显示问题描述及其关联事件的Slug字段 | 数据实时性取决于API更新")