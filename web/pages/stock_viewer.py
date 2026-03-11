# -*- coding: utf-8 -*-
"""个股分析 - 详细图表 + 智能指标解读 + 实战教学"""
import sys
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np

import importlib
from config import get_session_factory
from database.models import Stock, DailyPrice, TechnicalIndicator
from analysis import TrendAnalyzer
from analysis.risk_metrics import RiskMetrics
from analysis.valuation_analyzer import (
    ValuationAnalyzer, ValuationMetrics, ValuationResult,
    format_valuation_report, ValuationLevel, InvestmentSuggestion
)

# 强制重新加载 collectors 模块以获取最新更改
import collectors.akshare_collector
importlib.reload(collectors.akshare_collector)
from collectors.akshare_collector import AKShareCollector

st.set_page_config(page_title="个股分析 | Stock Viewer", layout="wide")

# ============== 技术指标详细教学内容 ==============
INDICATOR_GUIDE = {
    'MA': {
        'title': '📈 均线系统 (Moving Average) - 实战详解',
        'intro': """
        ## 什么是均线？
        
        均线（Moving Average, MA）是技术分析中最基础、最重要的指标之一。它将一段时间内的收盘价求平均，
        形成一条平滑的曲线，用于过滤短期价格波动，反映股价的中长期趋势。
        
        **核心思想**："趋势是你的朋友"（Trend is your friend）。均线帮助我们识别趋势方向、判断支撑阻力位、发现买卖时机。
        """,
        'calculation': """
        ### 计算公式
        
        **简单移动平均线 (SMA)**：
        $$MA_n = \\frac{P_1 + P_2 + ... + P_n}{n}$$
        
        其中：
        - $P_1$ 到 $P_n$ 是最近 n 天的收盘价
        - $n$ 是计算周期（如5日、20日、60日）
        
        **实际案例**：
        假设某股票最近5日收盘价为：10.0, 10.5, 11.0, 10.8, 11.2元
        
        则 MA5 = (10.0 + 10.5 + 11.0 + 10.8 + 11.2) / 5 = **10.7元**
        
        如果第6天收盘价为11.5元，则新的MA5 = (10.5 + 11.0 + 10.8 + 11.2 + 11.5) / 5 = **11.0元**
        """,
        'interpretation': """
        ### 实战解读技巧
        
        #### 1️⃣ 多头排列 vs 空头排列
        
        **多头排列**（MA5 > MA20 > MA60）：
        - 短期均线在最上方，中期次之，长期在最下方
        - 代表股价处于**强势上升趋势**
        - 各条均线都成为回调时的支撑位
        - **操作策略**：持股待涨，回调到均线附近买入
        
        **空头排列**（MA5 < MA20 < MA60）：
        - 短期均线在最下方，中期次之，长期在最上方
        - 代表股价处于**弱势下跌趋势**
        - 各条均线都成为反弹时的阻力位
        - **操作策略**：空仓观望，反弹到均线附近卖出
        
        #### 2️⃣ 金叉与死叉
        
        **金叉**（黄金交叉）：短期均线上穿中期均线
        - MA5 上穿 MA20：短期买入信号
        - MA5 上穿 MA60：中期买入信号，可靠性更高
        - 发生在低位时，信号更可靠
        - **实战要点**：成交量配合放大，金叉更有效
        
        **死叉**（死亡交叉）：短期均线下穿中期均线
        - MA5 下穿 MA20：短期卖出信号
        - MA5 下穿 MA60：中期卖出信号，需高度重视
        - 发生在高位时，信号更可靠
        - **实战要点**：跌破重要均线后，往往开启一波下跌
        
        #### 3️⃣ 价格与均线的关系
        
        | 位置关系 | 市场含义 | 操作建议 |
        |---------|---------|---------|
        | 股价 > MA5 | 短期强势 | 可持有 |
        | 股价 > MA20 | 中期强势 | 中期持有 |
        | 股价 > MA60 | 长期强势 | 长期看好 |
        | 股价 < MA5 | 短期弱势 | 减仓 |
        | 股价跌破MA20 | 中期转弱 | 考虑离场 |
        | 股价跌破MA60 | 长期转弱 | 止损离场 |
        """,
        'examples': """
        ### 真实案例分析
        
        **案例1：多头排列买入法**
        
        假设光伏ETF（515790）在某段时间：
        - MA5 = 1.18元（持续向上）
        - MA20 = 1.15元（拐头向上）
        - MA60 = 1.10元（稳步向上）
        - 当前价格 = 1.20元
        
        **分析过程**：
        1. 价格(1.20) > MA5(1.18) > MA20(1.15) > MA60(1.10)，形成完美的多头排列
        2. 说明短期、中期、长期资金都在流入，趋势强劲
        3. 每次回调到MA5(1.18)附近都是买入机会
        4. 跌破MA20(1.15)时考虑减仓，跌破MA60(1.10)时止损
        
        **案例2：金叉买入实战**
        
        某股票经过一个月下跌后：
        - 第1天：MA5=10.0, MA20=10.2（空头排列）
        - 第5天：股价大涨5%，MA5=10.5, MA20=10.3
        - **金叉形成**：MA5(10.5) > MA20(10.3)，且MA5拐头向上
        - 成交量较昨日放大150%
        - **判断**：金叉+放量，买入信号可靠
        - **买入价**：10.5元左右
        - **止损位**：跌破MA20(10.3)或设置-5%止损
        """,
        'common_mistakes': """
        ### ⚠️ 常见误区与注意事项
        
        1. **均线滞后性**
           - 均线基于历史价格计算，必然滞后于价格
           - 在快速拉升或暴跌行情中，均线信号会延迟
           - **对策**：结合K线形态、成交量综合判断
        
        2. **震荡市失效**
           - 横盘震荡时，均线反复交叉，产生大量假信号
           - 此时金叉买入、死叉卖出会导致频繁亏损
           - **对策**：震荡市少用均线，改用RSI、布林带等指标
        
        3. **周期选择不当**
           - 短线交易者用MA60做决策，信号太慢
           - 长线投资者用MA5做决策，信号太杂
           - **建议**：短线看MA5/MA10，中线看MA20/MA30，长线看MA60/MA120
        
        4. **忽视成交量**
           - 金叉但成交量萎缩，可能是假突破
           - 死叉但成交量放大，下跌趋势确认
           - **原则**：所有价格信号都需要成交量验证
        """
    },
    'MACD': {
        'title': '📊 MACD指标 - 趋势跟踪利器',
        'intro': """
        ## 什么是MACD？
        
        MACD（Moving Average Convergence Divergence，指数平滑异同移动平均线）是由Gerald Appel于1970年代提出的，
        是股票技术分析中最经典、使用最广泛的指标之一。
        
        **核心功能**：
        1. 判断趋势方向和强度
        2. 识别趋势转折（金叉死叉）
        3. 发现顶背离、底背离（趋势衰竭信号）
        
        **MACD vs 均线**：MACD比单条均线更灵敏，比多条均线更直观。
        """,
        'calculation': """
        ### 计算公式详解
        
        MACD由三部分组成：**DIF线、DEA线、MACD柱状图**
        
        #### 第一步：计算EMA（指数移动平均）
        
        $$EMA_{12} = EMA_{12昨日} \\times \\frac{11}{13} + 今日收盘价 \\times \\frac{2}{13}$$
        
        $$EMA_{26} = EMA_{26昨日} \\times \\frac{25}{27} + 今日收盘价 \\times \\frac{2}{27}$$
        
        #### 第二步：计算DIF（差离值）
        
        $$DIF = EMA_{12} - EMA_{26}$$
        
        DIF是快速线，反映短期趋势相对长期趋势的变化。
        
        #### 第三步：计算DEA（信号线）
        
        $$DEA = DEA_{昨日} \\times \\frac{8}{10} + DIF \\times \\frac{2}{10}$$
        
        DEA是DIF的9日EMA，作为信号线，比DIF更平滑。
        
        #### 第四步：计算MACD柱状图
        
        $$MACD柱状图 = (DIF - DEA) \\times 2$$
        
        **为什么是2倍？** 为了放大差异，让柱状图变化更明显。
        
        #### 实战计算示例
        
        假设某日数据：
        - 收盘价：100元
        - EMA12（昨日）：98元
        - EMA26（昨日）：95元
        - DEA（昨日）：2.5
        
        **计算过程**：
        1. 今日EMA12 = 98 × 11/13 + 100 × 2/13 = **98.31**
        2. 今日EMA26 = 95 × 25/27 + 100 × 2/27 = **95.37**
        3. 今日DIF = 98.31 - 95.37 = **2.94**
        4. 今日DEA = 2.5 × 8/10 + 2.94 × 2/10 = **2.59**
        5. MACD柱状图 = (2.94 - 2.59) × 2 = **0.70**
        """,
        'interpretation': """
        ### MACD实战解读
        
        #### 1️⃣ 零轴的意义
        
        **零轴上方（DIF > 0）**：
        - 12日EMA > 26日EMA，短期趋势强于长期趋势
        - 处于**多头市场**，以做多为主
        - 零轴上方的金叉信号更可靠
        - 跌破零轴是重要警示信号
        
        **零轴下方（DIF < 0）**：
        - 12日EMA < 26日EMA，短期趋势弱于长期趋势
        - 处于**空头市场**，以观望或做空为主
        - 零轴下方的死叉信号更可靠
        - 上穿零轴是潜在买入信号
        
        #### 2️⃣ 金叉与死叉详解
        
        **金叉类型（按可靠性排序）**：
        
        | 类型 | 条件 | 可靠性 | 操作建议 |
        |-----|------|-------|---------|
        | 🔥 零上二次金叉 | 零轴上方，第二次金叉 | ⭐⭐⭐⭐⭐ | 强烈买入 |
        | 🟢 零上首次金叉 | 零轴上方，第一次金叉 | ⭐⭐⭐⭐ | 积极买入 |
        | 🟡 零下金叉 | 零轴下方金叉 | ⭐⭐⭐ | 谨慎买入，需确认 |
        | ⚠️ 零下二次金叉 | 零轴下方第二次金叉 | ⭐⭐ | 观望，可能继续下跌 |
        
        **死叉类型（按危险性排序）**：
        
        | 类型 | 条件 | 危险性 | 操作建议 |
        |-----|------|-------|---------|
        | 🔥 零下二次死叉 | 零轴下方，第二次死叉 | ⭐⭐⭐⭐⭐ | 强烈卖出/止损 |
        | 🔴 零下首次死叉 | 零轴下方，第一次死叉 | ⭐⭐⭐⭐ | 卖出 |
        | 🟠 零上死叉 | 零轴上方死叉 | ⭐⭐⭐ | 减仓，可能回调 |
        | ⚠️ 零上二次死叉 | 零轴上方第二次死叉 | ⭐⭐ | 警惕，趋势可能反转 |
        
        #### 3️⃣ MACD柱状图的奥秘
        
        **柱状图变长（放大）**：
        - 红柱变长：上涨动能增强
        - 绿柱变长：下跌动能增强
        
        **柱状图缩短（收敛）**：
        - 红柱缩短：上涨动能减弱，可能回调
        - 绿柱缩短：下跌动能减弱，可能反弹
        
        **柱状图与零轴的关系**：
        - 红柱在零轴上方：多头强势
        - 绿柱在零轴下方：空头强势
        - 柱状图穿越零轴：趋势转折信号
        """,
        'examples': """
        ### MACD实战案例分析
        
        **案例1：零上金叉买入法**
        
        背景：某科技股经过3个月横盘整理后启动
        
        **时间线分析**：
        - 第1周：DIF=0.5, DEA=0.3, 红柱0.4（零轴上方运行）
        - 第2周：股价大涨10%，DIF=1.2, DEA=0.8, 红柱0.8
        - 第3周：回调5%，DIF=0.9, DEA=0.85（DIF向DEA靠拢）
        - 第4周：再次大涨，DIF=1.5, DEA=1.0, **金叉形成**（DIF上穿DEA）
        
        **买入逻辑**：
        1. 金叉发生在零轴上方，属于强势金叉
        2. 金叉前红柱曾经缩短但未变绿，属于强势整理
        3. 成交量在金叉日放大至前期2倍
        4. 股价突破前期整理平台上沿
        5. **买入点**：金叉确认后第二日开盘价
        6. **止损位**：DIF下穿DEA（死叉）或-8%
        
        **案例2：顶背离卖出法**
        
        背景：某白马股经过半年上涨，股价创新高
        
        **背离识别**：
        - 2个月前：股价=100元，DIF=2.5（高点）
        - 1个月前：股价=105元，DIF=2.3（次高点，略低）
        - 当前：股价=110元（创新高！），DIF=2.0（明显下降）
        
        **顶背离判断**：
        1. 股价连续3次创新高（100→105→110）
        2. DIF连续3次降低（2.5→2.3→2.0）
        3. 形成明显的**顶背离**
        4. MACD柱状图红柱明显缩短
        
        **卖出策略**：
        - 发现背离后，不再追高，准备减仓
        - 当DIF下穿DEA（死叉）时，果断卖出50%
        - 当DIF下穿零轴时，清仓剩余50%
        
        **结果**：该股票在背离出现后2个月内下跌25%
        """,
        'common_mistakes': """
        ### MACD使用误区
        
        1. **过度频繁交易**
           - MACD在震荡市会产生大量假信号
           - 频繁金叉死叉导致高买低卖
           - **解决**：只在明显的趋势中使用MACD
        
        2. **忽视零轴位置**
           - 零下金叉买入，容易被套
           - 零上死叉卖出，容易错过主升
           - **原则**：零轴上方多买少卖，零轴下方多看少动
        
        3. **单独使用MACD**
           - MACD是趋势指标，没有超买超卖概念
           - 需要配合RSI、KDJ判断买卖点
           - **建议**：MACD定方向，其他指标定买卖
        
        4. **柱状图误解**
           - 红柱存在不代表一定会涨
           - 绿柱缩短不代表一定会反弹
           - **注意**：柱状图只是DIF和DEA的差值，不代表价格绝对涨跌
        """
    },
    'RSI': {
        'title': '🌡️ RSI指标 - 超买超卖探测器',
        'intro': """
        ## 什么是RSI？
        
        RSI（Relative Strength Index，相对强弱指标）由Welles Wilder于1978年提出，
        是衡量买卖双方力量对比的技术指标，取值范围0-100。
        
        **核心作用**：
        - 识别超买（Overbought）和超卖（Oversold）状态
        - 发现顶背离和底背离
        - 判断多空力量对比
        
        **RSI vs 其他指标**：
        - MACD看趋势，RSI看强弱
        - KDJ看短线，RSI看中短线
        - RSI比KDJ更平滑，假信号更少
        """,
        'calculation': """
        ### RSI计算公式
        
        #### 第一步：计算价格变动
        
        对于每一天，计算：
        - 涨幅（Gain）：如果今日收盘 > 昨日收盘，Gain = 差价，否则 Gain = 0
        - 跌幅（Loss）：如果今日收盘 < 昨日收盘，Loss = |差价|，否则 Loss = 0
        
        #### 第二步：计算平均涨幅和平均跌幅
        
        **简单平均法（Wilder原始方法）**：
        
        $$平均涨幅 = \\frac{前13日涨幅总和 + 今日涨幅}{14}$$
        
        $$平均跌幅 = \\frac{前13日跌幅总和 + 今日跌幅}{14}$$
        
        #### 第三步：计算RS和RSI
        
        $$RS = \\frac{平均涨幅}{平均跌幅}$$
        
        $$RSI = 100 - \\frac{100}{1 + RS} = \\frac{平均涨幅}{平均涨幅 + 平均跌幅} \\times 100$$
        
        #### 实战计算示例
        
        假设某股票最近14天的涨跌幅如下（单位：元）：
        
        | 天数 | 收盘价 | 涨跌 | 涨幅 | 跌幅 |
        |-----|-------|-----|------|------|
        | 1 | 100 | - | - | - |
        | 2 | 102 | +2 | 2 | 0 |
        | 3 | 101 | -1 | 0 | 1 |
        | ... | ... | ... | ... | ... |
        | 14 | 110 | +1 | 1 | 0 |
        | 15 | 108 | -2 | 0 | 2 |
        
        前14天（第1-14天）：
        - 总涨幅 = 15元
        - 总跌幅 = 6元
        - 平均涨幅 = 15 / 14 = 1.07
        - 平均跌幅 = 6 / 14 = 0.43
        
        第14天RSI = 100 × 1.07 / (1.07 + 0.43) = **71.3**（接近超买）
        
        第15天（今日跌幅2元）：
        - 新平均涨幅 = (15 - 2 + 0) / 14 = 0.93（注意：这里要减去第1天的涨幅）
        - 新平均跌幅 = (6 - 0 + 2) / 14 = 0.57
        - 第15天RSI = 100 × 0.93 / (0.93 + 0.57) = **62.0**
        
        RSI从71.3下降到62.0，说明上涨动能有所减弱。
        """,
        'interpretation': """
        ### RSI实战解读
        
        #### 1️⃣ 超买超卖区间
        
        **传统划分（日线级别）**：
        
        | RSI值 | 状态 | 市场含义 | 操作建议 |
        |-------|------|---------|---------|
        | 80-100 | 严重超买 | 买方力量耗尽，回调风险大 | 🔴 减仓/卖出 |
        | 70-80 | 轻度超买 | 买方力量较强，警惕回调 | 🟡 持有观望 |
        | 50-70 | 多头优势 | 买方占优，趋势向上 | 🟢 逢低买入 |
        | 50 | 多空平衡 | 买卖双方力量均衡 | ⚪ 观望 |
        | 30-50 | 空头优势 | 卖方占优，趋势向下 | 🟠 减仓/观望 |
        | 20-30 | 轻度超卖 | 卖方力量较强，可能反弹 | 🟡 关注买入 |
        | 0-20 | 严重超卖 | 卖方力量耗尽，反弹概率大 | 🟢 积极买入 |
        
        **不同周期的调整**：
        - 日线：用70/30作为界限
        - 周线：用75/25作为界限（更严格）
        - 60分钟线：用65/35作为界限（更宽松）
        
        #### 2️⃣ RSI的50分界线
        
        **RSI > 50**：
        - 平均涨幅 > 平均跌幅，买方力量更强
        - 股价在N日平均线上方运行
        - RSI数值越大，买方优势越明显
        
        **RSI < 50**：
        - 平均跌幅 > 平均涨幅，卖方力量更强
        - 股价在N日平均线下方运行
        - RSI数值越小，卖方优势越明显
        
        **50附近的RSI**：
        - RSI在45-55之间震荡：趋势不明，观望为主
        - RSI从下方突破50：可能转多，关注买入机会
        - RSI从上方跌破50：可能转空，考虑减仓
        
        #### 3️⃣ RSI的趋势线应用
        
        **RSI趋势线**：在RSI曲线上画趋势线，突破时往往领先价格突破
        
        **实战技巧**：
        - 股价创新高，RSI未创新高 → 顶背离，警惕下跌
        - 股价创新低，RSI未创新低 → 底背离，关注反弹
        - RSI突破下降趋势线 → 价格可能即将上涨
        - RSI跌破上升趋势线 → 价格可能即将下跌
        """,
        'examples': """
        ### RSI实战案例分析
        
        **案例1：超卖买入法**
        
        背景：光伏ETF（515790）连续下跌后出现反弹机会
        
        **时间线**：
        - 第1天：价格1.20元，RSI6=45，RSI12=50（正常）
        - 第5天：价格1.10元，RSI6=25，RSI12=35（进入超卖）
        - 第8天：价格1.05元，RSI6=18，RSI12=28（严重超卖）
        - 第10天：价格1.03元，RSI6=15，RSI12=25（极度超卖）
        - 第12天：价格1.08元，RSI6=35，RSI12=32（RSI开始回升）
        
        **分析过程**：
        1. 第8天RSI12接近28，进入超卖区，开始关注
        2. 第10天RSI6跌至15，极度超卖，但此时不宜抄底（恐慌情绪未释放完）
        3. 第12天RSI从低位回升，说明买方开始入场
        4. 确认信号：
           - RSI6上穿RSI12（短周期上穿长周期）
           - 成交量较前几日放大
           - 出现止跌K线形态（如锤子线）
        5. **买入点**：第12天收盘价1.08元
        6. **止损位**：跌破前期低点1.03元
        7. **目标位**：RSI回到50上方，或价格达到1.15元
        
        **结果**：随后2周内价格上涨至1.18元，获利约10%
        
        **案例2：顶背离卖出法**
        
        背景：某消费股经过长期上涨后
        
        **背离识别**：
        | 时间 | 价格 | RSI12 | 说明 |
        |-----|------|-------|------|
        | 1月 | 80元 | 75 | 第一个高点 |
        | 3月 | 85元 | 72 | 第二个高点，RSI下降 |
        | 5月 | 92元 | 68 | 第三个高点，RSI继续下降 |
        
        **顶背离判断**：
        1. 股价三次创新高（80→85→92）
        2. RSI三次降低（75→72→68）
        3. 形成明显的顶背离
        4. 上涨动能衰竭，风险累积
        
        **卖出策略**：
        - 5月RSI从68跌破60时，卖出30%
        - RSI跌破50时，再卖出30%
        - RSI跌破40（确认空头），清仓剩余40%
        
        **结果**：该股票随后3个月下跌35%
        """,
        'common_mistakes': """
        ### RSI使用误区
        
        1. **超买一定跌，超卖一定涨**
           - 强势牛市中，RSI可以长期维持在70以上
           - 恐慌熊市中，RSI可以长期维持在30以下
           - **对策**：结合趋势判断，趋势强时超买可继续持有
        
        2. **只看RSI不看价格**
           - RSI只是辅助指标，价格才是根本
           - RSI可以钝化，但价格始终在反映市场
           - **原则**：价格第一，RSI第二
        
        3. **单一周期决策**
           - 只用RSI6做决策，信号太频繁
           - 建议同时参考RSI6、RSI12、RSI24
           - **方法**：多周期共振（如RSI6和RSI12都超卖）更可靠
        
        4. **在趋势行情中反向操作**
           - 牛市中RSI到70就卖出，容易错过主升浪
           - 熊市中RSI到30就买入，容易被套
           - **解决**：趋势行情用趋势指标，震荡行情用RSI
        """
    },
    'KDJ': {
        'title': '🎲 KDJ指标 - 短线交易神器',
        'intro': """
        ## 什么是KDJ？
        
        KDJ（随机指标，Stochastic Oscillator）由George Lane于1950年代提出，
        是判断价格动量和超买超卖的重要指标，特别适合短线交易。
        
        **KDJ vs RSI**：
        - RSI只看收盘价，KDJ看最高价、最低价、收盘价，更全面
        - RSI变化较平缓，KDJ更灵敏，信号更多
        - RSI适合中线，KDJ适合短线
        
        **核心优势**：
        - 提前预警价格转折
        - 识别超买超卖更敏感
        - J值提供极端行情预警
        """,
        'calculation': """
        ### KDJ计算公式详解
        
        KDJ由三条线组成：**K线（快线）、D线（慢线）、J线（敏感线）**
        
        #### 第一步：计算RSV（未成熟随机值）
        
        $$RSV = \\frac{当日收盘价 - N日内最低价}{N日内最高价 - N日内最低价} \\times 100$$
        
        **RSV的含义**：
        - RSV = 100：收盘价等于N日最高价，最强
        - RSV = 50：收盘价在N日中间位置
        - RSV = 0：收盘价等于N日最低价，最弱
        
        通常N=9，即计算最近9日的RSV。
        
        #### 第二步：计算K值、D值、J值
        
        **K值**（快速确认线，相当于RSV的3日移动平均）：
        $$K = \\frac{2}{3} \\times 前日K值 + \\frac{1}{3} \\times 当日RSV$$
        
        **D值**（慢速主干线，相当于K的3日移动平均）：
        $$D = \\frac{2}{3} \\times 前日D值 + \\frac{1}{3} \\times 当日K值$$
        
        **J值**（方向敏感线，反映K、D的乖离程度）：
        $$J = 3K - 2D$$
        
        或者等价于：
        $$J = K + 2(K - D)$$
        
        **J值的意义**：
        - J > 100：超买，数值越大超买越严重
        - J < 0：超卖，数值越小超卖越严重
        - J是KDJ中最敏感的线
        
        #### 实战计算示例
        
        假设某股票最近9天数据：
        - 9日最高价：50元
        - 9日最低价：40元
        - 今日收盘价：48元
        - 前日K值：60
        - 前日D值：55
        
        **计算过程**：
        1. **RSV** = (48 - 40) / (50 - 40) × 100 = 8/10 × 100 = **80**
           - 说明收盘价处于9日区间的80%位置，偏强
        
        2. **K值** = 2/3 × 60 + 1/3 × 80 = 40 + 26.67 = **66.67**
           - K值向RSV靠拢，但比RSV平滑
        
        3. **D值** = 2/3 × 55 + 1/3 × 66.67 = 36.67 + 22.22 = **58.89**
           - D值向K值靠拢，比K值更平滑
        
        4. **J值** = 3 × 66.67 - 2 × 58.89 = 200.01 - 117.78 = **82.23**
           - J值 > 80，进入超买区
        
        **解读**：该股处于相对强势，但J值显示接近超买，短线可能回调。
        """,
        'interpretation': """
        ### KDJ实战解读
        
        #### 1️⃣ KDJ的区间划分
        
        | 区域 | K值范围 | D值范围 | J值范围 | 市场状态 | 操作建议 |
        |-----|---------|---------|---------|---------|---------|
        | 严重超买 | >80 | >80 | >100 | 极度强势，随时回调 | 🔴 坚决卖出 |
        | 轻度超买 | 70-80 | 70-80 | 80-100 | 强势，需警惕 | 🟡 减仓观望 |
        | 强势区 | 50-70 | 50-70 | 50-80 | 多头市场 | 🟢 持有或逢低买 |
        | 多空平衡 | 40-60 | 40-60 | 40-60 | 震荡整理 | ⚪ 观望 |
        | 弱势区 | 30-50 | 30-50 | 20-50 | 空头市场 | 🟠 减仓或观望 |
        | 轻度超卖 | 20-30 | 20-30 | 0-20 | 弱势，可能反弹 | 🟡 关注买入 |
        | 严重超卖 | <20 | <20 | <0 | 极度弱势，随时反弹 | 🟢 积极买入 |
        
        #### 2️⃣ 金叉与死叉详解
        
        **金叉类型（买入信号）**：
        
        | 类型 | 条件 | 强度 | 说明 |
        |-----|------|------|------|
        | 🏆 低位二次金叉 | K、D都在20以下，第二次金叉 | ⭐⭐⭐⭐⭐ | 最可靠的买入信号 |
        | 🥇 低位金叉 | K、D都在20以下，首次金叉 | ⭐⭐⭐⭐ | 较强的买入信号 |
        | 🥈 中位金叉 | K、D在50附近金叉 | ⭐⭐⭐ | 震荡市中的买入信号 |
        | 🥉 高位金叉 | K、D都在80以上金叉 | ⭐⭐ | 可能是多头陷阱，谨慎 |
        
        **死叉类型（卖出信号）**：
        
        | 类型 | 条件 | 危险度 | 说明 |
        |-----|------|--------|------|
        | 🔥 高位二次死叉 | K、D都在80以上，第二次死叉 | ⭐⭐⭐⭐⭐ | 最危险的信号，立即卖出 |
        | ⚠️ 高位死叉 | K、D都在80以上，首次死叉 | ⭐⭐⭐⭐ | 较强的卖出信号 |
        | 📉 中位死叉 | K、D在50附近死叉 | ⭐⭐⭐ | 可能开启下跌 |
        | 📊 低位死叉 | K、D都在20以下死叉 | ⭐⭐ | 可能是空头陷阱，观望 |
        
        #### 3️⃣ J值的特殊用法
        
        **J值 > 100**：
        - 严重超买，股价可能随时回调
        - J值越大，超买越严重
        - J值连续多日 > 100，风险极高
        - **策略**：逐步减仓，不追涨
        
        **J值 < 0**：
        - 严重超卖，股价可能随时反弹
        - J值越小（负得越多），超卖越严重
        - J值连续多日 < 0，反弹概率大
        - **策略**：逐步建仓，不杀跌
        
        **J值的转向**：
        - J值从 >100 向下转折：短线见顶信号
        - J值从 <0 向上转折：短线见底信号
        - J值在50附近金叉：趋势转强信号
        """,
        'examples': """
        ### KDJ实战案例分析
        
        **案例1：低位二次金叉买入**
        
        背景：化工ETF（159870）经历一波下跌后筑底
        
        **时间线数据**：
        | 日期 | 价格 | K | D | J | 说明 |
        |-----|------|---|---|---|------|
        | Day1 | 0.85 | 15 | 20 | 5 | 严重超卖 |
        | Day3 | 0.82 | 10 | 15 | 0 | 超卖加剧 |
        | Day5 | 0.80 | 18 | 16 | 22 | **首次金叉**（K上穿D） |
        | Day7 | 0.83 | 35 | 25 | 55 | 金叉后上涨 |
        | Day10 | 0.81 | 25 | 28 | 19 | 短暂回调 |
        | Day12 | 0.84 | 30 | 26 | 38 | **二次金叉** |
        | Day15 | 0.90 | 65 | 50 | 95 | 大幅上涨 |
        
        **分析逻辑**：
        1. Day1-Day3：KDJ都在20以下，严重超卖区，开始关注
        2. Day5：首次金叉，但可靠性一般（可能反弹后继续跌）
        3. Day10-Day12：二次金叉！这是经典的**低位二次金叉**形态
        4. 二次金叉特点：
           - K、D值都在20-30之间，处于低位
           - 第二次金叉比第一次更可靠
           - 说明底部夯实，上涨概率大
        5. **买入点**：Day12收盘价0.84
        6. **止损点**：跌破前低0.80
        7. **目标位**：J值达到80-100区域
        
        **结果**：15个交易日后价格上涨至0.90，获利7%
        
        **案例2：J值极端值逃顶抄底**
        
        **逃顶案例**：
        某科技股连续上涨，KDJ显示：
        - 第1天：K=85, D=80, J=95（超买，但还能涨）
        - 第3天：K=90, D=85, J=100（严重超买）
        - 第5天：K=88, D=87, J=90（J值开始下降）
        - 第6天：K=82, D=85, J=76（J值快速下降，K下穿D死叉）
        
        **卖出决策**：
        1. J值达到100后开始下降 → 警惕
        2. K线下穿D线形成死叉 → 卖出50%
        3. 跌破5日均线 → 清仓剩余50%
        
        **结果**：成功逃顶，随后股价下跌20%
        
        **抄底案例**：
        某医药股连续下跌：
        - 第1天：K=25, D=30, J=15（接近超卖）
        - 第3天：K=15, D=20, J=5（严重超卖）
        - 第5天：K=10, D=15, J=-5（J值负值，极度超卖）
        - 第7天：K=20, D=16, J=28（J值转正，K上穿D金叉）
        
        **买入决策**：
        1. J值负值 → 开始关注
        2. J值转正且金叉 → 买入30%
        3. 放量突破5日均线 → 加仓至70%
        
        **结果**：成功抄底，随后反弹15%
        """,
        'common_mistakes': """
        ### KDJ使用误区
        
        1. **金叉就买，死叉就卖**
           - KDJ非常灵敏，会产生大量假信号
           - 震荡市中频繁交易导致亏损
           - **解决**：高位死叉才卖，低位金叉才买，中位观望
        
        2. **忽视J值的极端值**
           - J值>100或<0时信号最强
           - 普通金叉死叉不如J值极端值可靠
           - **技巧**：等J值到极端区域后再操作
        
        3. **单一KDJ决策**
           - KDJ适合短线，中线需配合MACD
           - KDJ在单边趋势中会过早给出反向信号
           - **建议**：KDJ定买卖点，MACD定方向
        
        4. **参数设置不当**
           - 默认参数(9,3,3)适合日线
           - 60分钟线应调整为(18,3,3)减少假信号
           - 周线可调整为(5,3,3)提高灵敏度
        """
    }
}

