# rwa.py

import streamlit as st
import pandas as pd
import plotly.express as px
from db import get_db_engine

def load_rwa_data(query):
    """通用函数：从数据库执行 SQL 查询并返回 DataFrame"""
    engine = get_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

def show_stablecoin():
    st.header("稳定币 🪙")
    st.subheader("各链上稳定币市场价值（Bridged Token Market Cap）")

    query = "SELECT * FROM rwa_稳定币_代币;"
    
    try:
        df = load_rwa_data(query)

        if not df.empty:
            # 转换时间戳列
            if 'Timestamp' in df.columns:
                df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
            elif 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], format='%Y/%m/%d')

            # 筛选所有资产列（排除非数值列）
            asset_columns = df.select_dtypes(include=['number']).columns.tolist()

            if len(asset_columns) == 0:
                st.warning("没有可绘制的数值列，请检查数据结构。")
                return

            # 长格式转换，便于 Plotly 展示
            df_long = df.melt(id_vars=['Date'], value_vars=asset_columns,
                              var_name='Chain_Asset', value_name='Value')

            # 去除 NaN 或 0 值以避免干扰图表
            df_long = df_long.dropna()
            df_long = df_long[df_long['Value'] > 0]

            # 初始化 session_state 中的资产选择状态
            if "selected_assets" not in st.session_state:
                st.session_state.selected_assets = []

            # 添加多选控件
            selected_assets = st.multiselect(
                "请选择要显示的稳定币资产",
                options=sorted(asset_columns),
                default=st.session_state.selected_assets,
                key="stablecoin_asset_multiselect"
            )

            # 判断是否发生变化，仅当变化时才更新 session_state 并刷新页面
            if selected_assets != st.session_state.selected_assets:
                st.session_state.selected_assets = selected_assets
                st.rerun()

            # 过滤数据
            if st.session_state.selected_assets:
                filtered_df = df_long[df_long['Chain_Asset'].isin(st.session_state.selected_assets)]
            else:
                filtered_df = pd.DataFrame()  # 空数据

            # 绘制图表
            if not filtered_df.empty:
                fig = px.line(
                    filtered_df,
                    x='Date',
                    y='Value',
                    color='Chain_Asset',
                    title="所选稳定币资产的时间序列趋势",
                    labels={'Value': '市场价值 (美元)', 'Date': '时间'}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("请从上方选择至少一个资产进行展示。")

        else:
            st.warning("数据库中没有找到相关数据。")

    except Exception as e:
        st.error(f"加载或解析数据失败: {e}")

def show_treasury_bonds():
    st.header("美国国债 🏦")
    st.subheader("各链上代币化资产价值（Bridged Token Value）")

    # 查询主表（链资产）
    query_assets = "SELECT * FROM rwa_美国国债_代币;"
    df_assets = load_rwa_data(query_assets)

    # 查询管辖权表（国家分布）
    query_jurisdictions = "SELECT * FROM rwa_美国国债_管辖权;"
    df_jurisdictions = load_rwa_data(query_jurisdictions)

    if not df_assets.empty:
        # 处理时间列
        if 'Timestamp' in df_assets.columns:
            df_assets['Date'] = pd.to_datetime(df_assets['Timestamp'], unit='ms')
        elif 'Date' in df_assets.columns:
            df_assets['Date'] = pd.to_datetime(df_assets['Date'], format='%Y/%m/%d')

        # 获取资产列
        asset_columns = df_assets.select_dtypes(include=['number']).columns.tolist()
        if 'Date' in asset_columns:
            asset_columns.remove('Date')
        if 'Timestamp' in asset_columns:
            asset_columns.remove('Timestamp')

        # 初始化 session_state
        if "selected_assets" not in st.session_state:
            st.session_state.selected_assets = []

        # 资产多选控件
        selected_assets = st.multiselect(
            "请选择要显示的链上资产",
            options=sorted(asset_columns),
            default=st.session_state.selected_assets,
            key="asset_multiselect"
        )

        # 判断是否发生变化，仅当变化时才更新 session_state 并刷新
        if selected_assets != st.session_state.selected_assets:
            st.session_state.selected_assets = selected_assets
            st.rerun()

        # 过滤数据
        if st.session_state.selected_assets:
            filtered_df = df_assets.melt(id_vars=['Date'],
                                          value_vars=st.session_state.selected_assets,
                                          var_name='Chain_Asset',
                                          value_name='Value')
            filtered_df = filtered_df[filtered_df['Value'] > 0]

            fig_assets = px.line(
                filtered_df,
                x='Date',
                y='Value',
                color='Chain_Asset',
                title="所选资产的时间序列趋势",
                labels={'Value': '资产价值 (美元)', 'Date': '时间'}
            )
            st.plotly_chart(fig_assets, use_container_width=True)

        else:
            st.info("请从上方选择至少一个资产进行展示。")

    else:
        st.warning("数据库中没有找到链资产数据。")

    st.markdown("---")

    if not df_jurisdictions.empty:
        st.subheader("各国发行价值分布 🌍")

        # 处理时间列
        if 'Timestamp' in df_jurisdictions.columns:
            df_jurisdictions['Date'] = pd.to_datetime(df_jurisdictions['Timestamp'], unit='ms')
        elif 'Date' in df_jurisdictions.columns:
            df_jurisdictions['Date'] = pd.to_datetime(df_jurisdictions['Date'], format='%Y/%m/%d')

        # 获取国家列
        country_columns = df_jurisdictions.select_dtypes(include=['number']).columns.tolist()
        if 'Date' in country_columns:
            country_columns.remove('Date')
        if 'Timestamp' in country_columns:
            country_columns.remove('Timestamp')

        # 初始化 session_state
        if "selected_countries" not in st.session_state:
            st.session_state.selected_countries = []

        # 国家多选控件
        selected_countries = st.multiselect(
            "请选择要显示的国家/地区",
            options=sorted(country_columns),
            default=st.session_state.selected_countries,
            key="country_multiselect"
        )

        # 判断是否发生变化，仅当变化时才更新 session_state 并刷新
        if selected_countries != st.session_state.selected_countries:
            st.session_state.selected_countries = selected_countries
            st.rerun()

        # 过滤数据
        if st.session_state.selected_countries:
            filtered_country_df = df_jurisdictions.melt(id_vars=['Date'],
                                                          value_vars=st.session_state.selected_countries,
                                                          var_name='Country',
                                                          value_name='Value')
            filtered_country_df = filtered_country_df[filtered_country_df['Value'] > 0]

            fig_countries = px.bar(
                filtered_country_df,
                x='Date',
                y='Value',
                color='Country',
                title="所选国家的资产价值分布",
                labels={'Value': '资产价值 (美元)', 'Date': '时间'},
                barmode='stack'
            )
            st.plotly_chart(fig_countries, use_container_width=True)

        else:
            st.info("请从上方选择至少一个国家进行展示。")

    else:
        st.warning("数据库中没有找到国家分布数据。")

def show_global_bonds():
    st.header("全球债券 🌍")
    st.write("这是全球债券资产的信息展示区域。")
    st.info("功能开发中...")

def show_commodities():
    st.header("大宗商品 ⛽")
    st.write("这是大宗商品资产的信息展示区域。")
    st.info("功能开发中...")

def show_stocks():
    st.header("股票 📈")
    st.write("这是股票资产的信息展示区域。")
    st.info("功能开发中...")

def show_real_estate():
    st.header("房地产 🏠")
    st.write("这是房地产资产的信息展示区域。")
    st.info("功能开发中...")