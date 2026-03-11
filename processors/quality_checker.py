"""数据质量检查模块"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class QualityReport:
    """质量检查报告"""
    stock_code: str
    check_date: datetime
    total_records: int
    valid_records: int
    issues: List[Dict[str, Any]]
    score: float  # 0-100
    
    def to_dict(self) -> dict:
        return {
            'stock_code': self.stock_code,
            'check_date': self.check_date.isoformat(),
            'total_records': self.total_records,
            'valid_records': self.valid_records,
            'issues_count': len(self.issues),
            'score': round(self.score, 2),
            'issues': self.issues
        }


class QualityChecker:
    """数据质量检查器"""
    
    def __init__(self):
        self.checks = []
    
    def check_completeness(self, df: pd.DataFrame) -> List[Dict]:
        """检查数据完整性"""
        issues = []
        
        if df.empty:
            issues.append({
                'type': 'completeness',
                'severity': 'error',
                'message': '数据为空',
                'count': 0
            })
            return issues
        
        # 检查必要列
        required_cols = ['trade_date', 'open_price', 'high_price', 'low_price', 'close_price']
        for col in required_cols:
            if col not in df.columns:
                issues.append({
                    'type': 'completeness',
                    'severity': 'error',
                    'message': f'缺少必要列: {col}',
                    'count': 1
                })
        
        # 检查缺失值
        for col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                issues.append({
                    'type': 'completeness',
                    'severity': 'warning',
                    'message': f'列 {col} 有 {null_count} 个缺失值',
                    'count': int(null_count)
                })
        
        return issues
    
    def check_consistency(self, df: pd.DataFrame) -> List[Dict]:
        """检查数据一致性"""
        issues = []
        
        if df.empty:
            return issues
        
        # 检查价格逻辑
        if all(col in df.columns for col in ['low_price', 'high_price']):
            invalid = df[df['low_price'] > df['high_price']]
            if not invalid.empty:
                issues.append({
                    'type': 'consistency',
                    'severity': 'error',
                    'message': f'最低价高于最高价: {len(invalid)}条',
                    'count': len(invalid),
                    'dates': invalid['trade_date'].tolist() if 'trade_date' in invalid.columns else []
                })
        
        if all(col in df.columns for col in ['open_price', 'high_price', 'low_price']):
            # 开盘价应该在最高最低价之间
            invalid = df[(df['open_price'] > df['high_price']) | 
                        (df['open_price'] < df['low_price'])]
            if not invalid.empty:
                issues.append({
                    'type': 'consistency',
                    'severity': 'error',
                    'message': f'开盘价超出最高最低价范围: {len(invalid)}条',
                    'count': len(invalid)
                })
        
        if all(col in df.columns for col in ['close_price', 'high_price', 'low_price']):
            # 收盘价应该在最高最低价之间
            invalid = df[(df['close_price'] > df['high_price']) | 
                        (df['close_price'] < df['low_price'])]
            if not invalid.empty:
                issues.append({
                    'type': 'consistency',
                    'severity': 'error',
                    'message': f'收盘价超出最高最低价范围: {len(invalid)}条',
                    'count': len(invalid)
                })
        
        return issues
    
    def check_validity(self, df: pd.DataFrame) -> List[Dict]:
        """检查数据有效性"""
        issues = []
        
        if df.empty:
            return issues
        
        # 检查价格为正
        price_cols = ['open_price', 'high_price', 'low_price', 'close_price']
        for col in price_cols:
            if col in df.columns:
                invalid = df[df[col] <= 0]
                if not invalid.empty:
                    issues.append({
                        'type': 'validity',
                        'severity': 'error',
                        'message': f'{col} 有 {len(invalid)} 条非正数记录',
                        'count': len(invalid)
                    })
        
        # 检查涨跌幅合理性
        if 'change_pct' in df.columns:
            extreme = df[df['change_pct'].abs() > 20]  # A股正常涨跌停是10%/20%
            if not extreme.empty:
                issues.append({
                    'type': 'validity',
                    'severity': 'warning',
                    'message': f'涨跌幅超过20%: {len(extreme)}条 (可能是除权除息日)',
                    'count': len(extreme)
                })
        
        # 检查成交量
        if 'volume' in df.columns:
            zero_volume = df[df['volume'] == 0]
            if not zero_volume.empty:
                issues.append({
                    'type': 'validity',
                    'severity': 'warning',
                    'message': f'成交量为0: {len(zero_volume)}条 (可能是停牌)',
                    'count': len(zero_volume)
                })
        
        return issues
    
    def check_timeliness(self, df: pd.DataFrame) -> List[Dict]:
        """检查数据时效性"""
        issues = []
        
        if df.empty or 'trade_date' not in df.columns:
            return issues
        
        df = df.copy()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        # 检查最新数据日期
        latest_date = df['trade_date'].max()
        today = datetime.now()
        days_diff = (today - latest_date).days
        
        if days_diff > 3:
            issues.append({
                'type': 'timeliness',
                'severity': 'warning',
                'message': f'最新数据是 {latest_date.strftime("%Y-%m-%d")}，距今 {days_diff} 天',
                'count': 1
            })
        
        # 检查数据缺失
        date_range = pd.date_range(df['trade_date'].min(), df['trade_date'].max(), freq='B')
        missing_days = len(date_range) - len(df)
        
        if missing_days > 0:
            missing_ratio = missing_days / len(date_range)
            if missing_ratio > 0.1:  # 缺失超过10%
                issues.append({
                    'type': 'timeliness',
                    'severity': 'warning',
                    'message': f'缺失 {missing_days} 个交易日 ({missing_ratio*100:.1f}%)',
                    'count': missing_days
                })
        
        return issues
    
    def check_duplicates(self, df: pd.DataFrame) -> List[Dict]:
        """检查重复数据"""
        issues = []
        
        if df.empty or 'trade_date' not in df.columns:
            return issues
        
        duplicates = df[df.duplicated(subset=['trade_date'], keep=False)]
        
        if not duplicates.empty:
            issues.append({
                'type': 'duplicates',
                'severity': 'error',
                'message': f'存在 {len(duplicates)} 条重复日期记录',
                'count': len(duplicates),
                'dates': duplicates['trade_date'].unique().tolist()
            })
        
        return issues
    
    def check_all(self, df: pd.DataFrame, stock_code: str = '') -> QualityReport:
        """
        执行所有检查
        
        Returns:
            QualityReport: 质量检查报告
        """
        all_issues = []
        
        # 执行各项检查
        all_issues.extend(self.check_completeness(df))
        all_issues.extend(self.check_consistency(df))
        all_issues.extend(self.check_validity(df))
        all_issues.extend(self.check_timeliness(df))
        all_issues.extend(self.check_duplicates(df))
        
        # 计算得分
        score = self._calculate_score(df, all_issues)
        
        # 统计有效记录
        valid_records = len(df)
        for issue in all_issues:
            if issue['severity'] == 'error':
                valid_records -= issue.get('count', 0)
        
        return QualityReport(
            stock_code=stock_code,
            check_date=datetime.now(),
            total_records=len(df),
            valid_records=max(0, valid_records),
            issues=all_issues,
            score=score
        )
    
    def _calculate_score(self, df: pd.DataFrame, issues: List[Dict]) -> float:
        """计算数据质量得分 (0-100)"""
        if df.empty:
            return 0.0
        
        base_score = 100.0
        
        for issue in issues:
            severity = issue['severity']
            count = issue.get('count', 0)
            
            # 根据严重程度扣分
            if severity == 'error':
                deduction = min(count * 5, 50)  # 每个错误扣5分，最多50分
            else:
                deduction = min(count * 1, 20)  # 每个警告扣1分，最多20分
            
            base_score -= deduction
        
        return max(0, base_score)
    
    @staticmethod
    def generate_summary(reports: List[QualityReport]) -> Dict:
        """生成多个报告的综合摘要"""
        if not reports:
            return {'message': '无报告'}
        
        total_stocks = len(reports)
        avg_score = sum(r.score for r in reports) / total_stocks
        
        error_count = sum(
            1 for r in reports 
            for i in r.issues if i['severity'] == 'error'
        )
        warning_count = sum(
            1 for r in reports 
            for i in r.issues if i['severity'] == 'warning'
        )
        
        # 分级统计
        excellent = sum(1 for r in reports if r.score >= 90)
        good = sum(1 for r in reports if 70 <= r.score < 90)
        fair = sum(1 for r in reports if 50 <= r.score < 70)
        poor = sum(1 for r in reports if r.score < 50)
        
        return {
            'total_stocks': total_stocks,
            'average_score': round(avg_score, 2),
            'total_errors': error_count,
            'total_warnings': warning_count,
            'grade_distribution': {
                'excellent': excellent,
                'good': good,
                'fair': fair,
                'poor': poor
            }
        }
