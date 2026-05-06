"""
╔══════════════════════════════════════════════════════════════════════╗
║         SWING TRADING TERMINAL — Data Fetcher Module                ║
║         PyQt6 + yfinance + pandas-ta                                 ║
║         Covers: Live Price, OHLCV, Fundamentals, Technicals         ║
╚══════════════════════════════════════════════════════════════════════╝

INSTALL REQUIREMENTS:
    pip install PyQt6 yfinance pandas pandas-ta requests

ARCHITECTURE:
    ┌─────────────────────────────────────────────────┐
    │  QThread Workers (non-blocking background fetch) │
    │   ├── LivePriceFetcher   → current price + info  │
    │   ├── OHLCVFetcher       → candlestick history   │
    │   ├── FundamentalFetcher → PE, D/E, revenue etc  │
    │   └── TechnicalFetcher   → RSI, MACD, BBands     │
    └─────────────────────────────────────────────────┘
    All workers emit Qt signals → safe GUI updates
"""

import sys
import yfinance as yf
import pandas as pd
import pandas_ta as ta

from PyQt6.QtCore  import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QTabWidget, QSplitter, QHeaderView, QGroupBox,
    QStatusBar, QProgressBar
)
from PyQt6.QtGui import QColor, QFont


# ══════════════════════════════════════════════════════════════════════
# SECTION 1 — QThread Workers (all network I/O off the main thread)
# ══════════════════════════════════════════════════════════════════════

class LivePriceFetcher(QThread):
    """
    Fetches real-time quote data for a single ticker.
    Emits: data_ready(dict) on success, error(str) on failure.

    Data returned:
        price, previousClose, change, changePct,
        open, dayHigh, dayLow, volume, avgVolume,
        marketCap, fiftyTwoWeekHigh, fiftyTwoWeekLow,
        shortName, currency
    """
    data_ready = pyqtSignal(dict)
    error      = pyqtSignal(str)

    def __init__(self, ticker: str):
        super().__init__()
        self.ticker = ticker.upper().strip()

    def run(self):
        try:
            tk   = yf.Ticker(self.ticker)
            info = tk.info  # dict with 100+ fields

            # Pull the fields most useful for a swing trader
            price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("navPrice")
            )
            prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

            change     = round(price - prev_close, 4) if price and prev_close else None
            change_pct = round((change / prev_close) * 100, 2) if change and prev_close else None

            payload = {
                "ticker":             self.ticker,
                "shortName":          info.get("shortName", "N/A"),
                "currency":           info.get("currency", "USD"),
                "price":              price,
                "previousClose":      prev_close,
                "change":             change,
                "changePct":          change_pct,
                "open":               info.get("open") or info.get("regularMarketOpen"),
                "dayHigh":            info.get("dayHigh") or info.get("regularMarketDayHigh"),
                "dayLow":             info.get("dayLow") or info.get("regularMarketDayLow"),
                "volume":             info.get("volume") or info.get("regularMarketVolume"),
                "avgVolume":          info.get("averageVolume"),
                "marketCap":          info.get("marketCap"),
                "fiftyTwoWeekHigh":   info.get("fiftyTwoWeekHigh"),
                "fiftyTwoWeekLow":    info.get("fiftyTwoWeekLow"),
                "beta":               info.get("beta"),
                "sector":             info.get("sector", "N/A"),
                "industry":           info.get("industry", "N/A"),
            }
            self.data_ready.emit(payload)

        except Exception as e:
            self.error.emit(f"LivePriceFetcher [{self.ticker}]: {str(e)}")


class OHLCVFetcher(QThread):
    """
    Fetches historical OHLCV candlestick data.
    Emits: data_ready(pd.DataFrame) or error(str).

    Supported intervals:
        '1m','2m','5m','15m','30m','60m','90m','1h',
        '1d','5d','1wk','1mo','3mo'

    Supported periods (when no start/end given):
        '1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max'

    NOTE: Intraday intervals (< 1d) limited to last 60 days.
    """
    data_ready = pyqtSignal(object)   # pd.DataFrame
    error      = pyqtSignal(str)

    def __init__(self, ticker: str, period: str = "6mo", interval: str = "1d",
                 start: str = None, end: str = None):
        super().__init__()
        self.ticker   = ticker.upper().strip()
        self.period   = period
        self.interval = interval
        self.start    = start
        self.end      = end

    def run(self):
        try:
            tk = yf.Ticker(self.ticker)

            if self.start and self.end:
                df = tk.history(start=self.start, end=self.end,
                                interval=self.interval, auto_adjust=True)
            else:
                df = tk.history(period=self.period,
                                interval=self.interval, auto_adjust=True)

            if df.empty:
                self.error.emit(f"No OHLCV data for {self.ticker}")
                return

            # Flatten MultiIndex columns if present (batch downloads)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            # Ensure clean column names
            df.index = pd.to_datetime(df.index)
            df.index.name = "Date"

            self.data_ready.emit(df)

        except Exception as e:
            self.error.emit(f"OHLCVFetcher [{self.ticker}]: {str(e)}")


