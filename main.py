import ccxt
import config
import schedule
import pandas as pd
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

import warnings
warnings.filterwarnings('ignore')

from datetime import datetime
import time

exchange = ccxt.binance({
    "apiKey": config.BINANCE_API_KEY,
    "secret": config.BINANCE_SECRET_KEY
})
exchange.set_sandbox_mode(True)

# calculate heiken ashi Low
def haLow(row, df):
        ha_low = min(df.iloc[row]['low'], df.iloc[row]['open'], df.iloc[row]['close'])
        return ha_low

# calculate heiken ashi High
def haHigh(row, df): 
        ha_high = max(df.iloc[row]['high'], df.iloc[row]['open'], df.iloc[row]['close'])
        return ha_high 

# calculate heiken ashi Open
def haOp(row, df): 
        data = df.iloc[row-1]['open'] + df.iloc[row-1]['close']
        ha_op = data/2
        return ha_op

# calculate heiken ashi Close
def haClose(row, df):
        data = df.iloc[row]['open'] + df.iloc[row]['high'] + df.iloc[row]['low'] + df.iloc[row]['close']
        ha_close = data/4
        return ha_close


# heiken ashi strategy
def heiken_ashi(df):
    for x in range(len(df.index)): 
        df.at[x, 'low'] = haLow(x, df)
        df.at[x, 'high'] = haHigh(x, df)
        df.at[x, 'open'] = haOp(x, df)
        df.at[x, 'close'] = haClose(x, df)
        
    df['in_uptrend'] = True

    for current in range(1, len(df.index)):
        previous = current - 1
        if df['close'][current] > df['close'][previous]:
            df['in_uptrend'][current] = True
        elif df['close'][current] < df['close'][previous]:
            df['in_uptrend'][current] = False
        else:
            df['in_uptrend'][current] = df['in_uptrend'][previous]
    return df


# đánh dấu khi entry và exit
in_position = False

# check buy sell signals
def check_buy_sell_signals(df):
    global in_position

    print("checking for buy and sell signals")
    print(df.tail(5))
    last_row_index = len(df.index) - 1
    previous_row_index = last_row_index - 1

    if df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]:
        print("changed to uptrend, buy")
        if not in_position:
            order = exchange.create_market_buy_order('BTCUSDT', 0.05)
            print(order)
            in_position = True
        else:
            print("already in position, nothing to do")
    
    if not df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index]:
        if in_position:
            print("changed to downtrend, sell")
            order = exchange.create_market_sell_order('BTCUSDT', 0.05)
            print(order)
            in_position = False
        else:
            print("You aren't in position, nothing to sell")

def run_bot():
    print(f"Fetching new bars for {datetime.now().isoformat()}")
    bars = exchange.fetch_ohlcv('BTCUSDT', timeframe='1m', limit=100)
    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # print(df)
    heiken_ashi_data = heiken_ashi(df)
    check_buy_sell_signals(heiken_ashi_data)
    
    

# mỗi 2 giây chạy một lần  
schedule.every(2).seconds.do(run_bot)


while True:
    schedule.run_pending()
    # time sleep
    time.sleep(1)