# ============== 页面主函数 ==============

I18N_BASIC = {
    'zh': {
        'title': '📈 个股分析',
        'select_stock': '选择股票',
        'time_range': '时间范围',
        'days': '{}天',
        'latest_price': '最新价',
        'change': '涨跌幅',
        'volume': '成交量',
        'high_52w': '52周最高',
        'low_52w': '52周最低',
        'kline': 'K线图',
        'trend_analysis': '趋势分析',
        'technical_indicators': '技术指标',
        'risk_metrics': '风险指标',
        'valuation_analysis': '💎 估值分析',
        'indicator_learning': '📚 指标实战教学',
        'direction': '趋势方向',
        'strength': '趋势强度',
        'duration': '持续天数',
        'support': '支撑位',
        'resistance': '阻力位',
        'annual_return': '年化收益',
        'volatility': '波动率',
        'max_dd': '最大回撤',
        'sharpe': '夏普比率',
        'signal': '交易信号',
        'analysis': '分析解读',
        'suggestion': '操作建议',
        'comprehensive': '综合分析',
        'ma_analysis': '均线系统',
        'macd_analysis': 'MACD指标',
        'rsi_analysis': 'RSI指标',
        'kdj_analysis': 'KDJ指标',
        'indicator_value': '指标数值',
        'market_state': '市场状态',
        'no_signal': '暂无明确信号',
        'no_indicators': '暂无技术指标数据，请在股票查询页面重新获取数据',
        # 估值分析相关
        'pe_ttm': 'PE(TTM)',
        'pe_lyr': 'PE(静态)',
        'pb': '市净率PB',
        'ps': '市销率PS',
        'peg': 'PEG',
        'roe': '净资产收益率ROE',
        'dividend_yield': '股息率',
        'pe_percentile': 'PE历史分位',
        'pb_percentile': 'PB历史分位',
        'industry_comparison': '行业对比',
        'valuation_level': '估值水平',
        'fair_value': '合理价值区间',
        'investment_suggestion': '投资建议',
        'confidence': '置信度',
        'risk_factors': '⚠️ 风险因素',
        'opportunities': '✅ 投资机会',
        'technical_alignment': '估值与技术契合度',
        'no_valuation_data': '暂无估值数据（ETF基金或数据获取失败）',
        'extremely_low': '极度低估',
        'low': '低估',
        'reasonable_low': '合理偏低',
        'reasonable': '合理',
        'reasonable_high': '合理偏高',
        'high': '高估',
        'extremely_high': '极度高估',
        'strong_buy': '强烈买入',
        'buy': '建议买入',
        'accumulate': '逢低吸纳',
        'hold': '持有观望',
        'reduce': '减仓观望',
        'sell': '建议卖出',
        'strong_sell': '强烈卖出',
        'high_confidence': '高',
        'medium_confidence': '中',
        'low_confidence': '低',
    },
    'en': {
        'title': '📈 Stock Viewer',
        'select_stock': 'Select Stock',
        'time_range': 'Time Range',
        'days': '{} days',
        'latest_price': 'Latest Price',
        'change': 'Change',
        'volume': 'Volume',
        'high_52w': '52W High',
        'low_52w': '52W Low',
        'kline': 'Candlestick Chart',
        'trend_analysis': 'Trend Analysis',
        'technical_indicators': 'Technical Indicators',
        'risk_metrics': 'Risk Metrics',
        'valuation_analysis': '💎 Valuation Analysis',
        'indicator_learning': '📚 Indicator Guide',
        'direction': 'Direction',
        'strength': 'Strength',
        'duration': 'Duration',
        'support': 'Support',
        'resistance': 'Resistance',
        'annual_return': 'Annual Return',
        'volatility': 'Volatility',
        'max_dd': 'Max Drawdown',
        'sharpe': 'Sharpe Ratio',
        'signal': 'Signal',
        'analysis': 'Analysis',
        'suggestion': 'Suggestion',
        'comprehensive': 'Comprehensive',
        'ma_analysis': 'Moving Average',
        'macd_analysis': 'MACD',
        'rsi_analysis': 'RSI',
        'kdj_analysis': 'KDJ',
        'indicator_value': 'Value',
        'market_state': 'Market State',
        'no_signal': 'No clear signal',
        'no_indicators': 'No technical indicators available',
        # 估值分析相关
        'pe_ttm': 'PE(TTM)',
        'pe_lyr': 'PE(LYR)',
        'pb': 'PB',
        'ps': 'PS',
        'peg': 'PEG',
        'roe': 'ROE',
        'dividend_yield': 'Dividend Yield',
        'pe_percentile': 'PE Percentile',
        'pb_percentile': 'PB Percentile',
        'industry_comparison': 'Industry Comparison',
        'valuation_level': 'Valuation Level',
        'fair_value': 'Fair Value Range',
        'investment_suggestion': 'Investment Suggestion',
        'confidence': 'Confidence',
        'risk_factors': '⚠️ Risk Factors',
        'opportunities': '✅ Opportunities',
        'technical_alignment': 'Valuation-Technical Alignment',
        'no_valuation_data': 'No valuation data available',
        'extremely_low': 'Extremely Low',
        'low': 'Low',
        'reasonable_low': 'Reasonably Low',
        'reasonable': 'Reasonable',
        'reasonable_high': 'Reasonably High',
        'high': 'High',
        'extremely_high': 'Extremely High',
        'strong_buy': 'Strong Buy',
        'buy': 'Buy',
        'accumulate': 'Accumulate',
        'hold': 'Hold',
        'reduce': 'Reduce',
        'sell': 'Sell',
        'strong_sell': 'Strong Sell',
        'high_confidence': 'High',
        'medium_confidence': 'Medium',
        'low_confidence': 'Low',
    }
}

