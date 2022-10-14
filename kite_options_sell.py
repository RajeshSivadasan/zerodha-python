
# To get a list of latest instruments as csv dump, type in browser the below url:
# https://api.kite.trade/instruments

###### STRATEGY / TRADE PLAN #####
# Trading Style     : Intraday. Positional if MTM is negative.
# Trade Timing      : Entry: Morning 10:30 to 12:00 AM , After noon 1.30 PM to 3.30 PM 
# Trading Capital   : Rs 6,60,000 approx to start with
# Script            : Nifty Options
# Trading Qty       : Min upto 6 lots
# Premarket Routine : None
# Trading Goals     : Short max Nifty OTM Call/Put < 100   
# Time Frame        : 1 min
 
# Risk Capacity     : <>
# Order Management  : BO orders else MIS/Normal(may need additional exit criteria)

# Long or Short Bias decision:
# Long Bias  : When Nifty/Call opens above r1
# Short Bias : When Nifty/Call opens below  Pivot. 


# Strategy 0:
# Instead of Pivot point levels, use (open -  close) to see the % rise or fall and decide bias and 20/30/40/50 pts entry targets
# So no need for getting historic data and all. 

# Strategy 1 (Neutral Bias/Small Short Bias): Sell Both Call and Put at 10:08 AM of strike around 150  
# Entry Criteria    : Entry post 10:30 AM to 12;
# If crossed R3 sell next strike
# Exit Criteria     : 1% of Margin used (1100 per lot) or 75% at first support   

# Strategy 2 (Long Biased): 
# Entry (Option 1) :Sell at R2(Base Lot), at R3(Base Lot*1.5) , at R4(Base Lot*2)  
# Entry (Option 2-Wed,Thu) :Sell at R2(Base Lot), at R2+30(Base Lot) , Sell next Strike at NextStrikPrice=Martek+5 (Base Lot) 
# , at NextStrikPrice+30(Base Lot), at NextToNextStrikPrice(Market)+5(Base Lot),at NextToNextStrikPrice30(Base Lot)
# Entry (Option 2-Fri,Mon,Tue) :Sell at R2(Base Lot), at R2+30(Base Lot) , Sell next Strike at NextStrikPrice=Martek+5 (Base Lot) 
# , at NextStrikPrice+30(Base Lot), at NextToNextStrikPrice(Market)+5(Base Lot),at NextToNextStrikPrice30(Base Lot)
# or Use Golden Ratio (Fibonacci series) for entry prices

# Exit Criteria    : Book 75% of Qty at 1% of Margin used (Rs 1200 per lot) or 75% at first support if profit is above



import pyotp
from kiteext import KiteExt
import time
import datetime
import os
import sys
import configparser
import pandas as pd
# from kiteconnect import KiteTicker    # Used for websocket only


# Enable logging to file; if log folder is not present create it
if not os.path.exists("./log"):
    os.makedirs("./log")
# Initialise logging and set console and error target as log file
LOG_FILE = r"./log/kite_options_sell_" + datetime.datetime.now().strftime("%Y%m%d") +".log"
# sys.stdout = sys.stderr = open(LOG_FILE, "a")



# Initialise Variables/parameters
# -------------------------------
# Read parameters and settings from the .ini file
INI_FILE = "kite_options_sell.ini"
cfg = configparser.ConfigParser()
cfg.read(INI_FILE)

user_id = cfg.get("tokens", "user_id")
password = cfg.get("tokens", "password")
totp_key = cfg.get("tokens", "totp_key")

nifty_opt_ce_max_price_limit = int(cfg.get("info", "nifty_opt_ce_max_price_limit"))
nifty_opt_pe_max_price_limit = int(cfg.get("info", "nifty_opt_pe_max_price_limit"))

interval = int(cfg.get("info", "interval"))   #3min, 5min, 10min ...

