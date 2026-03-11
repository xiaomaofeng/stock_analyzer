# -*- coding: utf-8 -*-
"""
估值分析模块 - 结合技术指标的综合估值分析
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class ValuationLevel(Enum):
    """估值水平"""
    EXTREMELY_LOW = "极度低估"
    LOW = "低估"
    REASONABLE_LOW = "合理偏低"
    REASONABLE = "合理"
    REASONABLE_HIGH = "合理偏高"
    HIGH = "高估"
    EXTREMELY_HIGH = "极度高估"
    UNKNOWN = "未知"


class InvestmentSuggestion(Enum):
    """投资建议"""
    STRONG_BUY = "强烈买入"
    BUY = "建议买入"
    ACCUMULATE = "逢低吸纳"
    HOLD = "持有观望"
    REDUCE = "减仓观望"
    SELL = "建议卖出"
    STRONG_SELL = "强烈卖出"
    UNKNOWN = "数据不足"


@dataclass
class ValuationMetrics:
    """估值指标数据类"""
    # 基础估值指标
    pe_ttm: Optional[float] = None  # 滚动市盈率
    pe_lyr: Optional[float] = None  # 静态市盈率
    pb: Optional[float] = None  # 市净率
    ps: Optional[float] = None  # 市销率
    pcf: Optional[float] = None  # 市现率
    
    # 衍生指标
    peg: Optional[float] = None  # PEG比率
    roe: Optional[float] = None  # 净资产收益率
    dividend_yield: Optional[float] = None  # 股息率
    
    # 历史百分位
    pe_percentile: Optional[float] = None  # PE历史百分位
    pb_percentile: Optional[float] = None  # PB历史百分位
    
    # 行业对比
    industry_pe: Optional[float] = None  # 行业平均PE
    industry_pb: Optional[float] = None  # 行业平均PB
    pe_vs_industry: Optional[float] = None  # PE相对行业比例
    pb_vs_industry: Optional[float] = None  # PB相对行业比例


@dataclass
class ValuationResult:
    """估值分析结果"""
    stock_code: str
    stock_name: str
    analysis_date: datetime
    
    # 估值指标
    metrics: ValuationMetrics
    
    # 估值水平判断
    pe_level: ValuationLevel
    pb_level: ValuationLevel
    overall_level: ValuationLevel
    
    # 投资建议
    suggestion: InvestmentSuggestion
    confidence: str  # 置信度：高/中/低
    
    # 详细分析
    pe_analysis: str
    pb_analysis: str
    technical_alignment: str  # 与技术指标的契合度分析
    
    # 风险提示
    risk_factors: List[str]
    opportunities: List[str]
    
    # 目标价区间（基于估值）
    fair_value_low: Optional[float] = None
    fair_value_mid: Optional[float] = None
    fair_value_high: Optional[float] = None


class ValuationAnalyzer:
    """估值分析器 - 结合技术指标的综合估值分析"""
    
    # 估值区间定义（可根据市场调整）
    PE_RANGES = {
        ValuationLevel.EXTREMELY_LOW: (0, 10),
        ValuationLevel.LOW: (10, 15),
        ValuationLevel.REASONABLE_LOW: (15, 20),
        ValuationLevel.REASONABLE: (20, 30),
        ValuationLevel.REASONABLE_HIGH: (30, 40),
        ValuationLevel.HIGH: (40, 60),
        ValuationLevel.EXTREMELY_HIGH: (60, float('inf')),
    }
    
    PB_RANGES = {
        ValuationLevel.EXTREMELY_LOW: (0, 1),
        ValuationLevel.LOW: (1, 1.5),
        ValuationLevel.REASONABLE_LOW: (1.5, 2),
        ValuationLevel.REASONABLE: (2, 3),
        ValuationLevel.REASONABLE_HIGH: (3, 4),
        ValuationLevel.HIGH: (4, 6),
        ValuationLevel.EXTREMELY_HIGH: (6, float('inf')),
    }
    
    def __init__(self, pe_history: Optional[pd.Series] = None, pb_history: Optional[pd.Series] = None):
        """
        初始化估值分析器
        
        Args:
            pe_history: 历史PE数据序列，用于计算百分位
            pb_history: 历史PB数据序列，用于计算百分位
        """
        self.pe_history = pe_history
        self.pb_history = pb_history
    
    def calculate_percentile(self, current_value: float, history: pd.Series) -> float:
        """计算历史百分位"""
        if history is None or history.empty or pd.isna(current_value):
            return 50.0
        # 过滤有效值
        valid_history = history.dropna()
        if len(valid_history) < 30:  # 需要至少30个数据点
            return 50.0
        return (valid_history < current_value).mean() * 100
    
    def get_valuation_level(self, value: float, ranges: Dict) -> ValuationLevel:
        """根据数值判断估值水平"""
        if pd.isna(value) or value <= 0:
            return ValuationLevel.UNKNOWN
        for level, (low, high) in ranges.items():
            if low <= value < high:
                return level
        return ValuationLevel.UNKNOWN
    
    def calculate_peg(self, pe: float, growth_rate: float) -> float:
        """计算PEG比率"""
        if pd.isna(pe) or pd.isna(growth_rate) or growth_rate <= 0:
            return float('inf')
        return pe / growth_rate
    
    def analyze_pe(self, pe: float, pe_percentile: float, industry_pe: Optional[float] = None) -> Tuple[ValuationLevel, str]:
        """
        分析PE估值
        
        Returns:
            (估值水平, 分析文本)
        """
        if pd.isna(pe) or pe <= 0:
            return ValuationLevel.UNKNOWN, "PE数据不可用"
        
        level = self.get_valuation_level(pe, self.PE_RANGES)
        
        analysis_parts = [f"当前PE: {pe:.2f}"]
        
        # 基于绝对值分析
        if level == ValuationLevel.EXTREMELY_LOW:
            analysis_parts.append("绝对估值极低，具备显著安全边际")
        elif level == ValuationLevel.LOW:
            analysis_parts.append("绝对估值较低，具有投资价值")
        elif level == ValuationLevel.REASONABLE:
            analysis_parts.append("绝对估值处于合理区间")
        elif level == ValuationLevel.HIGH:
            analysis_parts.append("绝对估值偏高，需谨慎")
        elif level == ValuationLevel.EXTREMELY_HIGH:
            analysis_parts.append("绝对估值极高，存在泡沫风险")
        
        # 基于历史百分位分析
        if pe_percentile < 20:
            analysis_parts.append(f"处于历史极低水平({pe_percentile:.1f}%分位)")
        elif pe_percentile < 40:
            analysis_parts.append(f"低于历史平均水平({pe_percentile:.1f}%分位)")
        elif pe_percentile > 80:
            analysis_parts.append(f"处于历史高位({pe_percentile:.1f}%分位)")
        elif pe_percentile > 60:
            analysis_parts.append(f"高于历史平均水平({pe_percentile:.1f}%分位)")
        
        # 行业对比
        if industry_pe and not pd.isna(industry_pe):
            ratio = pe / industry_pe
            if ratio < 0.7:
                analysis_parts.append(f"显著低于行业平均({ratio:.1%})")
            elif ratio > 1.3:
                analysis_parts.append(f"显著高于行业平均({ratio:.1%})")
            else:
                analysis_parts.append(f"与行业平均水平相当({ratio:.1%})")
        
        return level, "；".join(analysis_parts)
    
    def analyze_pb(self, pb: float, pb_percentile: float, roe: Optional[float] = None, industry_pb: Optional[float] = None) -> Tuple[ValuationLevel, str]:
        """
        分析PB估值
        
        Returns:
            (估值水平, 分析文本)
        """
        if pd.isna(pb) or pb <= 0:
            return ValuationLevel.UNKNOWN, "PB数据不可用"
        
        level = self.get_valuation_level(pb, self.PB_RANGES)
        
        analysis_parts = [f"当前PB: {pb:.2f}"]
        
        # 结合ROE分析
        if roe and not pd.isna(roe) and roe > 0:
            pb_roe = pb / (roe / 100)  # PB/ROE比率，越小越好
            if pb_roe < 0.1:
                analysis_parts.append(f"PB-ROE性价比极高(ROE: {roe:.1f}%)")
            elif pb_roe < 0.15:
                analysis_parts.append(f"PB-ROE性价比较好(ROE: {roe:.1f}%)")
            elif pb_roe > 0.3:
                analysis_parts.append(f"PB-ROE性价比偏低(ROE: {roe:.1f}%)")
        
        # 基于绝对值分析
        if level == ValuationLevel.EXTREMELY_LOW:
            analysis_parts.append("破净状态，资产价值被低估")
        elif level == ValuationLevel.LOW:
            analysis_parts.append("市净率较低，资产安全边际充足")
        elif level == ValuationLevel.HIGH:
            analysis_parts.append("市净率偏高，资产溢价明显")
        
        # 历史百分位
        if pb_percentile < 20:
            analysis_parts.append(f"处于历史底部区域({pb_percentile:.1f}%分位)")
        elif pb_percentile > 80:
            analysis_parts.append(f"处于历史高位({pb_percentile:.1f}%分位)")
        
        # 行业对比
        if industry_pb and not pd.isna(industry_pb):
            ratio = pb / industry_pb
            if ratio < 0.7:
                analysis_parts.append(f"显著低于行业均值({ratio:.1%})")
            elif ratio > 1.3:
                analysis_parts.append(f"显著高于行业均值({ratio:.1%})")
        
        return level, "；".join(analysis_parts)
    
    def calculate_fair_value(
        self, 
        current_price: float,
        pe: float, 
        pb: float,
        pe_level: ValuationLevel,
        pb_level: ValuationLevel
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        计算合理估值区间
        
        Returns:
            (低估价, 合理价, 高估价)
        """
        if pd.isna(current_price) or current_price <= 0:
            return None, None, None
        
        # 基于PE计算
        if not pd.isna(pe) and pe > 0:
            # 假设合理PE为20倍
            fair_pe_mid = 20
            fair_pe_low = 15
            fair_pe_high = 30
            
            eps = current_price / pe
            pe_low = eps * fair_pe_low
            pe_mid = eps * fair_pe_mid
            pe_high = eps * fair_pe_high
        else:
            pe_low = pe_mid = pe_high = None
        
        # 基于PB计算
        if not pd.isna(pb) and pb > 0:
            # 假设合理PB为2倍
            fair_pb_mid = 2.0
            fair_pb_low = 1.5
            fair_pb_high = 3.0
            
            bvps = current_price / pb
            pb_low = bvps * fair_pb_low
            pb_mid = bvps * fair_pb_mid
            pb_high = bvps * fair_pb_high
        else:
            pb_low = pb_mid = pb_high = None
        
        # 综合PE和PB结果
        if pe_mid and pb_mid:
            # 取平均值，PE权重60%，PB权重40%
            low = (pe_low * 0.6 + pb_low * 0.4) if pe_low and pb_low else (pe_low or pb_low)
            mid = pe_mid * 0.6 + pb_mid * 0.4
            high = (pe_high * 0.6 + pb_high * 0.4) if pe_high and pb_high else (pe_high or pb_high)
        else:
            low = pe_low or pb_low
            mid = pe_mid or pb_mid
            high = pe_high or pb_high
        
        return low, mid, high
    
    def get_overall_valuation(
        self, 
        pe_level: ValuationLevel, 
        pb_level: ValuationLevel,
        pe_percentile: float,
        pb_percentile: float
    ) -> ValuationLevel:
        """综合判断整体估值水平"""
        # 如果任一指标极度异常，以该指标为准
        if pe_level == ValuationLevel.EXTREMELY_LOW or pb_level == ValuationLevel.EXTREMELY_LOW:
            return ValuationLevel.EXTREMELY_LOW
        if pe_level == ValuationLevel.EXTREMELY_HIGH or pb_level == ValuationLevel.EXTREMELY_HIGH:
            return ValuationLevel.EXTREMELY_HIGH
        
        # 计算得分
        level_scores = {
            ValuationLevel.EXTREMELY_LOW: 1,
            ValuationLevel.LOW: 2,
            ValuationLevel.REASONABLE_LOW: 3,
            ValuationLevel.REASONABLE: 4,
            ValuationLevel.REASONABLE_HIGH: 5,
            ValuationLevel.HIGH: 6,
            ValuationLevel.EXTREMELY_HIGH: 7,
            ValuationLevel.UNKNOWN: 4,
        }
        
        pe_score = level_scores.get(pe_level, 4)
        pb_score = level_scores.get(pb_level, 4)
        
        # 考虑历史百分位
        if pe_percentile < 30:
            pe_score -= 1
        elif pe_percentile > 70:
            pe_score += 1
        
        if pb_percentile < 30:
            pb_score -= 1
        elif pb_percentile > 70:
            pb_score += 1
        
        avg_score = (pe_score + pb_score) / 2
        
        if avg_score <= 1.5:
            return ValuationLevel.EXTREMELY_LOW
        elif avg_score <= 2.5:
            return ValuationLevel.LOW
        elif avg_score <= 3.5:
            return ValuationLevel.REASONABLE_LOW
        elif avg_score <= 4.5:
            return ValuationLevel.REASONABLE
        elif avg_score <= 5.5:
            return ValuationLevel.REASONABLE_HIGH
        elif avg_score <= 6.5:
            return ValuationLevel.HIGH
        else:
            return ValuationLevel.EXTREMELY_HIGH
    
    def get_investment_suggestion(
        self,
        overall_level: ValuationLevel,
        technical_trend: str,  # "UP", "DOWN", "SIDEWAYS"
        technical_strength: str  # "STRONG", "MODERATE", "WEAK"
    ) -> Tuple[InvestmentSuggestion, str]:
        """
        结合估值和技术指标给出投资建议
        
        Returns:
            (建议, 置信度)
        """
        # 估值与趋势的一致性判断
        alignment_map = {
            (ValuationLevel.EXTREMELY_LOW, "UP"): (InvestmentSuggestion.STRONG_BUY, "高"),
            (ValuationLevel.LOW, "UP"): (InvestmentSuggestion.BUY, "高"),
            (ValuationLevel.REASONABLE_LOW, "UP"): (InvestmentSuggestion.ACCUMULATE, "中"),
            (ValuationLevel.REASONABLE, "UP"): (InvestmentSuggestion.HOLD, "中"),
            (ValuationLevel.REASONABLE_HIGH, "UP"): (InvestmentSuggestion.HOLD, "低"),
            (ValuationLevel.HIGH, "UP"): (InvestmentSuggestion.REDUCE, "低"),
            (ValuationLevel.EXTREMELY_HIGH, "UP"): (InvestmentSuggestion.SELL, "中"),
            
            (ValuationLevel.EXTREMELY_LOW, "DOWN"): (InvestmentSuggestion.ACCUMULATE, "中"),
            (ValuationLevel.LOW, "DOWN"): (InvestmentSuggestion.HOLD, "低"),
            (ValuationLevel.REASONABLE_LOW, "DOWN"): (InvestmentSuggestion.HOLD, "中"),
            (ValuationLevel.REASONABLE, "DOWN"): (InvestmentSuggestion.REDUCE, "中"),
            (ValuationLevel.REASONABLE_HIGH, "DOWN"): (InvestmentSuggestion.SELL, "中"),
            (ValuationLevel.HIGH, "DOWN"): (InvestmentSuggestion.STRONG_SELL, "高"),
            (ValuationLevel.EXTREMELY_HIGH, "DOWN"): (InvestmentSuggestion.STRONG_SELL, "高"),
            
            (ValuationLevel.EXTREMELY_LOW, "SIDEWAYS"): (InvestmentSuggestion.BUY, "中"),
            (ValuationLevel.LOW, "SIDEWAYS"): (InvestmentSuggestion.ACCUMULATE, "中"),
            (ValuationLevel.REASONABLE_LOW, "SIDEWAYS"): (InvestmentSuggestion.HOLD, "中"),
            (ValuationLevel.REASONABLE, "SIDEWAYS"): (InvestmentSuggestion.HOLD, "中"),
            (ValuationLevel.REASONABLE_HIGH, "SIDEWAYS"): (InvestmentSuggestion.REDUCE, "低"),
            (ValuationLevel.HIGH, "SIDEWAYS"): (InvestmentSuggestion.SELL, "中"),
            (ValuationLevel.EXTREMELY_HIGH, "SIDEWAYS"): (InvestmentSuggestion.SELL, "高"),
        }
        
        result = alignment_map.get((overall_level, technical_trend), 
                                   (InvestmentSuggestion.UNKNOWN, "低"))
        
        # 根据趋势强度调整置信度
        suggestion, confidence = result
        if technical_strength == "STRONG":
            confidence = "高"
        elif technical_strength == "WEAK":
            confidence = "低"
        
        return suggestion, confidence
    
    def analyze(
        self,
        stock_code: str,
        stock_name: str,
        current_price: float,
        metrics: ValuationMetrics,
        technical_trend: str = "SIDEWAYS",
        technical_strength: str = "MODERATE"
    ) -> ValuationResult:
        """
        执行完整的估值分析
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            current_price: 当前价格
            metrics: 估值指标
            technical_trend: 技术趋势方向 (UP/DOWN/SIDEWAYS)
            technical_strength: 技术趋势强度 (STRONG/MODERATE/WEAK)
        
        Returns:
            ValuationResult: 完整的估值分析结果
        """
        analysis_date = datetime.now()
        
        # 计算历史百分位
        pe_percentile = self.calculate_percentile(metrics.pe_ttm, self.pe_history)
        pb_percentile = self.calculate_percentile(metrics.pb, self.pb_history)
        
        # 分析PE
        pe_level, pe_analysis = self.analyze_pe(
            metrics.pe_ttm, 
            pe_percentile, 
            metrics.industry_pe
        )
        
        # 分析PB
        pb_level, pb_analysis = self.analyze_pb(
            metrics.pb, 
            pb_percentile, 
            metrics.roe, 
            metrics.industry_pb
        )
        
        # 综合估值水平
        overall_level = self.get_overall_valuation(
            pe_level, pb_level, pe_percentile, pb_percentile
        )
        
        # 计算合理价值区间
        fair_low, fair_mid, fair_high = self.calculate_fair_value(
            current_price, metrics.pe_ttm, metrics.pb, pe_level, pb_level
        )
        
        # 投资建议
        suggestion, confidence = self.get_investment_suggestion(
            overall_level, technical_trend, technical_strength
        )
        
        # 分析估值与技术指标的契合度
        alignment_parts = []
        if overall_level in [ValuationLevel.EXTREMELY_LOW, ValuationLevel.LOW]:
            if technical_trend == "UP":
                alignment_parts.append("估值低估 + 技术上涨 = 强烈买入信号")
            elif technical_trend == "DOWN":
                alignment_parts.append("估值低估但技术走弱，可能处于探底阶段，可分批建仓")
            else:
                alignment_parts.append("估值低估 + 技术盘整 = 左侧布局机会")
        elif overall_level in [ValuationLevel.HIGH, ValuationLevel.EXTREMELY_HIGH]:
            if technical_trend == "DOWN":
                alignment_parts.append("估值高估 + 技术下跌 = 强烈卖出信号")
            elif technical_trend == "UP":
                alignment_parts.append("估值偏高但技术仍强，可能是最后的冲顶阶段，警惕反转")
            else:
                alignment_parts.append("估值高估 + 技术盘整 = 考虑逐步减仓")
        else:
            if technical_trend == "UP":
                alignment_parts.append("估值合理 + 技术上涨 = 可持有")
            elif technical_trend == "DOWN":
                alignment_parts.append("估值合理 + 技术下跌 = 观望等待")
            else:
                alignment_parts.append("估值合理 + 技术盘整 = 等待方向选择")
        
        technical_alignment = "；".join(alignment_parts)
        
        # 识别风险和机会
        risk_factors = []
        opportunities = []
        
        if pe_level in [ValuationLevel.HIGH, ValuationLevel.EXTREMELY_HIGH]:
            risk_factors.append("PE估值偏高，存在估值回归风险")
        if pb_level in [ValuationLevel.HIGH, ValuationLevel.EXTREMELY_HIGH]:
            risk_factors.append("PB估值偏高，资产溢价明显")
        if pe_percentile > 80:
            risk_factors.append("PE处于历史高位，回调概率大")
        if pb_percentile > 80:
            risk_factors.append("PB处于历史高位，注意资产泡沫风险")
        
        if pe_level in [ValuationLevel.EXTREMELY_LOW, ValuationLevel.LOW]:
            opportunities.append("PE估值较低，具备安全边际")
        if pb_level in [ValuationLevel.EXTREMELY_LOW, ValuationLevel.LOW]:
            opportunities.append("PB估值较低，资产价值被低估")
        if pe_percentile < 20:
            opportunities.append("PE处于历史低位，长期投资价值显现")
        if pb_percentile < 20:
            opportunities.append("PB处于历史低位，破净机会")
        if metrics.peg and metrics.peg < 1:
            opportunities.append(f"PEG={metrics.peg:.2f}<1，成长性价比较好")
        if metrics.dividend_yield and metrics.dividend_yield > 0.03:
            opportunities.append(f"股息率{metrics.dividend_yield:.2%}较高，具备防御价值")
        
        return ValuationResult(
            stock_code=stock_code,
            stock_name=stock_name,
            analysis_date=analysis_date,
            metrics=metrics,
            pe_level=pe_level,
            pb_level=pb_level,
            overall_level=overall_level,
            suggestion=suggestion,
            confidence=confidence,
            pe_analysis=pe_analysis,
            pb_analysis=pb_analysis,
            technical_alignment=technical_alignment,
            risk_factors=risk_factors,
            opportunities=opportunities,
            fair_value_low=fair_low,
            fair_value_mid=fair_mid,
            fair_value_high=fair_high
        )