class FundamentalFetcher(QThread):
    """
    Fetches all fundamental / screening metrics:
        PE ratio, Forward PE, PEG, D/E, Revenue growth (5Y),
        Dividend yield, Payout ratio, EPS, Gross Margins,
        Free Cash Flow, Return on Equity, Quick Ratio.

    This is the data layer for the screener table you saw in the UI.
    """
    data_ready = pyqtSignal(dict)
    error      = pyqtSignal(str)

    def __init__(self, ticker: str):
        super().__init__()
        self.ticker = ticker.upper().strip()

    def run(self):
        try:
            tk   = yf.Ticker(self.ticker)
            info = tk.info

            # ── Revenue growth: compare last 2 annual income statements ──
            try:
                financials  = tk.financials          # quarterly P&L
                annual_rev  = tk.income_stmt         # annual
                if annual_rev is not None and not annual_rev.empty:
                    rev_row  = annual_rev.loc["Total Revenue"] if "Total Revenue" in annual_rev.index else None
                    if rev_row is not None and len(rev_row) >= 2:
                        latest   = rev_row.iloc[0]
                        previous = rev_row.iloc[1]
                        rev_growth_yoy = round(((latest - previous) / abs(previous)) * 100, 2)
                    else:
                        rev_growth_yoy = None
                else:
                    rev_growth_yoy = None
            except Exception:
                rev_growth_yoy = None

            # ── Debt / Equity from balance sheet ──
            try:
                bs = tk.balance_sheet
                if bs is not None and not bs.empty:
                    total_debt   = bs.loc["Total Debt"].iloc[0]   if "Total Debt"   in bs.index else None
                    equity       = bs.loc["Stockholders Equity"].iloc[0] if "Stockholders Equity" in bs.index else None
                    de_ratio     = round(total_debt / equity, 2)  if total_debt and equity and equity != 0 else None
                else:
                    de_ratio = None
            except Exception:
                de_ratio = None

            payload = {
                "ticker":              self.ticker,
                # Valuation
                "trailingPE":          info.get("trailingPE"),
                "forwardPE":           info.get("forwardPE"),
                "pegRatio":            info.get("pegRatio"),
                "priceToBook":         info.get("priceToBook"),
                "priceToSales":        info.get("priceToSalesTrailing12Months"),
                "enterpriseToEbitda":  info.get("enterpriseToEbitda"),
                # Growth
                "revenueGrowth":       info.get("revenueGrowth"),        # TTM YoY %
                "earningsGrowth":      info.get("earningsGrowth"),
                "revenueGrowthYoY":    rev_growth_yoy,                   # from income stmt
                # Profitability
                "grossMargins":        info.get("grossMargins"),
                "operatingMargins":    info.get("operatingMargins"),
                "profitMargins":       info.get("profitMargins"),
                "returnOnEquity":      info.get("returnOnEquity"),
                "returnOnAssets":      info.get("returnOnAssets"),
                # Balance sheet
                "debtToEquity":        info.get("debtToEquity"),         # from info dict
                "debtToEquityCalc":    de_ratio,                         # from balance sheet
                "currentRatio":        info.get("currentRatio"),
                "quickRatio":          info.get("quickRatio"),
                "totalCash":           info.get("totalCash"),
                "totalDebt":           info.get("totalDebt"),
                "freeCashflow":        info.get("freeCashflow"),
                # Dividends
                "dividendYield":       info.get("dividendYield"),
                "payoutRatio":         info.get("payoutRatio"),
                "dividendRate":        info.get("dividendRate"),
                "exDividendDate":      info.get("exDividendDate"),
                # EPS
                "trailingEps":         info.get("trailingEps"),
                "forwardEps":          info.get("forwardEps"),
                # Analyst
                "targetMeanPrice":     info.get("targetMeanPrice"),
                "targetHighPrice":     info.get("targetHighPrice"),
                "targetLowPrice":      info.get("targetLowPrice"),
                "recommendationMean":  info.get("recommendationMean"),
                "recommendationKey":   info.get("recommendationKey"),
                "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
            }
            self.data_ready.emit(payload)

        except Exception as e:
            self.error.emit(f"FundamentalFetcher [{self.ticker}]: {str(e)}")