def analyze_ma_safe(price, ma5, ma20, ma60):
    """分析均线系统 - 安全版本"""
    signals = []
    analysis = []
    
    # 转换为float
    price = float(price) if price else 0
    ma5 = float(ma5) if ma5 else 0
    ma20 = float(ma20) if ma20 else 0
    ma60 = float(ma60) if ma60 else 0
    
    if not all([ma5 > 0, ma20 > 0, ma60 > 0]):
        return [], ["数据不足，无法分析"]
    
    # 多头排列 / 空头排列
    if ma5 > ma20 > ma60:
        signals.append(("🟢 多头排列", "强势上涨"))
        analysis.append("短期、中期、长期均线呈多头排列，上升趋势强劲")
    elif ma5 < ma20 < ma60:
        signals.append(("🔴 空头排列", "弱势下跌"))
        analysis.append("短期、中期、长期均线呈空头排列，下降趋势明显")
    else:
        signals.append(("🟡 震荡整理", "趋势不明"))
        analysis.append("均线交织，市场处于震荡整理阶段")
    
    # 金叉 / 死叉
    if ma5 > ma20 and ma5 <= ma20 * 1.02:
        signals.append(("🟢 金叉信号", "买入机会"))
        analysis.append("短期均线上穿中期均线，形成金叉，可能是买入时机")
    elif ma5 < ma20 and ma5 >= ma20 * 0.98:
        signals.append(("🔴 死叉信号", "卖出警示"))
        analysis.append("短期均线下穿中期均线，形成死叉，注意风险")
    
    # 价格与均线关系
    if price > ma5:
        analysis.append(f"股价({price:.3f})高于MA5({ma5:.3f})，短期强势")
    else:
        analysis.append(f"股价({price:.3f})低于MA5({ma5:.3f})，短期弱势")
    
    return signals, analysis

