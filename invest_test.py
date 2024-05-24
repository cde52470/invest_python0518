import os
from dotenv import load_dotenv
from alpha_vantage.timeseries import TimeSeries
import pandas as pd
import pandas_ta as ta

# 加載環境變量
load_dotenv()

# Alpha Vantage API 關鍵字
alpha_client = TimeSeries(key=os.getenv('ALPHA_VANTAGE_API_KEY'), output_format='pandas')

def get_stock_data(symbol):
    # 從Alpha Vantage獲取股票價格數據
    data, meta_data = alpha_client.get_daily(symbol=symbol, outputsize='full')
    # 只考慮收盤價
    close_prices = data['4. close']
    return close_prices.tail(60)  # 獲取最新的60天數據

def calculate_technical_indicators(close_prices):
    # 計算RSI
    rsi = ta.rsi(close_prices, length=14)
    # 計算SMA
    sma = ta.sma(close_prices, length=20)
    # 計算布林帶
    bbands = ta.bbands(close_prices, length=20, std=2)
    return rsi, sma, bbands

def main():
    symbol = input("請輸入股票代碼：")
    close_prices = get_stock_data(symbol)
    rsi, sma, bbands = calculate_technical_indicators(close_prices)
    
    # 檢查並格式化輸出
    rsi_value = rsi.iloc[-1] if not rsi.empty else None
    sma_value = sma.iloc[-1] if not sma.empty else None
    bbu_value = bbands['BBU_20_2.0'].iloc[-1] if 'BBU_20_2.0' in bbands else None
    bbl_value = bbands['BBL_20_2.0'].iloc[-1] if 'BBL_20_2.0' in bbands else None
    
    print(f"股票 {symbol} 的技術指標分析結果:")
    print(f"RSI: {rsi_value:.2f}")
    print(f"日均線 (SMA): {sma_value:.3f}")
    print(f"布林帶上軌: {bbu_value:.12f}")
    print(f"布林帶下軌: {bbl_value:.12f}")

if __name__ == "__main__":
    main()