class TechnicalFetcher(QThread):
    """
    Fetches OHLCV then computes technical indicators via pandas-ta.

    Indicators computed:
        RSI(14), MACD(12,26,9), Bollinger Bands(20,2),
        EMA(9), EMA(21), EMA(50), EMA(200),
        ATR(14), Stochastic(14,3), Volume SMA(20),
        ADX(14), OBV

    Returns dict with latest values for each indicator.
    """
    data_ready = pyqtSignal(dict)
    error      = pyqtSignal(str)

    def __init__(self, ticker: str, period: str = "1y", interval: str = "1d"):
        super().__init__()
        self.ticker   = ticker.upper().strip()
        self.period   = period
        self.interval = interval

    def run(self):
        try:
            tk = yf.Ticker(self.ticker)
            df = tk.history(period=self.period, interval=self.interval, auto_adjust=True)

            if df.empty:
                self.error.emit(f"No data for technical analysis on {self.ticker}")
                return

            # Flatten MultiIndex if needed
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            # ── Compute all indicators using pandas-ta strategy ──
            df.ta.rsi(length=14, append=True)           # RSI_14
            df.ta.macd(fast=12, slow=26, signal=9,
                       append=True)                     # MACD_12_26_9, MACDh_, MACDs_
            df.ta.bbands(length=20, std=2, append=True) # BBL_, BBM_, BBU_, BBB_, BBP_
            df.ta.ema(length=9,   append=True)          # EMA_9
            df.ta.ema(length=21,  append=True)          # EMA_21
            df.ta.ema(length=50,  append=True)          # EMA_50
            df.ta.ema(length=200, append=True)          # EMA_200
            df.ta.atr(length=14,  append=True)          # ATRr_14
            df.ta.stoch(k=14, d=3, append=True)         # STOCHk_14_3_3, STOCHd_14_3_3
            df.ta.adx(length=14,  append=True)          # ADX_14, DMP_14, DMN_14
            df.ta.obv(append=True)                      # OBV

            # Volume SMA manually (pandas-ta sma on volume)
            df["VOL_SMA_20"] = df["Volume"].rolling(20).mean()

            # ── Extract latest row values ──
            latest   = df.iloc[-1]
            prev     = df.iloc[-2] if len(df) >= 2 else latest
            close    = latest["Close"]

            def safe(col):
                val = latest.get(col)
                return round(float(val), 4) if val is not None and not pd.isna(val) else None

            # RSI signal
            rsi = safe("RSI_14")
            rsi_signal = (
                "Oversold"  if rsi and rsi < 30 else
                "Overbought" if rsi and rsi > 70 else
                "Neutral"
            )

            # MACD histogram direction
            macd_h    = safe("MACDh_12_26_9")
            prev_macdh = prev.get("MACDh_12_26_9")
            macd_signal = (
                "Bullish crossover" if macd_h and prev_macdh and macd_h > 0 > prev_macdh else
                "Bearish crossover" if macd_h and prev_macdh and macd_h < 0 < prev_macdh else
                "Bullish"           if macd_h and macd_h > 0 else
                "Bearish"           if macd_h and macd_h < 0 else "N/A"
            )

            # Bollinger Band position
            bbl  = safe("BBL_20_2.0")
            bbu  = safe("BBU_20_2.0")
            bbp  = safe("BBP_20_2.0")
            bb_signal = (
                "Near lower band (potential bounce)" if bbp and bbp < 0.2 else
                "Near upper band (overbought risk)"  if bbp and bbp > 0.8 else
                "Mid-band (neutral)"
            )

            # Trend via EMA stack
            ema9  = safe("EMA_9")
            ema21 = safe("EMA_21")
            ema50 = safe("EMA_50")
            ema200= safe("EMA_200")
            trend = "Unknown"
            if ema9 and ema21 and ema50 and ema200:
                if close > ema9 > ema21 > ema50 > ema200:
                    trend = "Strong Uptrend (all EMAs bullish)"
                elif close > ema50 > ema200:
                    trend = "Uptrend"
                elif close < ema9 < ema21 < ema50:
                    trend = "Downtrend"
                elif close < ema200:
                    trend = "Below 200 EMA (bearish bias)"
                else:
                    trend = "Mixed / Consolidating"

            # ADX trend strength
            adx = safe("ADX_14")
            adx_strength = (
                "Very strong trend" if adx and adx > 40 else
                "Strong trend"      if adx and adx > 25 else
                "Weak / ranging"    if adx and adx < 20 else "Moderate"
            )

            payload = {
                "ticker":      self.ticker,
                "close":       round(close, 4),
                "dataframe":   df,              # full df for charting

                # RSI
                "rsi":         rsi,
                "rsi_signal":  rsi_signal,

                # MACD
                "macd":        safe("MACD_12_26_9"),
                "macd_signal": safe("MACDs_12_26_9"),
                "macd_hist":   macd_h,
                "macd_interp": macd_signal,

                # Bollinger Bands
                "bb_lower":    bbl,
                "bb_mid":      safe("BBM_20_2.0"),
                "bb_upper":    bbu,
                "bb_pct":      bbp,
                "bb_signal":   bb_signal,

                # EMAs
                "ema_9":       ema9,
                "ema_21":      ema21,
                "ema_50":      ema50,
                "ema_200":     ema200,
                "trend":       trend,

                # ATR (volatility / stop-loss sizing)
                "atr":         safe("ATRr_14"),

                # Stochastic
                "stoch_k":     safe("STOCHk_14_3_3"),
                "stoch_d":     safe("STOCHd_14_3_3"),

                # ADX
                "adx":         adx,
                "adx_dmp":     safe("DMP_14"),    # +DI
                "adx_dmn":     safe("DMN_14"),    # -DI
                "adx_strength":adx_strength,

                # Volume
                "volume":      int(latest["Volume"]),
                "vol_sma20":   safe("VOL_SMA_20"),
                "vol_signal":  "Above avg" if latest["Volume"] > (latest.get("VOL_SMA_20") or 0) else "Below avg",

                # OBV
                "obv":         safe("OBV"),
            }
            self.data_ready.emit(payload)

        except Exception as e:
            self.error.emit(f"TechnicalFetcher [{self.ticker}]: {str(e)}")


