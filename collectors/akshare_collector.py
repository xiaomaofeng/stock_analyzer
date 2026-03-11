"""AKShare数据采集器实现"""
import time
import pandas as pd
import numpy as np
from typing import Optional, List
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
import akshare as ak

from .base import DataCollector


class AKShareCollector(DataCollector):
    """AKShare免费数据采集器"""
    
    def __init__(self, request_delay: float = 0.5, max_retries: int = 3):
        super().__init__(request_delay, max_retries)
        self._cache = {}
    
    def _sleep(self):
        """请求间隔"""
        time.sleep(self.request_delay)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_stock_list(self, market: str = "A") -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            market: A/港股/US
        """
        try:
            if market == "A":
                # 获取A股所有股票
                df = ak.stock_zh_a_spot_em()
                # 标准化列名
                df = df.rename(columns={
                    '代码': 'stock_code',
                    '名称': 'stock_name',
                })
                # 提取交易所
                df['exchange'] = df['stock_code'].apply(self._get_exchange)
                
            elif market == "HK":
                df = ak.stock_hk_spot_em()
                df = df.rename(columns={
                    '代码': 'stock_code',
                    '名称': 'stock_name',
                })
                df['exchange'] = 'HK'
                
            elif market == "US":
                df = ak.stock_us_spot_em()
                df = df.rename(columns={
                    '代码': 'stock_code',
                    '名称': 'stock_name',
                })
                df['exchange'] = 'US'
            else:
                raise ValueError(f"不支持的市场类型: {market}")
            
            # 统一列结构
            result = pd.DataFrame({
                'stock_code': df['stock_code'],
                'stock_name': df['stock_name'],
                'exchange': df['exchange'],
                'industry': df.get('所属行业', ''),
                'list_date': None,
            })
            
            self._sleep()
            return result
            
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            raise
    
    def _get_exchange(self, code: str) -> str:
        """根据代码判断交易所"""
        if code.startswith('6'):
            return 'SH'
        elif code.startswith('0') or code.startswith('3'):
            return 'SZ'
        elif code.startswith('8') or code.startswith('4'):
            return 'BJ'
        return 'SH'
    
    # 常见ETF名称映射表（备用）
    ETF_NAME_MAP = {
        # 宽基指数ETF
        '510300': '沪深300ETF',
        '510500': '中证500ETF',
        '510050': '上证50ETF',
        '588000': '科创50ETF',
        '588080': '科创50ETF',
        '159915': '创业板ETF',
        '159901': '深证100ETF',
        '159949': '创业板50ETF',
        '510500': '中证500ETF',
        '512100': '中证1000ETF',
        '159995': '芯片ETF',
        '512000': '券商ETF',
        '512880': '证券ETF',
        # 行业ETF
        '515790': '光伏ETF',
        '159892': '恒生医药ETF',
        '512010': '医药ETF',
        '512170': '医疗ETF',
        '512760': '芯片ETF',
        '512480': '半导体ETF',
        '515880': '科技ETF',
        '512690': '酒ETF',
        '512800': '银行ETF',
        '512200': '房地产ETF',
        '512980': '传媒ETF',
        '515030': '新能源车ETF',
        '516390': '新能源汽车ETF',
        '515250': '智能汽车ETF',
        '515210': '钢铁ETF',
        '515220': '煤炭ETF',
        '515080': '创新药ETF',
        '512290': '生物医药ETF',
        '516110': '汽车ETF',
        '516970': '基建ETF',
        '515050': '5GETF',
        '515400': '人工智能ETF',
        '515980': '人工智能ETF',
        '159819': '人工智能ETF',
        '159870': '化工ETF',
        '159928': '消费ETF',
        '159996': '家电ETF',
        '159938': '医药卫生ETF',
        '159939': '信息技术ETF',
        '159940': '金融地产ETF',
        '159944': '材料ETF',
        '159945': '能源ETF',
        '159946': '原材料ETF',
        '159951': '工业ETF',
        '159952': '电信ETF',
        '159953': '公用事业ETF',
        '159956': '医药健康ETF',
        '159957': '新能源ETF',
        '159958': '创业板ETF',
        '159959': '国企一带一路ETF',
        '159960': '地产ETF',
        '159961': '粤港澳大湾区ETF',
        '159962': '央企创新ETF',
        '159963': '生物科技ETF',
        '159964': '医疗保健ETF',
        '159965': '央企创新驱动ETF',
        '159966': '创成长ETF',
        '159967': '创蓝筹ETF',
        '159968': '创精选88ETF',
        '159969': '创大盘ETF',
        '159970': '创业板低波蓝筹ETF',
        '159971': '创业板动量成长ETF',
        '159972': '5年地债ETF',
        '159973': '民企领先100ETF',
        '159974': '央企ETF',
        '159975': '深100ETF',
        '159976': '湾创100ETF',
        '159977': '港股通50ETF',
        '159978': '全球消费ETF',
        '159979': '大湾区ETF',
        '159980': '有色ETF',
        '159981': '能源化工ETF',
        '159982': '粤港澳大湾区创新100ETF',
        '159983': '化工ETF',
        '159984': '黄金ETF基金',
        '159985': '豆粕ETF',
        '159986': '驰宏锌锗',
        '159987': '通用航空ETF',
        '159988': '成长40ETF',
        '159989': '恒生ETF',
        '159990': '创业板价值ETF',
        '159991': '创成长ETF',
        '159992': '创新药ETF',
        '159993': '龙头券商ETF',
        '159994': '5G通信ETF',
        '159995': '芯片ETF',
        '159996': '家电ETF',
        '159997': '电子ETF',
        '159998': '计算机ETF',
        '159999': '富国上证综指ETF',
        # 港股ETF
        '513050': '中概互联网ETF',
        '513180': '恒生科技ETF',
        '513130': '恒生科技ETF',
        '513060': '恒生医疗ETF',
        '513330': '恒生指数ETF',
        '513600': '港股通ETF',
        '513900': '港股100ETF',
        # 美股ETF
        '513100': '纳斯达克ETF',
        '513300': '纳斯达克100ETF',
        '513500': '标普500ETF',
        # 商品ETF
        '518880': '黄金ETF',
        '159934': '黄金ETF',
        '159937': '黄金ETF',
        '159985': '豆粕ETF',
        '159980': '有色ETF',
        '159981': '能源化工ETF',
        # 货币ETF
        '511880': '银华日利',
        '511660': '货币ETF',
        '511990': '华宝添益',
        '511830': '华泰货币ETF',
        '511810': '理财金货币ETF',
        # 债券ETF
        '511220': '城投债ETF',
        '511010': '国债ETF',
        '511260': '十年国债ETF',
        '511580': '中证短融ETF',
        '511360': '万应债券ETF',
    }
    
    def _is_etf_code(self, stock_code: str) -> bool:
        """判断是否为ETF基金代码"""
        # ETF基金代码范围：51, 56, 58, 15, 16 开头的6位数字
        if stock_code.isdigit() and len(stock_code) == 6:
            return stock_code.startswith(('51', '56', '58', '15', '16'))
        return False
    
    def _get_etf_name(self, stock_code: str) -> str:
        """获取ETF名称，优先使用映射表"""
        return self.ETF_NAME_MAP.get(stock_code, f'{stock_code}ETF')
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_daily_prices(
        self, 
        stock_code: str, 
        start_date: str, 
        end_date: str,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取日线行情数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            adjust: qfq-前复权, hfq-后复权, 空-不复权
        """
        try:
            # 标准化日期格式
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")
            
            # 判断市场并调用对应接口
            if stock_code.isdigit() and len(stock_code) == 6:
                if self._is_etf_code(stock_code):
                    # ETF基金
                    df = ak.fund_etf_hist_em(
                        symbol=stock_code,
                        period="daily",
                        start_date=start,
                        end_date=end,
                        adjust=adjust
                    )
                else:
                    # A股普通股票
                    df = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period="daily",
                        start_date=start,
                        end_date=end,
                        adjust=adjust
                    )
            elif stock_code.isdigit() and len(stock_code) == 5:
                # 港股
                df = ak.stock_hk_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start,
                    end_date=end,
                    adjust=adjust
                )
            else:
                # 美股 - 需要特殊处理代码格式
                df = ak.stock_us_hist(
                    symbol=f"105.{stock_code}",  # 东方财富格式
                    period="daily",
                    start_date=start,
                    end_date=end,
                    adjust=adjust
                )
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 标准化列名
            column_mapping = {
                '日期': 'trade_date',
                '开盘': 'open_price',
                '收盘': 'close_price',
                '最高': 'high_price',
                '最低': 'low_price',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change_amount',
                '换手率': 'turnover_rate',
            }
            
            df = df.rename(columns=column_mapping)
            
            # 添加股票代码
            df['stock_code'] = stock_code
            
            # 确保日期格式正确
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
            
            # 处理昨收价
            if 'pre_close' not in df.columns:
                df['pre_close'] = df['close_price'].shift(1)
            
            self._sleep()
            return df
            
        except Exception as e:
            print(f"获取{stock_code}日线数据失败: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_financial_reports(self, stock_code: str) -> pd.DataFrame:
        """
        获取财务报表数据 - 主要财务指标
        """
        try:
            # 获取主要财务指标
            df = ak.stock_financial_report_sina(stock_code, "利润表")
            
            # TODO: 需要进一步处理财务数据
            # AKShare的财务数据接口较为复杂，可能需要组合多个接口
            
            self._sleep()
            return df
            
        except Exception as e:
            print(f"获取{stock_code}财务数据失败: {e}")
            # 返回空DataFrame而不是抛出异常
            return pd.DataFrame()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_index_list(self) -> pd.DataFrame:
        """获取主要指数列表"""
        try:
            # 获取A股指数列表
            df = ak.stock_zh_index_spot_em()
            df = df.rename(columns={
                '代码': 'index_code',
                '名称': 'index_name',
            })
            df['exchange'] = df['index_code'].apply(
                lambda x: 'SH' if x.startswith('000') else 'SZ'
            )
            
            self._sleep()
            return df[['index_code', 'index_name', 'exchange']]
            
        except Exception as e:
            print(f"获取指数列表失败: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_index_prices(
        self,
        index_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """获取指数行情数据"""
        try:
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")
            
            df = ak.stock_zh_index_hist_csindex(
                symbol=index_code,
                start_date=start,
                end_date=end
            )
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open_price',
                '收盘': 'close_price',
                '最高': 'high_price',
                '最低': 'low_price',
                '成交量': 'volume',
                '成交金额': 'amount',
                '涨跌幅': 'change_pct',
            })
            
            df['index_code'] = index_code
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
            
            self._sleep()
            return df
            
        except Exception as e:
            print(f"获取{index_code}指数数据失败: {e}")
            raise
    
    def get_stock_info(self, stock_code: str) -> Optional[dict]:
        """获取个股详细信息（支持股票和ETF）"""
        try:
            # ETF基金使用映射表或ETF接口
            if self._is_etf_code(stock_code):
                etf_name = self._get_etf_name(stock_code)
                # 尝试从网络获取更准确的名称
                try:
                    df = ak.fund_etf_spot_em()
                    etf_info = df[df['代码'] == stock_code]
                    if len(etf_info) > 0:
                        etf_name = etf_info.iloc[0].get('名称', etf_name)
                except Exception:
                    pass  # 使用映射表名称
                
                return {
                    'stock_code': stock_code,
                    'stock_name': etf_name,
                    'industry': 'ETF基金',
                    'list_date': '',
                    'total_shares': '',
                    'float_shares': '',
                }
            
            # 普通股票使用个股信息接口
            df = ak.stock_individual_info_em(stock_code)
            
            if df is not None and not df.empty:
                info = dict(zip(df['item'], df['value']))
                stock_name = info.get('股票简称', '').strip()
                # 如果名称为空，使用代码作为名称
                if not stock_name:
                    stock_name = stock_code
                return {
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'industry': info.get('行业', ''),
                    'list_date': info.get('上市时间', ''),
                    'total_shares': info.get('总股本', ''),
                    'float_shares': info.get('流通股', ''),
                }
            return None
            
        except Exception as e:
            print(f"获取{stock_code}详细信息失败: {e}")
            return None
    
    def batch_get_daily_prices(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> dict:
        """
        批量获取日线数据
        
        Returns:
            dict: {stock_code: DataFrame}
        """
        results = {}
        total = len(stock_codes)
        
        for i, code in enumerate(stock_codes, 1):
            try:
                print(f"[{i}/{total}] 正在获取 {code}...")
                df = self.get_daily_prices(code, start_date, end_date, adjust)
                results[code] = df
            except Exception as e:
                print(f"获取{code}失败: {e}")
                results[code] = pd.DataFrame()
        
        return results
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_valuation_metrics(self, stock_code: str) -> Optional[dict]:
        """
        获取股票估值指标（PE、PB等）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            dict: 估值指标字典，包含 pe_ttm, pb, ps, dividend_yield 等
        """
        try:
            # ETF没有传统估值指标，返回None
            if self._is_etf_code(stock_code):
                return None
            
            # 方案1：使用stock_individual_info_em获取个股详细信息
            try:
                self._sleep()
                df = ak.stock_individual_info_em(symbol=stock_code)
                if df is not None and not df.empty:
                    info = dict(zip(df['item'], df['value']))
                    result = {}
                    
                    # 市盈率-动态
                    pe_ttm = info.get('市盈率-动态', '')
                    if pe_ttm and str(pe_ttm).replace('.', '').isdigit():
                        result['pe_ttm'] = float(pe_ttm)
                    
                    # 市盈率-静态
                    pe_lyr = info.get('市盈率-静态', '')
                    if pe_lyr and str(pe_lyr).replace('.', '').isdigit():
                        result['pe_lyr'] = float(pe_lyr)
                    
                    # 市净率
                    pb = info.get('市净率', '')
                    if pb and str(pb).replace('.', '').isdigit():
                        result['pb'] = float(pb)
                    
                    # 总股本
                    total_shares = info.get('总股本', '')
                    if total_shares:
                        result['total_shares'] = total_shares
                    
                    # 流通股
                    float_shares = info.get('流通股', '')
                    if float_shares:
                        result['float_shares'] = float_shares
                    
                    if result:
                        return result
            except Exception as e:
                print(f"方案1获取{stock_code}估值数据失败: {e}")
            
            # 方案2：使用stock_zh_a_spot_em获取全市场数据然后筛选
            try:
                self._sleep()
                df = ak.stock_zh_a_spot_em()
                stock_row = df[df['代码'] == stock_code]
                if not stock_row.empty:
                    row = stock_row.iloc[0]
                    result = {}
                    
                    # 市盈率-动态
                    pe_ttm = row.get('市盈率-动态')
                    if pd.notna(pe_ttm) and pe_ttm != '-':
                        try:
                            result['pe_ttm'] = float(pe_ttm)
                        except:
                            pass
                    
                    # 市盈率-静态
                    pe_lyr = row.get('市盈率-静态')
                    if pd.notna(pe_lyr) and pe_lyr != '-':
                        try:
                            result['pe_lyr'] = float(pe_lyr)
                        except:
                            pass
                    
                    # 市净率
                    pb = row.get('市净率')
                    if pd.notna(pb) and pb != '-':
                        try:
                            result['pb'] = float(pb)
                        except:
                            pass
                    
                    # 市销率
                    ps = row.get('市销率')
                    if pd.notna(ps) and ps != '-':
                        try:
                            result['ps'] = float(ps)
                        except:
                            pass
                    
                    # 股息率
                    dy = row.get('股息率')
                    if pd.notna(dy) and dy != '-':
                        try:
                            result['dividend_yield'] = float(dy) / 100
                        except:
                            pass
                    
                    # ROE
                    roe = row.get('净资产收益率')
                    if pd.notna(roe) and roe != '-':
                        try:
                            result['roe'] = float(roe)
                        except:
                            pass
                    
                    if result:
                        return result
            except Exception as e:
                print(f"方案2获取{stock_code}估值数据失败: {e}")
            
            # 方案3：使用stock_a_pe获取历史PE数据然后取最新
            try:
                self._sleep()
                df = ak.stock_a_pe(symbol=stock_code)
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    result = {}
                    
                    pe = latest.get('pe')
                    if pd.notna(pe):
                        result['pe_ttm'] = float(pe)
                    
                    pb = latest.get('pb')
                    if pd.notna(pb):
                        result['pb'] = float(pb)
                    
                    if result:
                        return result
            except Exception as e:
                print(f"方案3获取{stock_code}估值数据失败: {e}")
            
            # 方案4：使用stock_financial_report_sina获取财务数据计算
            try:
                self._sleep()
                # 尝试获取主要财务指标
                df = ak.stock_financial_analysis_indicator(symbol=stock_code)
                if df is not None and not df.empty:
                    latest = df.iloc[0]  # 通常第一行是最新数据
                    result = {}
                    
                    # 尝试获取各种估值指标
                    if '市盈率' in df.columns:
                        pe = latest.get('市盈率')
                        if pd.notna(pe):
                            result['pe_ttm'] = float(pe)
                    
                    if '市净率' in df.columns:
                        pb = latest.get('市净率')
                        if pd.notna(pb):
                            result['pb'] = float(pb)
                    
                    if '净资产收益率' in df.columns:
                        roe = latest.get('净资产收益率')
                        if pd.notna(roe):
                            result['roe'] = float(roe)
                    
                    if result:
                        return result
            except Exception as e:
                print(f"方案4获取{stock_code}估值数据失败: {e}")
            
            # 所有方案都失败，尝试从价格数据估算（仅用于ETF或特殊情况）
            if self._is_etf_code(stock_code):
                # 对于ETF，返回空表示无估值数据
                return None
            
            print(f"所有方案都无法获取{stock_code}的估值数据")
            return None
            
        except Exception as e:
            print(f"获取{stock_code}估值数据失败: {e}")
            return None
    
    def estimate_valuation_from_price(
        self, 
        stock_code: str, 
        price_data: pd.DataFrame,
        estimate_pe: float = 20.0,
        estimate_pb: float = 2.0
    ) -> Optional[dict]:
        """
        从价格数据估算估值（当无法获取真实估值数据时的备选方案）
        
        Args:
            stock_code: 股票代码
            price_data: 价格数据DataFrame
            estimate_pe: 预估PE（默认20）
            estimate_pb: 预估PB（默认2）
            
        Returns:
            dict: 估算的估值指标
        """
        try:
            if price_data is None or price_data.empty:
                return None
            
            # 获取最新价格
            latest_price = price_data['close_price'].iloc[-1] if 'close_price' in price_data.columns else None
            if latest_price is None or latest_price <= 0:
                return None
            
            # 计算一些技术指标作为参考
            returns = price_data['close_price'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) if len(returns) > 30 else 0.3
            
            # 根据波动率调整预估PE（波动大的股票给较低PE）
            adjusted_pe = estimate_pe * (1 - min(volatility, 0.5))
            
            return {
                'pe_ttm': adjusted_pe,
                'pb': estimate_pb,
                'is_estimated': True,  # 标记为估算值
                'estimate_note': '基于价格数据估算，仅供参考'
            }
            
        except Exception as e:
            print(f"估算{stock_code}估值失败: {e}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_historical_valuation(self, stock_code: str, days: int = 252) -> pd.DataFrame:
        """
        获取历史估值数据（用于计算估值百分位）
        
        Args:
            stock_code: 股票代码
            days: 历史数据天数
            
        Returns:
            DataFrame: 包含日期、PE、PB的DataFrame
        """
        try:
            # ETF返回空数据
            if self._is_etf_code(stock_code):
                return pd.DataFrame()
            
            # 方案1：使用stock_a_pe获取历史PE数据
            try:
                self._sleep()
                df = ak.stock_a_pe(symbol=stock_code)
                if df is not None and not df.empty:
                    df = df.tail(days)
                    result = pd.DataFrame()
                    if 'date' in df.columns:
                        result['trade_date'] = df['date']
                    if 'pe' in df.columns:
                        result['pe_ttm'] = pd.to_numeric(df['pe'], errors='coerce')
                    if 'pb' in df.columns:
                        result['pb'] = pd.to_numeric(df['pb'], errors='coerce')
                    return result
            except Exception as e:
                print(f"方案1获取历史估值失败: {e}")
            
            # 方案2：使用stock_zh_a_spot_em获取当前全市场数据作为参考
            # 这个方案只能获取当前数据，无法获取历史序列
            # 实际应用中建议接入专业数据接口（如Wind、Choice等）
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"获取{stock_code}历史估值数据失败: {e}")
            return pd.DataFrame()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_industry_valuation(self, industry: str) -> Optional[dict]:
        """
        获取行业平均估值数据
        
        Args:
            industry: 行业名称
            
        Returns:
            dict: 行业平均PE、PB等
        """
        try:
            # 获取行业估值数据
            try:
                df = ak.stock_industry_pe(symbol=industry)
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    return {
                        'industry_pe': float(latest.get('pe', 0)) if 'pe' in latest else None,
                        'industry_pb': float(latest.get('pb', 0)) if 'pb' in latest else None,
                    }
            except Exception:
                pass
            
            return None
            
        except Exception as e:
            print(f"获取行业{industry}估值数据失败: {e}")
            return None
