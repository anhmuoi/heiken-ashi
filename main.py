import ccxt
import config
import schedule
import pandas as pd
import pandas_ta as ta
import talib as ta
from time import ctime


pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

import warnings
warnings.filterwarnings('ignore')

from datetime import datetime
import time

exchange = ccxt.binance({
    "apiKey": config.BINANCE_API_KEY,
    "secret": config.BINANCE_SECRET_KEY,
    'options': { 'adjustForTimeDifference': True }
})
exchange.set_sandbox_mode(True)


# heiken ashi strategy
def heiken_ashi(df, ema_fast, ema_slow):




    df['HA_Close']=(df['open']+ df['high']+ df['low']+ df['close'])/4
    df['HA_Open']=(df['open']+df['close'])/2   
    #df['HA_Open'][1:]= (df['HA_Open'].shift(1)+df['HA_Close'].shift(1))/2 
    for i in range(1, len(df)):
        df['HA_Open'][i]=(df['HA_Open'][i-1]+df['HA_Close'][i-1])/2 
    df['HA_High']=df[['HA_Open','HA_Close','high']].max(axis=1)
    df['HA_Low']=df[['HA_Open','HA_Close','low']].min(axis=1)

    for current in range(20, len(df.index)):
        if df['HA_Close'][current] > df['HA_Open'][current]:
            df.at[current, 'white_body'] = True
            df.at[current, 'black_body'] = False
        elif df['HA_Close'][current] <= df['HA_Open'][current]:
            df.at[current, 'white_body'] = False
            df.at[current, 'black_body'] = True

        if ema_fast[current] > ema_slow[current]:
            df.at[current, 'uptrend'] = True
            df.at[current, 'downtrend'] = False
        elif ema_fast[current] <= ema_slow[current]:
            df.at[current, 'uptrend'] = False
            df.at[current, 'downtrend'] = True

        if df['HA_High'][current] == df['HA_Open'][current]:
            df.at[current, 'has_lower_wick'] = True
            df.at[current, 'has_upper_wick'] = False
        elif df['HA_Low'][current] == df['HA_Open'][current]:
            df.at[current, 'has_lower_wick'] = False
            df.at[current, 'has_upper_wick'] = True
        else:
            df.at[current, 'has_upper_wick'] = False
            df.at[current, 'has_lower_wick'] = False

        if df['uptrend'][current] and df['HA_Low'][current-1] <= ema_slow[current] and ((df['white_body'][current] and df['has_upper_wick'][current]) and (df['black_body'][current-1] or df['black_body'][current-2])):
            df.at[current, 'long_entry'] = True
            df.at[current, 'short_entry'] = False
            df.at[current, 'long_exit'] = False
            df.at[current, 'short_exit'] = False
        elif df['downtrend'][current] and df['HA_High'][current-1] >= ema_slow[current] and (df['black_body'][current] and df['has_lower_wick'][current] and (df['white_body'][current-1] or df['white_body'][current-2])):
            df.at[current, 'long_entry'] = False
            df.at[current, 'short_entry'] = True
            df.at[current, 'long_exit'] = False
            df.at[current, 'short_exit'] = False
        elif df['uptrend'][current] and (df['black_body'][current] and df['has_lower_wick'][current]):
            df.at[current, 'long_entry'] = False
            df.at[current, 'short_entry'] = False
            df.at[current, 'long_exit'] = True
            df.at[current, 'short_exit'] = False
        elif df['downtrend'][current] and (df['white_body'][current] and df['has_upper_wick'][current]):
            df.at[current, 'long_entry'] = False
            df.at[current, 'short_entry'] = False
            df.at[current, 'long_exit'] = False
            df.at[current, 'short_exit'] = True
        else:
            df.at[current, 'long_entry'] = False
            df.at[current, 'short_entry'] = False
            df.at[current, 'long_exit'] = False
            df.at[current, 'short_exit'] = False

        
    return df


# đánh dấu khi entry và exit
in_position = False

# check buy sell signals
def check_buy_sell_signals(df, stoploss_short, stoploss_long, df_original):
    global signal_type

    last_row_index = len(df.index) - 1

    if df['long_entry'][last_row_index]:
        print("long entry")
        if signal_type != "long" and (exchange.fetch_balance()['BNB']['free'] >= 0.001):
            order = exchange.create_market_buy_order('BTC/USDT', 0.0005)
            print(order)
            signal_type = "long"
        else:
            print("already long or not enough money nothing to do")
    elif df['short_entry'][last_row_index] or (df['high'][last_row_index] >= stoploss_short):
        if signal_type != "short" and (exchange.fetch_balance()['BTC']['free'] >= 0.001):
            print("short entry")
            order = exchange.create_market_sell_order('BTC/USDT', 0.0005)
            print(order)
            signal_type = "short"
        else:
            print("already short, nothing to do")
    elif df['long_exit'][last_row_index] or (df['low'][last_row_index] <= stoploss_long):
        if signal_type != "short"  and (exchange.fetch_balance()['BTC']['free'] >= 0.001):
            print("long exit")
            order = exchange.create_market_sell_order('BTC/USDT', 0.0005)
            print(order)
            signal_type = "short"
        else:
            print("You aren't in position, nothing to sell")     
    elif df['short_exit'][last_row_index]:
        if signal_type != "long" and (exchange.fetch_balance()['BTC']['free'] >= 0.001):
            print("short exit")
            order = exchange.create_market_buy_order('BTC/USDT', 0.0005)
            print(order)
            signal_type = "long"
        else:
            print("not enough money, nothing to sell")



signal_type = ''

def calculate_ema (df, period):
    ema = df['close'].ewm(span=period, adjust=False).mean()
    return ema

def run_bot():
    print(f"Fetching new bars for {datetime.now().isoformat()}")
    # order = exchange.create_order(symbol='BTC/USDT',type='market',amount=0.01,side='buy')
    # print(order)
    bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', limit=100)

    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    df_original = df.copy()

    # stoploss_short = highest(high, 5)
    # stoploss_long = lowest(low, 5)  
    stoploss_short = max(df['high'].tail(5))
    stoploss_long = min(df['low'].tail(5))

    # ema_fast = calculate_ema(df, 10)
    # ema_slow = calculate_ema(df, 20)
    ema_fast = ta.EMA(df['close'], timeperiod=10)
    ema_slow = ta.EMA(df['close'], timeperiod=20)


    # print(df)
    heiken_ashi_data = heiken_ashi(df, ema_fast, ema_slow)
    # heiken_ashi_data = heiken_ashi_data.loc[:, ['timestamp', 'uptrend', 'downtrend', 'long_entry', 'short_entry', 'long_exit', 'short_exit']]
    # print(heiken_ashi_data)
    # for index, row in heiken_ashi_data.iterrows():
    #     if row['long_entry'] == True or row['short_entry'] == True or row['long_exit'] == True or row['short_exit'] ==True :
    #         print(row)
    print(heiken_ashi_data)
    check_buy_sell_signals(heiken_ashi_data,stoploss_short,stoploss_long, df_original)
    

# mỗi 2 giây chạy một lần  
schedule.every(2).seconds.do(run_bot)


while True:
    schedule.run_pending()
    # time sleep
    time.sleep(1)