class BatchScreenerFetcher(QThread):
    """
    Fetches fundamental + live price data for a list of tickers.
    Used to populate the screener table (like the Goldman screener above).

    Emits: ticker_done(dict) after each ticker completes
           all_done() when all tickers are processed
    """
    ticker_done = pyqtSignal(dict)
    all_done    = pyqtSignal()
    error       = pyqtSignal(str)
    progress    = pyqtSignal(int)   # 0–100

    def __init__(self, tickers: list):
        super().__init__()
        self.tickers = [t.upper().strip() for t in tickers]

    def run(self):
        total = len(self.tickers)
        for i, ticker in enumerate(self.tickers):
            try:
                tk   = yf.Ticker(ticker)
                info = tk.info

                price      = info.get("currentPrice") or info.get("regularMarketPrice")
                prev_close = info.get("previousClose")
                change_pct = round(((price - prev_close) / prev_close) * 100, 2) if price and prev_close else None

                row = {
                    "ticker":       ticker,
                    "shortName":    info.get("shortName", ticker),
                    "sector":       info.get("sector", "N/A"),
                    "price":        price,
                    "changePct":    change_pct,
                    "trailingPE":   info.get("trailingPE"),
                    "forwardPE":    info.get("forwardPE"),
                    "pegRatio":     info.get("pegRatio"),
                    "marketCap":    info.get("marketCap"),
                    "debtToEquity": info.get("debtToEquity"),
                    "revenueGrowth":info.get("revenueGrowth"),
                    "grossMargins": info.get("grossMargins"),
                    "dividendYield":info.get("dividendYield"),
                    "returnOnEquity":info.get("returnOnEquity"),
                    "beta":         info.get("beta"),
                    "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
                    "fiftyTwoWeekLow":  info.get("fiftyTwoWeekLow"),
                    "targetMeanPrice":  info.get("targetMeanPrice"),
                    "recommendationKey": info.get("recommendationKey", "N/A"),
                }
                self.ticker_done.emit(row)
                self.progress.emit(int(((i + 1) / total) * 100))

            except Exception as e:
                self.error.emit(f"BatchScreener [{ticker}]: {str(e)}")

        self.all_done.emit()


# ══════════════════════════════════════════════════════════════════════
# SECTION 2 — Auto-Refresh Timer Helper
# ══════════════════════════════════════════════════════════════════════

class AutoRefreshManager:
    """
    Wraps a QTimer to periodically re-fire a fetch worker.
    Usage:
        self.refresher = AutoRefreshManager(
            interval_seconds=30,
            callback=self.fetch_live_price
        )
        self.refresher.start()
        self.refresher.stop()
    """
    def __init__(self, interval_seconds: int, callback):
        self.timer    = QTimer()
        self.interval = interval_seconds * 1000
        self.callback = callback
        self.timer.timeout.connect(self.callback)

    def start(self):
        self.timer.start(self.interval)

    def stop(self):
        self.timer.stop()

    def set_interval(self, seconds: int):
        self.interval = seconds * 1000
        if self.timer.isActive():
            self.timer.setInterval(self.interval)


# ══════════════════════════════════════════════════════════════════════
# SECTION 3 — Demo PyQt6 Terminal Window
# ══════════════════════════════════════════════════════════════════════