#List of thursdays when its NSE holiday
weekly_expiry_holiday_dates = cfg.get("info", "weekly_expiry_holiday_dates").split(",")

# Get NIfty and BankNifty instrument data
instruments = ["NSE:NIFTY 50","NSE:NIFTY BANK"] 

# Login and get kite object
# -------------------------
# Get the latest TOTP
toptp = pyotp.TOTP(totp_key).now()

# Authenticate using kite bypass and get Kite object
kite = KiteExt(user_id=user_id, password=password, twofa=toptp)
print(f"toptp={toptp}")



# Get current/next week expiry 
# ----------------------------
# if today is tue or wed then use next expiry else use current expiry. .isoweekday() 1 = Monday, 2 = Tuesday
if datetime.date.today().isoweekday()  in (2,3,4):
    expiry_date = datetime.date.today() + datetime.timedelta( ((3-datetime.date.today().weekday()) % 7)+7 )
else:
    expiry_date = datetime.date.today() + datetime.timedelta( ((3-datetime.date.today().weekday()) % 7))

if str(expiry_date) in weekly_expiry_holiday_dates :
    expiry_date = expiry_date - datetime.timedelta(days=1)

print(f"expiry_date={expiry_date}")

# Get option instruments for the expiry
df = pd.DataFrame(kite.instruments("NFO"))
df = df[(df.segment=='NFO-OPT') & (df.expiry==expiry_date)] 



# To find nifty open range to decide market bias (Long,Short,Neutral)
nifty_olhc = kite.ohlc(instruments[0])


# print(f"opt_instrument={opt_instrument}")
# print(f"nifty_opt_ltp={nifty_opt_ltp}")
# print(f"nifty_opt_ohlc={nifty_opt_ohlc}")
# print(f"nifty_olhc={nifty_olhc}")


instrument_nifty_opt_ce = ""
instrument_nifty_opt_pe = ""

