import os
from dotenv import load_dotenv
from alpha_vantage.timeseries import TimeSeries
import pandas as pd
import pandas_ta as ta
import openai
import logging

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


# 加載環境變量
load_dotenv()

# Alpha Vantage API 關鍵字
alpha_client = TimeSeries(key=os.getenv('ALPHA_VANTAGE_API_KEY'), output_format='pandas')
openai_api_key = os.getenv('OPENAI_API_KEY')
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

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


def consult_chatgpt(rsi, sma, bbu, bbl):
    prompt = f"给定以下股票技术指标，请评估此股票是否值得购买（0-10分）：RSI: {rsi:.2f}, SMA: {sma:.3f}, 布林带上轨: {bbu:.12f}, 布林带下轨: {bbl:.12f}。"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # 确保使用的是聊天模型
            messages=[{"role": "user", "content": prompt}],
            api_key=os.getenv("OPENAI_API_KEY")
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return "生成建议时出错。"



@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info(f"Received a request with body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    app.logger.info(f"Handling message: {text}")  # 日志输出接收到的消息内容

    if text.startswith("分析股票"):
        parts = text.split()
        if len(parts) >= 2:
            ticker = parts[1].upper()
            app.logger.info(f"Analyzing ticker: {ticker}")  # 日志输出正在分析的股票代码

            try:
                close_prices = get_stock_data(ticker)
                rsi, sma, bbands = calculate_technical_indicators(close_prices)  # 确保这里正确解包
                rsi_value = rsi.iloc[-1] if not rsi.empty else None
                sma_value = sma.iloc[-1] if not sma.empty else None
                bbu_value = bbands['BBU_20_2.0'].iloc[-1] if 'BBU_20_2.0' in bbands else None
                bbl_value = bbands['BBL_20_2.0'].iloc[-1] if 'BBL_20_2.0' in bbands else None

                response_text = (f"股票 {ticker} 的技术指标分析结果:\n"
                                 f"RSI: {rsi_value:.2f}\n"
                                 f"日均线 (SMA): {sma_value:.3f}\n"
                                 f"布林带上轨: {bbu_value:.12f}\n"
                                 f"布林带下轨: {bbl_value:.12f}")

                advice = consult_chatgpt(rsi_value, sma_value, bbu_value, bbl_value)
                response_text += f"\n根据 ChatGPT 的评估：{advice}"

                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=response_text)
                )
            except Exception as e:
                error_message = f"无法获取股票数据或处理过程中出错：{str(e)}"
                app.logger.error(error_message)  # 日志输出错误信息
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=error_message)
                )
        else:
            error_message = "请输入正确的股票代码，格式为：分析股票 股票代码"
            app.logger.error(error_message)  # 日志输出错误信息
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=error_message)
            )
    else:
        welcome_message = "欢迎使用股票分析机器人，请输入正确的格式以进行股票分析，例如：分析股票 AAPL"
        app.logger.info(welcome_message)  # 日志输出欢迎信息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=welcome_message)
        )







# def main():
    # symbol = input("請輸入股票代碼：")
    # close_prices = get_stock_data(symbol)
    # rsi, sma, bbands = calculate_technical_indicators(close_prices)
    
    # # 檢查並格式化輸出
    # rsi_value = rsi.iloc[-1] if not rsi.empty else None
    # sma_value = sma.iloc[-1] if not sma.empty else None
    # bbu_value = bbands['BBU_20_2.0'].iloc[-1] if 'BBU_20_2.0' in bbands else None
    # bbl_value = bbands['BBL_20_2.0'].iloc[-1] if 'BBL_20_2.0' in bbands else None
    
    # print(f"股票 {symbol} 的技術指標分析結果:")
    # print(f"RSI: {rsi_value:.2f}")
    # print(f"日均線 (SMA): {sma_value:.3f}")
    # print(f"布林帶上軌: {bbu_value:.12f}")
    # print(f"布林帶下軌: {bbl_value:.12f}\n")

    # # 咨詢 ChatGPT
    # # advice = consult_chatgpt(rsi_value, sma_value, bbu_value, bbl_value)
    # # print(f"根據 ChatGPT 的評估，此股票的購買評分為: \n{advice}")
    # advice = consult_chatgpt(rsi_value, sma_value, bbu_value, bbl_value)
    # explanation = advice[:-1]  # 移除原始评分句子
    # score = advice.split("。")[-2]  # 从最后第二句获取评分句子

    # print("以下為系統的評估與分析:")
    # print(explanation)  # 输出评价解释部分
    # print("\n" + score + "。")  # 输出评分，前加空行


# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
    # 这里简单回复收到的消息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)