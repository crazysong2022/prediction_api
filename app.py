import os
import requests
import json
import time
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from utils.db_utils import get_db_connection
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 加载环境变量
load_dotenv()

# 设置页面配置
st.set_page_config(
    page_title="Polymarket数据同步工具",
    page_icon="📊",
    layout="wide"
)

# 应用标题
st.title("Polymarket数据同步工具")

# 侧边栏配置
with st.sidebar:
    st.header("配置")
    
    # API配置
    st.subheader("API设置")
    API_URL = st.text_input("API URL", "https://gamma-api.polymarket.com/markets")
    start_date = st.date_input("开始日期", value=pd.to_datetime("2025-01-01"))
    end_date = st.date_input("结束日期", value=pd.to_datetime("2025-01-02"))
    limit = st.number_input("返回数量", min_value=1, max_value=100, value=2)
    
    # 代理配置
    use_proxy = st.checkbox("使用代理服务器")
    if use_proxy:
        http_proxy = st.text_input("HTTP代理", "")
        https_proxy = st.text_input("HTTPS代理", "")
        proxy_dict = {
            'http': http_proxy,
            'https': https_proxy
        }
    else:
        proxy_dict = None
    
    # 自动刷新配置
    st.subheader("自动刷新")
    auto_refresh = st.checkbox("启用自动刷新")
    refresh_interval = st.slider("刷新间隔(分钟)", min_value=1, max_value=60, value=30)

# 缓存API请求函数，避免重复请求
@st.cache_data(ttl=300)
def fetch_polymarket_data(url: str, start_date: str, end_date: str, limit: int, proxy: dict = None) -> dict:
    """从Polymarket API获取市场数据，添加超时和重试机制"""
    querystring = {
        "start_date_min": f"{start_date}T00:00:00Z",
        "end_date_min": f"{end_date}T00:00:00Z",
        "limit": str(limit)
    }
    
    # 配置重试策略
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    try:
        # 设置超时
        response = session.get(url, params=querystring, proxies=proxy, timeout=(5, 10))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API请求错误: {e}")
        return None

def save_to_database(content: dict) -> None:
    """将内容保存到数据库的test表中，若存在则覆盖"""
    if not content:
        st.warning("没有内容可保存")
        return
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 先清空表
                cursor.execute("DELETE FROM test")
                
                # 插入新数据
                cursor.execute(
                    "INSERT INTO test (info) VALUES (%s)",
                    (json.dumps(content),)
                )
            
            conn.commit()
            st.success("数据已成功保存到数据库")
    except Exception as e:
        st.error(f"数据库操作错误: {e}")

# 主界面
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("API数据")
    
    # 手动触发按钮
    if st.button("立即同步数据"):
        with st.spinner("正在获取数据..."):
            api_data = fetch_polymarket_data(
                API_URL, 
                start_date.strftime("%Y-%m-%d"), 
                end_date.strftime("%Y-%m-%d"), 
                limit,
                proxy_dict
            )
            
            if api_data:
                st.json(api_data)
                
                # 保存到数据库
                with st.spinner("正在保存到数据库..."):
                    save_to_database(api_data)
            else:
                st.warning("未能获取到数据")

with col2:
    st.subheader("数据库状态")
    
    # 显示最后更新时间
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM test")
                count = cursor.fetchone()[0]
                
                if count > 0:
                    st.info(f"数据库中有 {count} 条记录")
                    
                    # 显示最后更新时间
                    cursor.execute("SELECT pg_xact_commit_timestamp(xmin) FROM test LIMIT 1")
                    last_updated = cursor.fetchone()[0]
                    st.write(f"最后更新时间: {last_updated}")
                    
                    # 预览数据
                    if st.button("查看数据库内容"):
                        cursor.execute("SELECT info FROM test LIMIT 1")
                        data = cursor.fetchone()[0]
                        st.json(json.loads(data))
                else:
                    st.warning("数据库中没有数据，请先同步")
    except Exception as e:
        st.error(f"无法连接到数据库: {e}")

# 自动刷新逻辑
if auto_refresh:
    st.sidebar.info(f"自动刷新已启用，每 {refresh_interval} 分钟刷新一次")
    
    if 'last_refresh_time' not in st.session_state:
        st.session_state.last_refresh_time = time.time()
    
    current_time = time.time()
    if current_time - st.session_state.last_refresh_time > refresh_interval * 60:
        st.session_state.last_refresh_time = current_time
        
        with st.spinner("自动刷新中..."):
            api_data = fetch_polymarket_data(
                API_URL, 
                start_date.strftime("%Y-%m-%d"), 
                end_date.strftime("%Y-%m-%d"), 
                limit,
                proxy_dict
            )
            
            if api_data:
                save_to_database(api_data)
                st.experimental_rerun()  # 刷新页面    