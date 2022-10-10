
# To get a list of latest instruments as csv dump, type in browser the below url:
# https://api.kite.trade/instruments

###### STRATEGY / TRADE PLAN #####
# Trading Style     : Intraday. Positional if MTM is negative.
# Trade Timing      : Entry: Morning 10:30 to 12:00 AM , After noon 1.30 PM to 3.30 PM 
# Trading Capital   : Rs 6,60,000 approx to start with
# Trading Qty       : Min upto 6 lots
# Premarket Routine : None
# Trading Goals     : Short max Nifty OTM Call/Put < 100   
# Time Frame        : 1 min
# Entry Criteria    : Entry post 10:30 AM to 12
# Exit Criteria     : <>  
# Risk Capacity     : <>
# Order Management  : BO orders else MIS/Normal(may need additional exit criteria)

# Strategy 1 : Sell Both Call and Put at 10:08 AM of strike around 150  



import pyotp
from kiteext import KiteExt
import time
import datetime
import os
import sys
import configparser
import pandas as pd
# from kiteconnect import KiteTicker


# Enable logging to file; if log folder is not present create it
if not os.path.exists("./log"):
    os.makedirs("./log")
LOG_FILE = r"./log/kite_options_sell_" + datetime.datetime.now().strftime("%Y%m%d") +".log"
# sys.stdout = sys.stderr = open(LOG_FILE, "a")

# Read parameters and settings from the .ini file
INI_FILE = "kite_options_sell.ini"
cfg = configparser.ConfigParser()
cfg.read(INI_FILE)

user_id = cfg.get("tokens", "user_id")
password = cfg.get("tokens", "password")
totp_key = cfg.get("tokens", "totp_key")

#List of thursdays when its NSE holiday
weekly_expiry_holiday_dates = cfg.get("info", "weekly_expiry_holiday_dates").split(",")


# Get the latest TOTP
toptp = pyotp.TOTP(totp_key).now()

# Authenticate using kite bypass and get Kite object
kite = KiteExt(user_id=user_id, password=password, twofa=toptp)
print(f"toptp={toptp}")


instruments = ["NSE:NIFTY 50","NSE:NIFTY BANK"] 


# Get LTP for NIFTY and the required option strike
inst_ltp = kite.ltp(instruments)
nifty_ltp = inst_ltp['NSE:NIFTY 50']['last_price']
nifty_atm = round(int(nifty_ltp),-2)
int_strike = nifty_atm - 100

# Get next week expiry
expiry_date = datetime.date.today() + datetime.timedelta( ((3-datetime.date.today().weekday()) % 7)+7 )
if str(expiry_date) in weekly_expiry_holiday_dates :
    expiry_date = expiry_date - datetime.timedelta(days=1)

print(f"expiry_date={expiry_date}")

# Get option instrument and its ltp, ohlc
df = pd.DataFrame(kite.instruments("NFO"))

# Get NIFTY ATM strike 
#opt_instrument = 'NFO:' + df[(df.expiry==expiry_date) & (df.name=='NIFTY') & (df.strike==int_strike) & (df.instrument_type=='CE')].tradingsymbol.values[0]

# Get NIFTY ATM strike ltp
#nifty_opt_ltp = kite.ltp(opt_instrument)

# Get NIFTY ATM ohlc
#nifty_opt_ohlc = kite.ohlc(opt_instrument)

nifty_olhc = kite.ohlc(instruments[0])

# print(f"opt_instrument={opt_instrument}")
# print(f"nifty_opt_ltp={nifty_opt_ltp}")
# print(f"nifty_opt_ohlc={nifty_opt_ohlc}")
# print(f"nifty_olhc={nifty_olhc}")

# Get list of CE rounded strikes 300 pts on either side of the option chain
lst_nifty_opt_ce = df[(df.expiry==expiry_date) & (df.name=='NIFTY') & ((df.strike>=nifty_atm-300) & (df.strike<=nifty_atm+300)) & (df.strike%100==0) & (df.instrument_type=='CE')].tradingsymbol.apply(lambda x:'NFO:'+x).tolist()

# Get list of PE rounded strikes 300 pts on either side of the option chain
lst_nifty_opt_pe = df[(df.expiry==expiry_date) & (df.name=='NIFTY') & ((df.strike>=nifty_atm-300) & (df.strike<=nifty_atm+300)) & (df.strike%100==0) & (df.instrument_type=='PE')].tradingsymbol.apply(lambda x:'NFO:'+x).tolist()

# Get ltp for the list of filtered CE strikes 
dict_nifty_opt_ce_ltp = kite.ltp(lst_nifty_opt_ce)

# Get ltp for the list of filtered PE strikes 
dict_nifty_opt_pe_ltp = kite.ltp(lst_nifty_opt_pe)


# Get max NIFTY CE strike <=150
# Need to convert the below to lambda function to get max value lt 150 
for ts,dict_price in dict_nifty_opt_ce_ltp.items():
	dict_price['last_price']

# Get max NIFTY PE strike <=150


print("====== Done ======", datetime.datetime.now())

''' 
kws = kite.kws()
# Got from kite_options_sell.py

try:
    kite.place_order(variety=kite.VARIETY_REGULAR,
                        exchange=kite.EXCHANGE_NFO,
                        tradingsymbol=symbol,
                        transaction_type=kite.TRANSACTION_TYPE_SELL,
                        quantity=list(df["lot_size"])[0],
                        product=kite.PRODUCT_MIS,
                        order_type=kite.ORDER_TYPE_MARKET,
                        validity=kite.VALIDITY_DAY)
    print("Order Placed")
except Exception as e:
    print(f"{e}")

'''