def analyze_macd_safe(dif, dea, macd_bar=None):
    """分析MACD指标 - 安全版本"""
    signals = []
    analysis = []
    
    dif = float(dif) if dif else 0
    dea = float(dea) if dea else 0
    
    if not all([dif, dea]):
        return [], ["数据不足"]
    
    # 零轴判断
    if dif > 0 and dea > 0:
        analysis.append("DIF和DEA均在零轴上方，处于多头市场")
    elif dif < 0 and dea < 0:
        analysis.append("DIF和DEA均在零轴下方，处于空头市场")
    else:
        analysis.append("指标在零轴附近，市场方向不明")
    
    # 金叉 / 死叉
    if dif > dea and abs(dif - dea) < 0.05:
        signals.append(("🟢 MACD金叉", "买入信号"))
        analysis.append("DIF上穿DEA形成金叉，买入信号")
    elif dif < dea and abs(dif - dea) < 0.05:
        signals.append(("🔴 MACD死叉", "卖出信号"))
        analysis.append("DIF下穿DEA形成死叉，卖出信号")
    
    return signals, analysis

def analyze_rsi_safe(rsi):
    """分析RSI指标 - 安全版本"""
    signals = []
    analysis = []
    
    rsi = float(rsi) if rsi else 0
    
    if not rsi:
        return [], ["数据不足"]
    
    # 超买超卖
    if rsi > 80:
        signals.append(("🔴 严重超买", "强烈卖出"))
        analysis.append(f"RSI={rsi:.2f}>80，严重超买，建议减仓或卖出")
    elif rsi > 70:
        signals.append(("🟡 超买区域", "谨慎持有"))
        analysis.append(f"RSI={rsi:.2f}>70，进入超买区域，注意回调风险")
    elif rsi < 20:
        signals.append(("🟢 严重超卖", "强烈买入"))
        analysis.append(f"RSI={rsi:.2f}<20，严重超卖，可能是买入机会")
    elif rsi < 30:
        signals.append(("🟢 超卖区域", "关注买入"))
        analysis.append(f"RSI={rsi:.2f}<30，进入超卖区域，可关注买入机会")
    else:
        analysis.append(f"RSI={rsi:.2f}处于正常区间(30-70)，趋势健康")
    
    return signals, analysis