class SwingTraderTerminal(QMainWindow):
    """
    Demo terminal showing how to wire up all 4 data fetchers.

    Tabs:
        1. Live Quote   — real-time price panel
        2. Fundamentals — PE, D/E, revenue, dividends, analysts
        3. Technicals   — RSI, MACD, BB, EMA, ADX, ATR
        4. Screener     — batch multi-stock table
    """

    WATCHLIST = ["NVDA", "PLTR", "LLY", "AVGO", "JPM",
                 "MU",   "BAC",  "AMZN", "XOM", "META"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Swing Trading Terminal  |  Powered by yfinance + pandas-ta")
        self.resize(1200, 800)
        self._active_workers = []   # keep references so GC doesn't kill threads
        self._build_ui()
        self._apply_dark_theme()

    # ── UI Construction ──────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 4)

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("Enter ticker, e.g. NVDA")
        self.ticker_input.setMaximumWidth(160)
        self.ticker_input.returnPressed.connect(self._on_fetch)

        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1d","1h","15m","5m","1wk"])

        self.period_combo = QComboBox()
        self.period_combo.addItems(["6mo","1y","3mo","2y","5y","ytd"])

        fetch_btn = QPushButton("Fetch")
        fetch_btn.clicked.connect(self._on_fetch)
        fetch_btn.setFixedWidth(80)

        screen_btn = QPushButton("Run Screener")
        screen_btn.clicked.connect(self._on_run_screener)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMaximumWidth(200)

        toolbar.addWidget(QLabel("Ticker:"))
        toolbar.addWidget(self.ticker_input)
        toolbar.addWidget(QLabel("Interval:"))
        toolbar.addWidget(self.interval_combo)
        toolbar.addWidget(QLabel("Period:"))
        toolbar.addWidget(self.period_combo)
        toolbar.addWidget(fetch_btn)
        toolbar.addSpacing(20)
        toolbar.addWidget(screen_btn)
        toolbar.addWidget(self.progress)
        toolbar.addStretch()
        root_layout.addLayout(toolbar)

        # ── Tabs ──
        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_quote_tab(),        "Live Quote")
        self.tabs.addTab(self._build_fundamentals_tab(), "Fundamentals")
        self.tabs.addTab(self._build_technicals_tab(),   "Technicals")
        self.tabs.addTab(self._build_screener_tab(),     "Screener")

        # ── Status bar ──
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready — enter a ticker and press Fetch")

    def _build_quote_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Price header
        self.price_label  = QLabel("—")
        self.price_label.setFont(QFont("Courier New", 32, QFont.Bold))
        self.change_label = QLabel("")
        self.change_label.setFont(QFont("Courier New", 16))
        self.name_label   = QLabel("")
        self.name_label.setFont(QFont("Arial", 11))

        layout.addWidget(self.name_label)
        layout.addWidget(self.price_label)
        layout.addWidget(self.change_label)

        # Quote details table
        self.quote_table = self._make_kv_table([
            "Open","Day High","Day Low","Prev Close",
            "Volume","Avg Volume","Market Cap",
            "52W High","52W Low","Beta","Sector"
        ])
        layout.addWidget(self.quote_table)
        layout.addStretch()

        # Auto-refresh toggle
        refresh_row = QHBoxLayout()
        self.refresh_btn = QPushButton("Start Auto-Refresh (30s)")
        self.refresh_btn.setCheckable(True)
        self.refresh_btn.toggled.connect(self._toggle_auto_refresh)
        refresh_row.addWidget(self.refresh_btn)
        refresh_row.addStretch()
        layout.addLayout(refresh_row)

        self._auto_refresher = None
        return w

    def _build_fundamentals_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.fund_table = self._make_kv_table([
            "Trailing P/E","Forward P/E","PEG Ratio",
            "Price/Book","Price/Sales","EV/EBITDA",
            "─── Growth ───",
            "Revenue Growth (TTM)","Earnings Growth",
            "─── Margins ───",
            "Gross Margin","Operating Margin","Net Margin",
            "Return on Equity","Return on Assets",
            "─── Balance Sheet ───",
            "Debt/Equity","Current Ratio","Quick Ratio",
            "Free Cash Flow","Total Cash","Total Debt",
            "─── Dividends ───",
            "Dividend Yield","Payout Ratio","Dividend Rate",
            "─── EPS ───",
            "Trailing EPS","Forward EPS",
            "─── Analyst Targets ───",
            "Consensus","Mean Target","High Target","Low Target","# Analysts"
        ])
        layout.addWidget(self.fund_table)
        return w

    def _build_technicals_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.tech_table = self._make_kv_table([
            "Close Price","Trend (EMA stack)",
            "─── Momentum ───",
            "RSI (14)","RSI Signal",
            "MACD Line","MACD Signal","MACD Histogram","MACD Interpretation",
            "Stoch %K","Stoch %D",
            "─── Volatility ───",
            "ATR (14)","BB Lower","BB Mid","BB Upper","BB %B","BB Signal",
            "─── Trend ───",
            "EMA 9","EMA 21","EMA 50","EMA 200",
            "ADX (14)","ADX +DI","ADX -DI","ADX Strength",
            "─── Volume ───",
            "Volume","Volume SMA (20)","Volume Signal","OBV"
        ])
        layout.addWidget(self.tech_table)
        return w

    def _build_screener_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        columns = [
            "Ticker","Name","Sector","Price","Chg%",
            "P/E (TTM)","Fwd P/E","PEG","Market Cap",
            "D/E","Rev Growth","Gross Margin",
            "Div Yield","ROE","Beta",
            "52W High","52W Low","Target","Rating"
        ]
        self.screener_table = QTableWidget(0, len(columns))
        self.screener_table.setHorizontalHeaderLabels(columns)
        self.screener_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.screener_table.setAlternatingRowColors(True)
        self.screener_table.setSortingEnabled(True)
        layout.addWidget(self.screener_table)
        return w

    # ── Signal Handlers ───────────────────────────────────────────────

    def _on_fetch(self):
        ticker = self.ticker_input.text().strip().upper()
        if not ticker:
            self.status.showMessage("Please enter a ticker symbol.")
            return

        period   = self.period_combo.currentText()
        interval = self.interval_combo.currentText()
        self.status.showMessage(f"Fetching data for {ticker}...")

        # 1. Live price
        w1 = LivePriceFetcher(ticker)
        w1.data_ready.connect(self._on_quote_ready)
        w1.error.connect(self._on_error)
        w1.start()
        self._active_workers.append(w1)

        # 2. Fundamentals
        w2 = FundamentalFetcher(ticker)
        w2.data_ready.connect(self._on_fundamentals_ready)
        w2.error.connect(self._on_error)
        w2.start()
        self._active_workers.append(w2)

        # 3. Technicals
        w3 = TechnicalFetcher(ticker, period=period, interval=interval)
        w3.data_ready.connect(self._on_technicals_ready)
        w3.error.connect(self._on_error)
        w3.start()
        self._active_workers.append(w3)

    def _on_run_screener(self):
        self.screener_table.setRowCount(0)
        self.progress.setVisible(True)
        self.progress.setValue(0)

        worker = BatchScreenerFetcher(self.WATCHLIST)
        worker.ticker_done.connect(self._on_screener_row)
        worker.all_done.connect(lambda: (
            self.progress.setVisible(False),
            self.status.showMessage("Screener complete.")
        ))
        worker.progress.connect(self.progress.setValue)
        worker.error.connect(self._on_error)
        worker.start()
        self._active_workers.append(worker)
        self.status.showMessage("Running batch screener...")

    def _toggle_auto_refresh(self, checked: bool):
        ticker = self.ticker_input.text().strip().upper()
        if checked and ticker:
            self._auto_refresher = AutoRefreshManager(30, self._on_fetch)
            self._auto_refresher.start()
            self.refresh_btn.setText("Stop Auto-Refresh")
        else:
            if self._auto_refresher:
                self._auto_refresher.stop()
            self.refresh_btn.setText("Start Auto-Refresh (30s)")

    # ── Data Receivers ────────────────────────────────────────────────

    def _on_quote_ready(self, d: dict):
        ticker = d["ticker"]
        price  = d.get("price")
        chg    = d.get("change")
        chgpct = d.get("changePct")

        self.name_label.setText(f"{d.get('shortName','')}  ({ticker})")
        self.price_label.setText(f"${price:,.2f}" if price else "N/A")

        if chg is not None and chgpct is not None:
            sign  = "▲" if chg >= 0 else "▼"
            color = "#00C896" if chg >= 0 else "#E24B4A"
            self.change_label.setText(f"{sign} {abs(chg):.2f}  ({chgpct:+.2f}%)")
            self.change_label.setStyleSheet(f"color: {color};")

        def fmt_large(n):
            if n is None: return "N/A"
            if n >= 1e12: return f"${n/1e12:.2f}T"
            if n >= 1e9:  return f"${n/1e9:.2f}B"
            if n >= 1e6:  return f"${n/1e6:.2f}M"
            return str(n)

        self._set_kv(self.quote_table, {
            "Open":        f"${d.get('open'):,.2f}"        if d.get('open')      else "N/A",
            "Day High":    f"${d.get('dayHigh'):,.2f}"     if d.get('dayHigh')   else "N/A",
            "Day Low":     f"${d.get('dayLow'):,.2f}"      if d.get('dayLow')    else "N/A",
            "Prev Close":  f"${d.get('previousClose'):,.2f}" if d.get('previousClose') else "N/A",
            "Volume":      f"{d.get('volume'):,}"          if d.get('volume')    else "N/A",
            "Avg Volume":  f"{d.get('avgVolume'):,}"       if d.get('avgVolume') else "N/A",
            "Market Cap":  fmt_large(d.get('marketCap')),
            "52W High":    f"${d.get('fiftyTwoWeekHigh'):,.2f}" if d.get('fiftyTwoWeekHigh') else "N/A",
            "52W Low":     f"${d.get('fiftyTwoWeekLow'):,.2f}"  if d.get('fiftyTwoWeekLow')  else "N/A",
            "Beta":        str(round(d['beta'], 2)) if d.get('beta') else "N/A",
            "Sector":      d.get('sector', 'N/A'),
        })
        self.status.showMessage(f"{ticker} quote loaded successfully")

    def _on_fundamentals_ready(self, d: dict):
        def pct(v): return f"{v*100:.2f}%" if v is not None else "N/A"
        def val(v, fmt="{:.2f}"): return fmt.format(v) if v is not None else "N/A"
        def bil(v):
            if v is None: return "N/A"
            return f"${v/1e9:.2f}B" if abs(v) >= 1e9 else f"${v/1e6:.2f}M"

        rk = (d.get("recommendationKey") or "N/A").upper()
        rk_color = {"BUY":"#00C896","STRONG_BUY":"#00C896",
                    "SELL":"#E24B4A","STRONG_SELL":"#E24B4A",
                    "HOLD":"#EF9F27"}.get(rk, "white")

        self._set_kv(self.fund_table, {
            "Trailing P/E":          val(d.get("trailingPE")),
            "Forward P/E":           val(d.get("forwardPE")),
            "PEG Ratio":             val(d.get("pegRatio")),
            "Price/Book":            val(d.get("priceToBook")),
            "Price/Sales":           val(d.get("priceToSales")),
            "EV/EBITDA":             val(d.get("enterpriseToEbitda")),
            "Revenue Growth (TTM)":  pct(d.get("revenueGrowth")),
            "Earnings Growth":       pct(d.get("earningsGrowth")),
            "Gross Margin":          pct(d.get("grossMargins")),
            "Operating Margin":      pct(d.get("operatingMargins")),
            "Net Margin":            pct(d.get("profitMargins")),
            "Return on Equity":      pct(d.get("returnOnEquity")),
            "Return on Assets":      pct(d.get("returnOnAssets")),
            "Debt/Equity":           val(d.get("debtToEquity")),
            "Current Ratio":         val(d.get("currentRatio")),
            "Quick Ratio":           val(d.get("quickRatio")),
            "Free Cash Flow":        bil(d.get("freeCashflow")),
            "Total Cash":            bil(d.get("totalCash")),
            "Total Debt":            bil(d.get("totalDebt")),
            "Dividend Yield":        pct(d.get("dividendYield")),
            "Payout Ratio":          pct(d.get("payoutRatio")),
            "Dividend Rate":         f"${d.get('dividendRate'):.2f}" if d.get("dividendRate") else "N/A",
            "Trailing EPS":          val(d.get("trailingEps")),
            "Forward EPS":           val(d.get("forwardEps")),
            "Consensus":             rk,
            "Mean Target":           f"${d.get('targetMeanPrice'):,.2f}" if d.get("targetMeanPrice") else "N/A",
            "High Target":           f"${d.get('targetHighPrice'):,.2f}" if d.get("targetHighPrice") else "N/A",
            "Low Target":            f"${d.get('targetLowPrice'):,.2f}"  if d.get("targetLowPrice")  else "N/A",
            "# Analysts":            str(d.get("numberOfAnalystOpinions") or "N/A"),
        })

    def _on_technicals_ready(self, d: dict):
        def v(key): return str(d.get(key)) if d.get(key) is not None else "N/A"

        self._set_kv(self.tech_table, {
            "Close Price":           f"${d.get('close'):,.4f}",
            "Trend (EMA stack)":     d.get("trend", "N/A"),
            "RSI (14)":              v("rsi"),
            "RSI Signal":            d.get("rsi_signal", "N/A"),
            "MACD Line":             v("macd"),
            "MACD Signal":           v("macd_signal"),
            "MACD Histogram":        v("macd_hist"),
            "MACD Interpretation":   d.get("macd_interp", "N/A"),
            "Stoch %K":              v("stoch_k"),
            "Stoch %D":              v("stoch_d"),
            "ATR (14)":              v("atr"),
            "BB Lower":              v("bb_lower"),
            "BB Mid":                v("bb_mid"),
            "BB Upper":              v("bb_upper"),
            "BB %B":                 v("bb_pct"),
            "BB Signal":             d.get("bb_signal", "N/A"),
            "EMA 9":                 v("ema_9"),
            "EMA 21":                v("ema_21"),
            "EMA 50":                v("ema_50"),
            "EMA 200":               v("ema_200"),
            "ADX (14)":              v("adx"),
            "ADX +DI":               v("adx_dmp"),
            "ADX -DI":               v("adx_dmn"),
            "ADX Strength":          d.get("adx_strength", "N/A"),
            "Volume":                f"{d.get('volume', 0):,}",
            "Volume SMA (20)":       v("vol_sma20"),
            "Volume Signal":         d.get("vol_signal", "N/A"),
            "OBV":                   v("obv"),
        })

    def _on_screener_row(self, d: dict):
        row = self.screener_table.rowCount()
        self.screener_table.insertRow(row)

        def cell(val, color=None):
            item = QTableWidgetItem(str(val) if val is not None else "N/A")
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            if color:
                item.setForeground(QColor(color))
            return item

        def pct(v):   return f"{v*100:.1f}%" if v is not None else "N/A"
        def fmt_cap(n):
            if n is None: return "N/A"
            if n >= 1e12: return f"{n/1e12:.1f}T"
            if n >= 1e9:  return f"{n/1e9:.1f}B"
            return f"{n/1e6:.0f}M"

        chg = d.get("changePct")
        chg_color = "#00C896" if chg and chg > 0 else "#E24B4A" if chg and chg < 0 else None
        rk = (d.get("recommendationKey") or "N/A").upper()
        rk_color = {"BUY":"#00C896","STRONG_BUY":"#00FF99",
                    "SELL":"#E24B4A","STRONG_SELL":"#FF4444",
                    "HOLD":"#EF9F27"}.get(rk, None)

        cells = [
            cell(d.get("ticker"),                  "#C9A84C"),
            cell(d.get("shortName","")),
            cell(d.get("sector","")),
            cell(f"${d['price']:,.2f}" if d.get("price") else "N/A"),
            cell(f"{chg:+.2f}%" if chg else "N/A",   chg_color),
            cell(f"{d['trailingPE']:.1f}x"  if d.get("trailingPE") else "N/A"),
            cell(f"{d['forwardPE']:.1f}x"   if d.get("forwardPE")  else "N/A"),
            cell(f"{d['pegRatio']:.2f}"      if d.get("pegRatio")   else "N/A"),
            cell(fmt_cap(d.get("marketCap"))),
            cell(f"{d['debtToEquity']:.2f}"  if d.get("debtToEquity") else "N/A"),
            cell(pct(d.get("revenueGrowth"))),
            cell(pct(d.get("grossMargins"))),
            cell(pct(d.get("dividendYield"))),
            cell(pct(d.get("returnOnEquity"))),
            cell(f"{d['beta']:.2f}"          if d.get("beta") else "N/A"),
            cell(f"${d['fiftyTwoWeekHigh']:,.2f}" if d.get("fiftyTwoWeekHigh") else "N/A"),
            cell(f"${d['fiftyTwoWeekLow']:,.2f}"  if d.get("fiftyTwoWeekLow")  else "N/A"),
            cell(f"${d['targetMeanPrice']:,.2f}"  if d.get("targetMeanPrice")   else "N/A"),
            cell(rk, rk_color),
        ]
        for col, item in enumerate(cells):
            self.screener_table.setItem(row, col, item)

    def _on_error(self, msg: str):
        self.status.showMessage(f"Error: {msg}")

    # ── Helpers ───────────────────────────────────────────────────────

    def _make_kv_table(self, keys: list) -> QTableWidget:
        tbl = QTableWidget(len(keys), 2)
        tbl.setHorizontalHeaderLabels(["Metric", "Value"])
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setAlternatingRowColors(True)
        for i, key in enumerate(keys):
            item = QTableWidgetItem(key)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            if key.startswith("─"):
                item.setForeground(QColor("#C9A84C"))
                item.setFont(QFont("Arial", 9))
            tbl.setItem(i, 0, item)
            val_item = QTableWidgetItem("—")
            val_item.setFlags(val_item.flags() & ~Qt.ItemIsEditable)
            tbl.setItem(i, 1, val_item)
        return tbl

    def _set_kv(self, tbl: QTableWidget, data: dict):
        for row in range(tbl.rowCount()):
            key_item = tbl.item(row, 0)
            if key_item and key_item.text() in data:
                val_item = tbl.item(row, 1)
                if val_item:
                    val_item.setText(str(data[key_item.text()]))

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0D0D1A;
                color: #CCCCCC;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
            QTabWidget::pane { border: 1px solid #2A2A4A; }
            QTabBar::tab {
                background: #111127; color: #888;
                padding: 6px 16px; border: 1px solid #2A2A4A;
            }
            QTabBar::tab:selected { background: #1A1A3A; color: #C9A84C; }
            QTableWidget {
                background-color: #0D0D1A; gridline-color: #1A1A3A;
                alternate-background-color: #111127;
            }
            QTableWidget::item { padding: 3px 6px; }
            QHeaderView::section {
                background-color: #111127; color: #C9A84C;
                border: 0.5px solid #2A2A4A; padding: 4px;
                font-size: 10px; letter-spacing: 1px;
            }
            QLineEdit, QComboBox {
                background: #111127; color: #CCC;
                border: 1px solid #2A2A4A; padding: 4px 8px;
                border-radius: 3px;
            }
            QPushButton {
                background: #1A1A3A; color: #C9A84C;
                border: 1px solid #C9A84C; padding: 5px 14px;
                border-radius: 3px;
            }
            QPushButton:hover  { background: #2A2A4A; }
            QPushButton:checked { background: #C9A84C; color: #0D0D1A; }
            QProgressBar {
                background: #111127; border: 1px solid #2A2A4A;
                border-radius: 3px; text-align: center;
            }
            QProgressBar::chunk { background: #C9A84C; }
            QStatusBar { background: #0A0A18; color: #666; font-size: 10px; }
        """)


# ══════════════════════════════════════════════════════════════════════
# SECTION 4 — Standalone Usage Example (no GUI)
# ══════════════════════════════════════════════════════════════════════

def fetch_all_data_standalone(ticker: str):
    """
    Headless example — fetch everything for a ticker and print results.
    Useful for scripting / backtesting outside the GUI.
    """
    import time

    print(f"\n{'='*60}")
    print(f"  Fetching all data for: {ticker}")
    print(f"{'='*60}")

    # ── Live Price ──
    print("\n[1] Live Quote")
    try:
        tk   = yf.Ticker(ticker)
        info = tk.info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev  = info.get("previousClose")
        chg   = round(price - prev, 2) if price and prev else None
        print(f"    Price:   ${price}")
        print(f"    Change:  {chg:+} ({round(chg/prev*100,2):+}%)" if chg else "    Change: N/A")
        print(f"    Sector:  {info.get('sector','N/A')}")
    except Exception as e:
        print(f"    ERROR: {e}")

    # ── OHLCV ──
    print("\n[2] OHLCV (last 5 rows, 1d)")
    try:
        df = yf.Ticker(ticker).history(period="1mo", interval="1d", auto_adjust=True)
        print(df[["Open","High","Low","Close","Volume"]].tail(5).to_string())
    except Exception as e:
        print(f"    ERROR: {e}")

    # ── Technicals ──
    print("\n[3] Technical Indicators (latest values)")
    try:
        df = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        df.ta.ema(length=50, append=True)
        df.ta.ema(length=200, append=True)
        df.ta.bbands(append=True)
        latest = df.iloc[-1]
        print(f"    RSI(14):    {latest.get('RSI_14', 'N/A'):.2f}")
        print(f"    MACD Hist:  {latest.get('MACDh_12_26_9', 'N/A'):.4f}")
        print(f"    EMA 50:     {latest.get('EMA_50', 'N/A'):.2f}")
        print(f"    EMA 200:    {latest.get('EMA_200', 'N/A'):.2f}")
        print(f"    BB Upper:   {latest.get('BBU_20_2.0', 'N/A'):.2f}")
        print(f"    BB Lower:   {latest.get('BBL_20_2.0', 'N/A'):.2f}")
    except Exception as e:
        print(f"    ERROR: {e}")

    # ── Fundamentals ──
    print("\n[4] Key Fundamentals")
    try:
        info = yf.Ticker(ticker).info
        print(f"    P/E (TTM):    {info.get('trailingPE', 'N/A')}")
        print(f"    Forward P/E:  {info.get('forwardPE', 'N/A')}")
        print(f"    D/E Ratio:    {info.get('debtToEquity', 'N/A')}")
        print(f"    Rev Growth:   {info.get('revenueGrowth', 'N/A')}")
        print(f"    Div Yield:    {info.get('dividendYield', 'N/A')}")
        print(f"    ROE:          {info.get('returnOnEquity', 'N/A')}")
        print(f"    Analyst:      {info.get('recommendationKey','N/A').upper()}")
        print(f"    Mean Target:  ${info.get('targetMeanPrice','N/A')}")
    except Exception as e:
        print(f"    ERROR: {e}")


# ══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # ── Run headless demo ──
    if "--headless" in sys.argv:
        ticker = sys.argv[2] if len(sys.argv) > 2 else "NVDA"
        fetch_all_data_standalone(ticker)
        sys.exit(0)

    # ── Launch PyQt6 terminal ──
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SwingTraderTerminal()
    window.show()
    sys.exit(app.exec())