def format_valuation_report(result: ValuationResult) -> str:
    """格式化估值分析报告"""
    lines = [
        f"# {result.stock_name}({result.stock_code}) 估值分析报告",
        f"分析日期: {result.analysis_date.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 📊 估值指标",
        f"- PE(TTM): {result.metrics.pe_ttm:.2f}" if result.metrics.pe_ttm else "- PE(TTM): --",
        f"- PB: {result.metrics.pb:.2f}" if result.metrics.pb else "- PB: --",
        f"- PEG: {result.metrics.peg:.2f}" if result.metrics.peg else "- PEG: --",
        f"- ROE: {result.metrics.roe:.2f}%" if result.metrics.roe else "- ROE: --",
        "",
        "## 📈 估值判断",
        f"- PE估值水平: {result.pe_level.value}",
        f"- PB估值水平: {result.pb_level.value}",
        f"- **综合估值: {result.overall_level.value}**",
        "",
        "## 💡 投资建议",
        f"**{result.suggestion.value}** (置信度: {result.confidence})",
        "",
        "### PE分析",
        result.pe_analysis,
        "",
        "### PB分析",
        result.pb_analysis,
        "",
        "### 估值与技术契合度",
        result.technical_alignment,
        "",
    ]
    
    if result.fair_value_mid:
        lines.extend([
            "## 🎯 合理估值区间",
            f"- 低估区间: {result.fair_value_low:.2f}" if result.fair_value_low else "- 低估区间: --",
            f"- 合理价值: {result.fair_value_mid:.2f}",
            f"- 高估区间: {result.fair_value_high:.2f}" if result.fair_value_high else "- 高估区间: --",
            "",
        ])
    
    if result.opportunities:
        lines.extend([
            "## ✅ 投资机会",
        ])
        for opp in result.opportunities:
            lines.append(f"- {opp}")
        lines.append("")
    
    if result.risk_factors:
        lines.extend([
            "## ⚠️ 风险提示",
        ])
        for risk in result.risk_factors:
            lines.append(f"- {risk}")
        lines.append("")
    
    return "\n".join(lines)