def analyze_kdj_safe(k, d, j=None):
    """分析KDJ指标 - 安全版本"""
    signals = []
    analysis = []
    
    k = float(k) if k else 0
    d = float(d) if d else 0
    j = float(j) if j else 0
    
    if not all([k, d]):
        return [], ["数据不足"]
    
    # 金叉 / 死叉
    if k > d and abs(k - d) < 5:
        signals.append(("🟢 KDJ金叉", "买入信号"))
        analysis.append("K值上穿D值形成金叉，短线买入信号")
    elif k < d and abs(k - d) < 5:
        signals.append(("🔴 KDJ死叉", "卖出信号"))
        analysis.append("K值下穿D值形成死叉，短线卖出信号")
    
    # 超买超卖
    if k > 80 and d > 80:
        signals.append(("🔴 KDJ超买", "高位风险"))
        analysis.append(f"K={k:.2f}, D={d:.2f}均大于80，严重超买，注意回调")
    elif k < 20 and d < 20:
        signals.append(("🟢 KDJ超卖", "低位机会"))
        analysis.append(f"K={k:.2f}, D={d:.2f}均小于20，严重超卖，可能反弹")
    else:
        analysis.append(f"KDJ处于正常区间(K={k:.2f}, D={d:.2f})")
    
    return signals, analysis

