// This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
// © M0rty

//@version=4
study("Awesome Heikin Ashi [Morty]", max_labels_count=100)

// inputs
src = input(close, "EMA Source", type=input.source, tooltip="Source of EMA (default: close price)", group="EMA")
length_fast = input(10, "fast length", tooltip="Fast EMA length, adjust it according to different timeframe", group="EMA")
length_slow = input(20, "slow length", tooltip="Slow EMA length, adjust it according to different timeframe", group="EMA")

signal_type = input("ALL", options=["ALL", "Long", "Short"], tooltip="Select signal type", group="Signal")
show_entry_signals = input(true, "Show entry signals", group="Signal")
show_exit_signals = input(true, "Show exit signals", group="Signal")
filter_entry = input(true, "Filter continuous entry signals", tooltip="Filter continues signals, uncheck this if you need more signals", group="Signal")
filter_exit = input(true, "Filter continuous exit signals", tooltip="Filter continues signals, uncheck this if you need more signals", group="Signal")
highlight_bg = input(true, "Highlight background", tooltip="Highlight backgroud based on two EMAs", group="Signal")
lable_size = input(size.auto, "Label size", options=[size.normal, size.auto, size.tiny, size.small], tooltip="You can adjust the label size here", group="Signal")

alert_long  = input(true, "Alert Long Entry", group="Alert")
alert_short = input(true, "Alert Short Entry", group="Alert")
alert_exit = input(true, "Alert Exit Entry", group="Alert")

// get Heikin-Ashi OHLC
[ha_open, ha_high, ha_low, ha_close] = security(heikinashi(syminfo.tickerid), timeframe.period, [open, high, low, close])

// 2 EMAs for trend recognition
ema_fast = ema(src, length_fast)
ema_slow = ema(src, length_slow)

// buy and sell signals
white_body = ha_close > ha_open
black_body = ha_close <= ha_open
has_no_upper_wick = ha_high == ha_open or ha_high == ha_close
has_no_lower_wick = ha_low == ha_open or ha_low == ha_close

// trend recognition based on two EMAs
uptrend = ema_fast > ema_slow
downtrend = ema_fast < ema_slow

// entry signals
// ema cross or pullback in the strong trend
long_entry = crossover(ema_fast, ema_slow) or 
             (uptrend and ha_low[1] <= ema_slow and (white_body and has_no_lower_wick) and (black_body[1] or black_body[2]))

short_entry = crossunder(ema_fast, ema_slow) or 
             (downtrend and ha_high[1] >= ema_slow and (black_body and has_no_upper_wick) and (white_body[1] or white_body[2]))

// filter continuous entry signals
LE = (signal_type == "ALL" or signal_type == "Long")? (filter_entry ? (long_entry and not long_entry[1]) : long_entry) : na
SE = (signal_type == "ALL" or signal_type == "Short")? (filter_entry ? (short_entry and not short_entry[1]) : short_entry) : na

// exit signals
long_exit = uptrend and (black_body and has_no_upper_wick)
short_exit = downtrend and (white_body and has_no_lower_wick)

// filter continuous exit signals
L_exit = (signal_type == "ALL" or signal_type == "Long")? (filter_exit ? (long_exit and not long_exit[1]) : long_exit) : na
S_exit = (signal_type == "ALL" or signal_type == "Short")? (filter_exit ? (short_exit and not short_exit[1]) : short_exit) : na

// stoploss
stoploss_short = highest(high, 5)
stoploss_long = lowest(low, 5)


// ------Plots here--------------------------------------------------
// define colors
green = #26a69a
red = color.red
white = #dddddd
black = #3f3f3f
c = ha_close > ha_open ? white : black

// plot Heikin-Ashi candlesticks
plotcandle(ha_open, ha_high, ha_low, ha_close, color=c)

// plot 2 ema lines
plot(ema_fast, color=green)
plot(ema_slow, color=red)

// highlight background
bgcolor(highlight_bg ? (uptrend ? green : na) : na)
bgcolor(highlight_bg ? (downtrend ? red : na) : na)


// ------Labels------------------------------------------------------
// position of labels
patternLabelPosLow = ha_low - (atr(30) * 0.5)
patternLabelPosHigh = ha_high + (atr(30) * 0.5)

// show entry labels
if show_entry_signals
    if LE
        tt_long_entry_bottom = "Long Entry @" + tostring(close) + "\nStoploss: " + tostring(stoploss_long)
        text_LE = "LE @" + tostring(close) + "\nS/L: " + tostring(stoploss_long)
        label.new(bar_index, patternLabelPosLow, text=text_LE, style=label.style_label_up, color = green, textcolor=color.white, tooltip = tt_long_entry_bottom, size=lable_size, textalign=text.align_left)
        
    if SE
        tt_short_entry_top = "Short Entry @" + tostring(close) + "\nStoploss: " + tostring(stoploss_short)
        text_SE = "SE @" + tostring(close) + "\nS/L: " + tostring(stoploss_short)
        label.new(bar_index, patternLabelPosHigh, text=text_SE, style=label.style_label_down, color = red, textcolor=color.white, tooltip = tt_short_entry_top, size=lable_size, textalign=text.align_left)

// show exit labels
if show_exit_signals
    if L_exit
        label.new(bar_index, patternLabelPosHigh, text="Long\nExit", style=label.style_label_down, color = color.gray, textcolor=color.white, size=lable_size, textalign=text.align_left)
    if S_exit
        label.new(bar_index, patternLabelPosLow, text="Short\nExit", style=label.style_label_up, color = color.gray, textcolor=color.white, size=lable_size, textalign=text.align_left)


// ------Alerts------------------------------------------------------
if alert_long and LE
    tt_long_entry_bottom = "Long Entry @" + tostring(close) + "\nStoploss: " + tostring(stoploss_long)
    alert(tt_long_entry_bottom, alert.freq_once_per_bar_close)
if alert_short and SE
    tt_short_entry_top = "Short Entry @" + tostring(close) + "\nStoploss: " + tostring(stoploss_short)
    alert(tt_short_entry_top, alert.freq_once_per_bar_close)
if alert_exit
    if L_exit
        alert("Long Exit", alert.freq_once_per_bar_close)
    if S_exit
        alert("Short Exit", alert.freq_once_per_bar_close)