def getOption():
    '''
    Gets the option instruments(instrument_nifty_opt_ce,instrument_nifty_opt_pe) 
    for the required strike as per the parameters and and calculates pivot points for entry and exit
    '''
    print("In getOption():")
    global instrument_nifty_opt_ce, instrument_nifty_opt_pe

    # Get Nifty ATM
    inst_ltp = kite.ltp(instruments)
    nifty_ltp = inst_ltp['NSE:NIFTY 50']['last_price']
    nifty_atm = round(int(nifty_ltp),-2)

    # Find option stike for entry 
    #----------------------------

    # Get list of +- 300 stikes to filter the required price range strike
    # Get list of CE/PE rounded strikes 300 pts on either side of the option chain
    lst_nifty_opt = df[(df.name=='NIFTY') & ((df.strike>=nifty_atm-300) & (df.strike<=nifty_atm+300)) & (df.strike%100==0) ].tradingsymbol.apply(lambda x:'NFO:'+x).tolist()

    # Get ltp for the list of filtered CE/PE strikes 
    dict_nifty_opt_ltp = kite.ltp(lst_nifty_opt)

    # Convert the option ltp dict to dataframe for filtering option
    df_nifty_opt = pd.DataFrame.from_dict(dict_nifty_opt_ltp,orient='index')

    df_nifty_opt['type']= df_nifty_opt.index.str[-2:]   # Create type column
    df_nifty_opt['symbol'] = df_nifty_opt.index         # Create symbol column

    # Get the CE/PE instrument data(instrument_token,last_price,type,symbol) where last_price is maximum but less than equal to option max price limit (e.g <=200)
    instrument_nifty_opt_ce = df_nifty_opt[(df_nifty_opt.type=='CE') & (df_nifty_opt.last_price==df_nifty_opt[(df_nifty_opt.type=='CE') & (df_nifty_opt.last_price<=nifty_opt_ce_max_price_limit)].last_price.max())]
    instrument_nifty_opt_pe = df_nifty_opt[(df_nifty_opt.type=='PE') & (df_nifty_opt.last_price==df_nifty_opt[(df_nifty_opt.type=='PE') & (df_nifty_opt.last_price<=nifty_opt_pe_max_price_limit)].last_price.max())]

    print("Call selected is:",instrument_nifty_opt_ce)
    print("Put  selected is :",instrument_nifty_opt_pe)


    # Get CE instrument token (instrument_token)
    instrument_token_ce = instrument_nifty_opt_ce.instrument_token[-1]

    # Get CE instrument token (instrument_token)
    instrument_token_pe = instrument_nifty_opt_pe.instrument_token[-1]

    # Get previous day data for CE and PE
    # We will get last five days of data and take the latest one so that even if previous day is a holiday we will get next trading day data
    from_date = datetime.date.today()-datetime.timedelta(days=5)
    to_date = datetime.date.today()-datetime.timedelta(days=1)
    df_hist_ce = pd.DataFrame(kite.historical_data(instrument_token_ce,from_date,to_date,'day'))

    print(f"Previous day OHLC for {instrument_token_ce}:")
    print(df_hist_ce.iloc[-1])  #Previous days ohlc data


    # Calculate Pivot Points for CE
    # nifty_opt_ce_last_open = df_hist_ce.iloc[-1].open
    nifty_opt_ce_last_high = df_hist_ce.iloc[-1].high
    nifty_opt_ce_last_low = df_hist_ce.iloc[-1].low
    nifty_opt_ce_last_close = df_hist_ce.iloc[-1].close

    nifty_opt_ce_range = nifty_opt_ce_last_high - nifty_opt_ce_last_low
    nifty_opt_ce_pp = round((nifty_opt_ce_last_high + nifty_opt_ce_last_low + nifty_opt_ce_last_close)/3)
    nifty_opt_ce_r1 = round((2 * nifty_opt_ce_pp) - nifty_opt_ce_last_low)
    nifty_opt_ce_r2 = round(nifty_opt_ce_pp + nifty_opt_ce_range)
    nifty_opt_ce_r3 = round(nifty_opt_ce_pp + 2 * nifty_opt_ce_range)
    # ???? Check if we need to divide / 2 and then round
    nifty_opt_ce_r4 = nifty_opt_ce_r3 + round((nifty_opt_ce_r3 - nifty_opt_ce_r2))  


    # nifty_opt_ce_open = kite.ohlc(instrument_token_ce)[str(instrument_token_ce)]['ohlc']['open']
    # nifty_opt_ce_gap_updown = nifty_opt_ce_open - nifty_opt_ce_last_close

    print(f"Pivot Points for {instrument_token_ce}:")
    print(nifty_opt_ce_pp,nifty_opt_ce_r1,nifty_opt_ce_r2,nifty_opt_ce_r3,nifty_opt_ce_r4)



# Get current tradable Option details. Can be used during anytime of the day   
getOption()

######## Strategy 1: Sell both CE and PE
# Keep 0.4 (40%) of the ltp as the SL for both
# Place 

######## Strategy 2: Sell CE at pivot resistance points , R2(qty=baselot) , R3(qty=baselot*2), R3(qty=baselot*3)

while True:
    # Process as per start of market timing
    cur_HHMM = int(datetime.datetime.now().strftime("%H%M"))
    if cur_HHMM > 914:
        cur_min = datetime.datetime.now().minute 

        # Below if block will run after every time interval specifie in the .ini file
        if( cur_min % interval == 0 and flg_min != cur_min):
            flg_min = cur_min     # Set the minute flag to run the code only once post the interval
            t1 = time.time()      # Set timer to record the processing time of all the indicators

        if cur_HHMM > 1530 and cur_HHMM < 1532 :   # Exit the program post NSE closure
            print("Shutting down Algo at",datetime.datetime.now())
            sys.exit()

    time.sleep(10)   # reduce to accomodate the processing delay, if any


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