lang = st.session_state.get('lang', 'zh')
t = lambda k: I18N_BASIC[lang].get(k, k)

st.title(t('title'))

SessionLocal = get_session_factory()
db = SessionLocal()

try:
    stocks = db.query(Stock).order_by(Stock.stock_code).all()
    if not stocks:
        st.info("数据库中没有股票，请从股票查询页面添加。")
        st.stop()
    
    stock_options = [f"{s.stock_code} - {s.stock_name}" for s in stocks]
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected = st.selectbox(t('select_stock'), options=stock_options)
        stock_code = selected.split(" - ")[0]
    
    with col2:
        days = st.selectbox(t('time_range'), options=[60, 120, 252, 500], format_func=lambda x: t('days').format(x))
    
    # 加载数据 - 确保所有数值都是float
    prices = db.query(DailyPrice).filter(
        DailyPrice.stock_code == stock_code
    ).order_by(DailyPrice.trade_date.desc()).limit(days).all()
    
    if not prices:
        st.error(f"No data for {stock_code}")
        st.stop()
    
    df = pd.DataFrame([{
        'trade_date': p.trade_date,
        'open_price': float(p.open_price) if p.open_price else 0.0,
        'high_price': float(p.high_price) if p.high_price else 0.0,
        'low_price': float(p.low_price) if p.low_price else 0.0,
        'close_price': float(p.close_price) if p.close_price else 0.0,
        'volume': float(p.volume) if p.volume else 0.0,
        'change_pct': float(p.change_pct) if p.change_pct else 0.0,
    } for p in reversed(prices)])
    
    latest = df.iloc[-1]
    
    # 基本信息
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(t('latest_price'), f"{latest['close_price']:.3f}", f"{latest['change_pct']:.2f}%")
    c2.metric(t('change'), f"{latest['change_pct']:+.2f}%")
    c3.metric(t('volume'), f"{latest['volume']/10000:.0f}万")
    c4.metric(t('high_52w'), f"{df['high_price'].max():.3f}")
    c5.metric(t('low_52w'), f"{df['low_price'].min():.3f}")
    
    # K线图
    st.subheader(t('kline'))
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(
        x=df['trade_date'],
        open=df['open_price'],
        high=df['high_price'],
        low=df['low_price'],
        close=df['close_price']
    ), row=1, col=1)
    colors = ['red' if df.iloc[i]['close_price'] >= df.iloc[i]['open_price'] else 'green' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df['trade_date'], y=df['volume'], marker_color=colors), row=2, col=1)
    fig.update_layout(height=600, showlegend=False, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # 分析和指标
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        t('trend_analysis'), 
        t('technical_indicators'), 
        t('risk_metrics'), 
        t('valuation_analysis'),
        t('indicator_learning')
    ])
    
    with tab1:
        try:
            analyzer = TrendAnalyzer(df)
            result = analyzer.analyze()
            
            col1, col2, col3 = st.columns(3)
            col1.metric(t('direction'), result.direction.value)
            col2.metric(t('strength'), result.strength.value)
            col3.metric(t('duration'), f"{result.trend_days} days")
            
            st.info(result.description)
            
            if result.support_levels:
                st.markdown(f"**{t('support')}:** {', '.join([f'{float(s):.3f}' for s in result.support_levels[:3]])}")
            if result.resistance_levels:
                st.markdown(f"**{t('resistance')}:** {', '.join([f'{float(r):.3f}' for r in result.resistance_levels[:3]])}")
        except Exception as e:
            st.error(f"分析出错: {e}")
    
    with tab2:
        indicators = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_code == stock_code
        ).order_by(TechnicalIndicator.trade_date.desc()).first()
        
        if indicators:
            current_price = float(latest['close_price'])
            
            # MA分析
            st.subheader(t('ma_analysis'))
            ma_signals, ma_analysis = analyze_ma_safe(
                current_price, 
                indicators.ma5, 
                indicators.ma20, 
                indicators.ma60
            )
            
            col1, col2, col3 = st.columns([2, 3, 3])
            with col1:
                st.markdown(f"**{t('indicator_value')}**")
                ma5_val = float(indicators.ma5) if indicators.ma5 else 0
                ma20_val = float(indicators.ma20) if indicators.ma20 else 0
                ma60_val = float(indicators.ma60) if indicators.ma60 else 0
                st.write(f"MA5: {ma5_val:.3f}" if ma5_val else "MA5: -")
                st.write(f"MA20: {ma20_val:.3f}" if ma20_val else "MA20: -")
                st.write(f"MA60: {ma60_val:.3f}" if ma60_val else "MA60: -")
            
            with col2:
                st.markdown(f"**{t('signal')}**")
                if ma_signals:
                    for signal, desc in ma_signals:
                        st.write(f"{signal}")
                else:
                    st.write(t('no_signal'))
            
            with col3:
                st.markdown(f"**{t('analysis')}**")
                for analysis in ma_analysis:
                    st.write(f"• {analysis}")
            
            # MACD分析
            st.subheader(t('macd_analysis'))
            macd_signals, macd_analysis = analyze_macd_safe(
                indicators.macd_dif,
                indicators.macd_dea,
                indicators.macd_bar
            )
            
            col1, col2, col3 = st.columns([2, 3, 3])
            with col1:
                st.markdown(f"**{t('indicator_value')}**")
                dif_val = float(indicators.macd_dif) if indicators.macd_dif else 0
                dea_val = float(indicators.macd_dea) if indicators.macd_dea else 0
                bar_val = float(indicators.macd_bar) if indicators.macd_bar else 0
                st.write(f"DIF: {dif_val:.4f}" if dif_val else "DIF: -")
                st.write(f"DEA: {dea_val:.4f}" if dea_val else "DEA: -")
                st.write(f"BAR: {bar_val:.4f}" if bar_val else "BAR: -")
            
            with col2:
                st.markdown(f"**{t('signal')}**")
                if macd_signals:
                    for signal, desc in macd_signals:
                        st.write(f"{signal}")
                else:
                    st.write(t('no_signal'))
            
            with col3:
                st.markdown(f"**{t('analysis')}**")
                for analysis in macd_analysis:
                    st.write(f"• {analysis}")
            
            # RSI分析
            st.subheader(t('rsi_analysis'))
            rsi_signals, rsi_analysis = analyze_rsi_safe(indicators.rsi12)
            
            col1, col2, col3 = st.columns([2, 3, 3])
            with col1:
                st.markdown(f"**{t('indicator_value')}**")
                rsi6_val = float(indicators.rsi6) if indicators.rsi6 else 0
                rsi12_val = float(indicators.rsi12) if indicators.rsi12 else 0
                rsi24_val = float(indicators.rsi24) if indicators.rsi24 else 0
                st.write(f"RSI6: {rsi6_val:.2f}" if rsi6_val else "RSI6: -")
                st.write(f"RSI12: {rsi12_val:.2f}" if rsi12_val else "RSI12: -")
                st.write(f"RSI24: {rsi24_val:.2f}" if rsi24_val else "RSI24: -")
            
            with col2:
                st.markdown(f"**{t('signal')}**")
                if rsi_signals:
                    for signal, desc in rsi_signals:
                        st.write(f"{signal}")
                else:
                    st.write(t('no_signal'))
            
            with col3:
                st.markdown(f"**{t('analysis')}**")
                for analysis in rsi_analysis:
                    st.write(f"• {analysis}")
            
            # KDJ分析
            st.subheader(t('kdj_analysis'))
            kdj_signals, kdj_analysis = analyze_kdj_safe(
                indicators.k_value,
                indicators.d_value,
                indicators.j_value
            )
            
            col1, col2, col3 = st.columns([2, 3, 3])
            with col1:
                st.markdown(f"**{t('indicator_value')}**")
                k_val = float(indicators.k_value) if indicators.k_value else 0
                d_val = float(indicators.d_value) if indicators.d_value else 0
                j_val = float(indicators.j_value) if indicators.j_value else 0
                st.write(f"K: {k_val:.2f}" if k_val else "K: -")
                st.write(f"D: {d_val:.2f}" if d_val else "D: -")
                st.write(f"J: {j_val:.2f}" if j_val else "J: -")
            
            with col2:
                st.markdown(f"**{t('signal')}**")
                if kdj_signals:
                    for signal, desc in kdj_signals:
                        st.write(f"{signal}")
                else:
                    st.write(t('no_signal'))
            
            with col3:
                st.markdown(f"**{t('analysis')}**")
                for analysis in kdj_analysis:
                    st.write(f"• {analysis}")
            
            # 综合分析
            st.divider()
            st.subheader(t('comprehensive'))
            
            trend_dir = result.direction.value if 'result' in locals() else None
            
            # 统计买卖信号
            buy_count = 0
            sell_count = 0
            for signals in [ma_signals, macd_signals, rsi_signals, kdj_signals]:
                for signal, _ in signals:
                    if "🟢" in signal or "买入" in signal:
                        buy_count += 1
                    elif "🔴" in signal or "卖出" in signal:
                        sell_count += 1
            
            if buy_count >= 3:
                overall_signal, overall_suggestion = "🟢 强烈买入", "多个指标发出买入信号，建议积极做多"
            elif buy_count >= 2:
                overall_signal, overall_suggestion = "🟢 建议买入", "部分指标显示买入机会，可考虑建仓"
            elif sell_count >= 3:
                overall_signal, overall_suggestion = "🔴 强烈卖出", "多个指标发出卖出信号，建议减仓或离场"
            elif sell_count >= 2:
                overall_signal, overall_suggestion = "🔴 建议卖出", "部分指标显示风险，建议谨慎操作"
            else:
                overall_signal, overall_suggestion = "🟡 观望", "指标信号不一致，建议观望等待 clearer signals"
            
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f"### {overall_signal}")
            with col2:
                st.info(f"**{t('suggestion')}:** {overall_suggestion}")
        else:
            st.warning(t('no_indicators'))
    
    with tab3:
        try:
            close_prices = pd.to_numeric(df['close_price'], errors='coerce').astype(float)
            returns = close_prices.pct_change().dropna()
            
            if len(returns) > 30:
                metrics = RiskMetrics(returns)
                result = metrics.calculate_all()
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric(t('annual_return'), f"{float(result.annualized_return)*100:.1f}%")
                col2.metric(t('volatility'), f"{float(result.annualized_volatility)*100:.1f}%")
                col3.metric(t('max_dd'), f"{float(result.max_drawdown)*100:.1f}%")
                col4.metric(t('sharpe'), f"{float(result.sharpe_ratio):.2f}")
                
                st.divider()
                st.subheader("风险指标解读")
                
                sharpe = float(result.sharpe_ratio)
                max_dd = float(result.max_drawdown)
                
                if sharpe > 2:
                    st.success(f"夏普比率 {sharpe:.2f} > 2.0，风险调整后收益优秀")
                elif sharpe > 1:
                    st.info(f"夏普比率 {sharpe:.2f} > 1.0，风险调整后收益良好")
                else:
                    st.warning(f"夏普比率 {sharpe:.2f} < 1.0，风险收益比一般")
                
                if max_dd < 0.1:
                    st.success(f"最大回撤 {max_dd*100:.1f}% < 10%，风险控制优秀")
                elif max_dd < 0.2:
                    st.info(f"最大回撤 {max_dd*100:.1f}% < 20%，风险控制良好")
                else:
                    st.warning(f"最大回撤 {max_dd*100:.1f}% > 20%，波动较大")
            else:
                st.info("数据不足，无法计算风险指标 (需要至少30天数据)")
        except Exception as e:
            st.error(f"风险指标计算出错: {e}")
    
    with tab4:
        # 估值分析模块
        st.subheader(t('valuation_analysis'))
        
        try:
            # 获取当前股票信息
            stock_record = db.query(Stock).filter(Stock.stock_code == stock_code).first()
            stock_name = stock_record.stock_name if stock_record and stock_record.stock_name else stock_code
            
            # 获取当前价格
            current_price = float(latest['close_price'])
            
            # 获取趋势分析结果用于估值分析
            try:
                analyzer = TrendAnalyzer(df)
                trend_result = analyzer.analyze()
                technical_trend = "UP" if "上涨" in trend_result.direction.value or "上升" in trend_result.direction.value else \
                                 "DOWN" if "下跌" in trend_result.direction.value or "下降" in trend_result.direction.value else "SIDEWAYS"
                technical_strength = "STRONG" if "强" in trend_result.strength.value else \
                                    "WEAK" if "弱" in trend_result.strength.value else "MODERATE"
            except Exception:
                technical_trend = "SIDEWAYS"
                technical_strength = "MODERATE"
            
            # 获取估值数据
            with st.spinner("正在获取估值数据..."):
                collector = AKShareCollector()
                valuation_data = collector.get_valuation_metrics(stock_code)
            
            # 显示调试信息（可折叠）
            with st.expander("🔧 调试信息"):
                if valuation_data:
                    st.write("获取到的原始数据:")
                    st.json(valuation_data)
                else:
                    st.warning("未能从数据源获取估值数据")
                    st.info("可能的原因：\n1. 网络连接问题\n2. 该股票暂无估值数据\n3. 数据源暂时不可用")
            
            # 如果无法获取数据，提供手动输入选项或使用估算
            is_estimated = False
            if not valuation_data:
                st.info("无法自动获取估值数据，您可以手动输入或使用价格估算")
                
                # 提供估算选项
                use_estimate = st.checkbox("使用基于价格数据的估算", value=False, key="use_estimate")
                
                if use_estimate:
                    # 使用价格数据估算
                    estimated = collector.estimate_valuation_from_price(stock_code, df)
                    if estimated:
                        valuation_data = estimated
                        is_estimated = True
                        st.success("已使用基于价格数据的估算值（仅供参考）")
                    else:
                        st.error("无法估算估值数据")
                
                # 手动输入
                st.markdown("**或手动输入估值数据：**")
                manual_col1, manual_col2, manual_col3 = st.columns(3)
                with manual_col1:
                    manual_pe = st.number_input("PE(TTM)", min_value=0.0, max_value=1000.0, value=0.0, step=0.1, key="manual_pe")
                with manual_col2:
                    manual_pb = st.number_input("PB", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="manual_pb")
                with manual_col3:
                    manual_roe = st.number_input("ROE(%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="manual_roe")
                
                if st.button("使用手动数据进行分析", key="use_manual"):
                    if manual_pe > 0 or manual_pb > 0:
                        valuation_data = {
                            'pe_ttm': manual_pe if manual_pe > 0 else None,
                            'pb': manual_pb if manual_pb > 0 else None,
                            'roe': manual_roe if manual_roe > 0 else None,
                        }
                        st.success("已使用手动输入的估值数据")
                    else:
                        st.error("请至少输入PE或PB数据")
            
            if valuation_data:
                # 获取历史估值数据用于计算百分位
                historical_pe = None
                historical_pb = None
                try:
                    hist_val = collector.get_historical_valuation(stock_code, days=252)
                    if not hist_val.empty:
                        historical_pe = hist_val.get('pe_ttm')
                        historical_pb = hist_val.get('pb')
                except Exception:
                    pass
                
                # 创建估值分析器
                valuation_analyzer = ValuationAnalyzer(
                    pe_history=historical_pe,
                    pb_history=historical_pb
                )
                
                # 创建估值指标
                metrics = ValuationMetrics(
                    pe_ttm=valuation_data.get('pe_ttm'),
                    pe_lyr=valuation_data.get('pe_lyr'),
                    pb=valuation_data.get('pb'),
                    ps=valuation_data.get('ps'),
                    roe=valuation_data.get('roe'),
                    dividend_yield=valuation_data.get('dividend_yield')
                )
                
                # 执行估值分析
                result = valuation_analyzer.analyze(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    current_price=current_price,
                    metrics=metrics,
                    technical_trend=technical_trend,
                    technical_strength=technical_strength
                )
                
                # 显示估值指标卡片
                st.markdown("### 📊 估值指标")
                
                # 如果是估算数据，显示警告
                if is_estimated or valuation_data.get('is_estimated'):
                    st.warning("⚠️ 当前使用的是基于价格数据的**估算值**，仅供参考。建议从其他渠道获取真实估值数据。")
                
                vcol1, vcol2, vcol3, vcol4 = st.columns(4)
                
                with vcol1:
                    pe_val = result.metrics.pe_ttm
                    if pe_val and not pd.isna(pe_val):
                        st.metric(t('pe_ttm'), f"{pe_val:.2f}")
                    else:
                        st.metric(t('pe_ttm'), "--")
                
                with vcol2:
                    pb_val = result.metrics.pb
                    if pb_val and not pd.isna(pb_val):
                        st.metric(t('pb'), f"{pb_val:.2f}")
                    else:
                        st.metric(t('pb'), "--")
                
                with vcol3:
                    roe_val = result.metrics.roe
                    if roe_val and not pd.isna(roe_val):
                        st.metric(t('roe'), f"{roe_val:.2f}%")
                    else:
                        st.metric(t('roe'), "--")
                
                with vcol4:
                    dy_val = result.metrics.dividend_yield
                    if dy_val and not pd.isna(dy_val):
                        st.metric(t('dividend_yield'), f"{dy_val:.2%}")
                    else:
                        st.metric(t('dividend_yield'), "--")
                
                st.divider()
                
                # 显示估值水平判断
                st.markdown("### 📈 估值水平判断")
                lcol1, lcol2, lcol3 = st.columns(3)
                
                # 估值水平颜色映射
                level_colors = {
                    ValuationLevel.EXTREMELY_LOW: "🟢",
                    ValuationLevel.LOW: "🟢",
                    ValuationLevel.REASONABLE_LOW: "🟡",
                    ValuationLevel.REASONABLE: "⚪",
                    ValuationLevel.REASONABLE_HIGH: "🟠",
                    ValuationLevel.HIGH: "🔴",
                    ValuationLevel.EXTREMELY_HIGH: "🔴",
                    ValuationLevel.UNKNOWN: "⚪"
                }
                
                with lcol1:
                    pe_level_str = result.pe_level.value if lang == 'zh' else result.pe_level.name.replace("_", " ").title()
                    st.metric("PE估值", f"{level_colors[result.pe_level]} {pe_level_str}")
                
                with lcol2:
                    pb_level_str = result.pb_level.value if lang == 'zh' else result.pb_level.name.replace("_", " ").title()
                    st.metric("PB估值", f"{level_colors[result.pb_level]} {pb_level_str}")
                
                with lcol3:
                    overall_str = result.overall_level.value if lang == 'zh' else result.overall_level.name.replace("_", " ").title()
                    st.metric("综合估值", f"{level_colors[result.overall_level]} {overall_str}")
                
                st.divider()
                
                # 显示投资建议
                st.markdown("### 💡 投资建议")
                suggestion_str = result.suggestion.value if lang == 'zh' else result.suggestion.name.replace("_", " ").title()
                confidence_str = t(f"{result.confidence}_confidence".lower())
                
                suggestion_colors = {
                    InvestmentSuggestion.STRONG_BUY: "success",
                    InvestmentSuggestion.BUY: "success",
                    InvestmentSuggestion.ACCUMULATE: "info",
                    InvestmentSuggestion.HOLD: "info",
                    InvestmentSuggestion.REDUCE: "warning",
                    InvestmentSuggestion.SELL: "error",
                    InvestmentSuggestion.STRONG_SELL: "error",
                    InvestmentSuggestion.UNKNOWN: "info"
                }
                
                st.markdown(f"#### **{suggestion_str}** (置信度: {confidence_str})")
                
                # 显示详细分析
                with st.expander("📖 详细估值分析", expanded=True):
                    st.markdown("#### PE分析")
                    st.write(result.pe_analysis)
                    
                    st.markdown("#### PB分析")
                    st.write(result.pb_analysis)
                    
                    st.markdown(f"#### {t('technical_alignment')}")
                    st.write(result.technical_alignment)
                
                # 显示合理价值区间
                if result.fair_value_mid:
                    st.markdown("### 🎯 合理价值区间")
                    fcol1, fcol2, fcol3 = st.columns(3)
                    with fcol1:
                        if result.fair_value_low:
                            upside_low = (result.fair_value_low - current_price) / current_price * 100
                            st.metric("低估区间", f"{result.fair_value_low:.2f}", f"{upside_low:+.1f}%")
                    with fcol2:
                        upside_mid = (result.fair_value_mid - current_price) / current_price * 100
                        st.metric("合理价值", f"{result.fair_value_mid:.2f}", f"{upside_mid:+.1f}%")
                    with fcol3:
                        if result.fair_value_high:
                            upside_high = (result.fair_value_high - current_price) / current_price * 100
                            st.metric("高估区间", f"{result.fair_value_high:.2f}", f"{upside_high:+.1f}%")
                
                # 显示机会和风险
                ocol1, ocol2 = st.columns(2)
                with ocol1:
                    if result.opportunities:
                        st.markdown(f"### {t('opportunities')}")
                        for opp in result.opportunities:
                            st.success(f"✅ {opp}")
                
                with ocol2:
                    if result.risk_factors:
                        st.markdown(f"### {t('risk_factors')}")
                        for risk in result.risk_factors:
                            st.error(f"⚠️ {risk}")
                
                # 估值与技术指标综合报告
                st.divider()
                st.markdown("### 📋 估值-技术综合报告")
                
                # 计算综合评分
                score = 50  # 基础分
                
                # 估值评分
                if result.overall_level in [ValuationLevel.EXTREMELY_LOW, ValuationLevel.LOW]:
                    score += 20
                elif result.overall_level in [ValuationLevel.REASONABLE_LOW]:
                    score += 10
                elif result.overall_level in [ValuationLevel.HIGH, ValuationLevel.EXTREMELY_HIGH]:
                    score -= 20
                elif result.overall_level == ValuationLevel.REASONABLE_HIGH:
                    score -= 10
                
                # 技术趋势评分
                if technical_trend == "UP":
                    score += 15 if technical_strength == "STRONG" else 10
                elif technical_trend == "DOWN":
                    score -= 15 if technical_strength == "STRONG" else 10
                
                # 显示评分
                if score >= 80:
                    st.success(f"综合评分: {score}/100 - 极具投资价值")
                elif score >= 60:
                    st.info(f"综合评分: {score}/100 - 具备投资价值")
                elif score >= 40:
                    st.warning(f"综合评分: {score}/100 - 中性观望")
                else:
                    st.error(f"综合评分: {score}/100 - 投资风险较高")
                
                # 综合建议
                if result.overall_level in [ValuationLevel.EXTREMELY_LOW, ValuationLevel.LOW] and technical_trend == "UP":
                    st.success("🎯 **核心观点**: 估值低估且技术趋势向上，是较好的布局时机。建议分批买入，控制仓位。")
                elif result.overall_level in [ValuationLevel.HIGH, ValuationLevel.EXTREMELY_HIGH] and technical_trend == "DOWN":
                    st.error("🎯 **核心观点**: 估值偏高且技术趋势向下，建议减仓或离场观望。")
                elif result.overall_level in [ValuationLevel.EXTREMELY_LOW, ValuationLevel.LOW] and technical_trend == "DOWN":
                    st.info("🎯 **核心观点**: 估值已处于低位，但技术趋势仍弱，可等待企稳信号后分批建仓。")
                elif result.overall_level in [ValuationLevel.HIGH, ValuationLevel.EXTREMELY_HIGH] and technical_trend == "UP":
                    st.warning("🎯 **核心观点**: 技术趋势仍强但估值偏高，注意止盈，设置好止损位。")
                else:
                    st.info("🎯 **核心观点**: 估值处于合理区间，技术方向不明，建议观望等待更明确信号。")
                
            else:
                st.info(t('no_valuation_data'))
                
        except Exception as e:
            st.error(f"估值分析出错: {e}")
            import traceback
            st.error(traceback.format_exc())
    
    with tab5:
        # 指标学习模块
        st.subheader("📚 选择要学习的指标")
        
        indicator_choice = st.selectbox(
            "选择指标",
            ["均线系统 (MA)", "MACD指标", "RSI指标", "KDJ指标"],
            key='indicator_learning_select'
        )
        
        indicator_key = indicator_choice.split("(")[1].replace(")", "") if "(" in indicator_choice else "MA"
        
        if indicator_key in INDICATOR_GUIDE:
            guide = INDICATOR_GUIDE[indicator_key]
            
            st.markdown(f"# {guide['title']}")
            
            # 使用expander组织内容
            with st.expander("📖 指标简介", expanded=True):
                st.markdown(guide['intro'])
            
            with st.expander("🔢 计算公式与原理"):
                st.markdown(guide['calculation'])
            
            with st.expander("📊 实战解读技巧"):
                st.markdown(guide['interpretation'])
            
            with st.expander("💡 真实案例分析"):
                st.markdown(guide['examples'])
            
            with st.expander("⚠️ 常见误区与注意事项"):
                st.markdown(guide['common_mistakes'])

except Exception as e:
    st.error(f"错误: {e}")
    import traceback
    st.error(traceback.format_exc())
finally:
    db.close()
