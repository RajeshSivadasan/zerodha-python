
# To get a list of latest instruments as csv dump, type in browser the below url:
# https://api.kite.trade/instruments


# Script to be scheduled at 9:14 AM IST
# Can run premarket advance and decline check to find the market sentiment
#  
###### STRATEGY / TRADE PLAN #####
# Trading Style     : Intraday. Positional if MTM is negative(Use Mean reversion)
# Trade Timing      : Entry: Morning 10:30 to 12:00 AM , After noon 1.30 PM to 3.30 PM 
# Trading Capital   : Rs 6,60,000 approx to start with
# Script            : Nifty Options
# Trading Qty       : Min upto 6 lots
# Premarket Routine : None
# Trading Goals     : Short max Nifty OTM Call/Put < 100   
# Time Frame        : 1 min
 
# Risk Capacity     : <>
# Order Management  : 

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

# TO DO
# net_margin_utilised =  (abs(pos)/50) * 100000   # lot size to be parameterised for nifty/bank


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
# sys.stdout = sys.stderr = open(LOG_FILE, "a") # use flush=True parameter in print statement if values are not seen in log file
print(f"Logging to file :{LOG_FILE}",flush=True)


########################################################
#        Initialise Variables/parameters
########################################################
# Read parameters and settings from the .ini file
INI_FILE = "kite_options_sell.ini"
cfg = configparser.ConfigParser()
cfg.read(INI_FILE)

user_id = cfg.get("tokens", "user_id")
password = cfg.get("tokens", "password")
totp_key = cfg.get("tokens", "totp_key")

nifty_opt_ce_max_price_limit = int(cfg.get("info", "nifty_opt_ce_max_price_limit")) # 105
nifty_opt_pe_max_price_limit = int(cfg.get("info", "nifty_opt_pe_max_price_limit")) # 105

short_strangle_time = int(cfg.get("info", "short_strangle_time"))   # 925
short_strangle_flag = False

# Time interval e.g 2min, 3min, 5min, 10min ...
interval = int(cfg.get("info", "interval"))   # 2

# profit target percentage of the utilised margin
profit_target_perc = float(cfg.get("info", "profit_target_perc"))  # 0.1 

loss_limit_perc = float(cfg.get("info", "loss_limit_perc")) # 40

print(f"profit_target_perc={profit_target_perc}, loss_limit_perc={loss_limit_perc}")

#List of thursdays when its NSE holiday
weekly_expiry_holiday_dates = cfg.get("info", "weekly_expiry_holiday_dates").split(",") # 2023-01-26,2023-03-30,2024-08-15

# List of days in number for which next week expiry needs to be selected, else use current week expiry
next_week_expiry_days = list(map(int,cfg.get("info", "next_week_expiry_days").split(",")))

# Get base lot and qty 
nifty_opt_base_lot = int(cfg.get("info", "nifty_opt_base_lot"))         # 1
nifty_opt_per_lot_qty = int(cfg.get("info", "nifty_opt_per_lot_qty"))   # 50


# Get NIfty and BankNifty instrument data
instruments = ["NSE:NIFTY 50","NSE:NIFTY BANK"] 



# Login and get kite object
# -------------------------
# Get the latest TOTP
totp = pyotp.TOTP(totp_key).now()
twoFA = f"{int(totp):06d}" if len(totp) <=5 else totp   # Suffix zeros if length of the totp is less than 5 digits

# Authenticate using kite bypass and get Kite object
kite = KiteExt(user_id=user_id, password=password, twofa=twoFA)
print(f"totp={twoFA}")



# Get current/next week expiry 
# ----------------------------
# if today is tue or wed then use next expiry else use current expiry. .isoweekday() 1 = Monday, 2 = Tuesday
if datetime.date.today().isoweekday()  in (next_week_expiry_days):  # next_week_expiry_days = 2,3,4 
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


########################################################
#        Declare Functions
########################################################
def get_options():
    '''
    Gets the call and put option instruments(instrument_nifty_opt_ce,instrument_nifty_opt_pe) 
    for the required strike as per the parameters and and calculates pivot points for entry and exit
    '''
    print("In get_options():")
    global instrument_nifty_opt_ce, instrument_nifty_opt_pe

    # Get Nifty ATM
    inst_ltp = kite.ltp(instruments)
    nifty_ltp = inst_ltp['NSE:NIFTY 50']['last_price']
    nifty_atm = round(int(nifty_ltp),-2)

    # Find option stike for entry 
    #----------------------------

    # Get list of +- 300 stikes to filter the required price range strike
    # Get list of CE/PE rounded strikes 300 pts on either side of the option chain
    lst_nifty_opt = df[(df.name=='NIFTY') & ((df.strike>=nifty_atm-500) & (df.strike<=nifty_atm+500)) & (df.strike%100==0) ].tradingsymbol.apply(lambda x:'NFO:'+x).tolist()

    # Get ltp for the list of filtered CE/PE strikes 
    dict_nifty_opt_ltp = kite.ltp(lst_nifty_opt)

    # Convert the option ltp dict to dataframe for filtering option
    df_nifty_opt = pd.DataFrame.from_dict(dict_nifty_opt_ltp,orient='index')

    df_nifty_opt['type']= df_nifty_opt.index.str[-2:]   # Create type column
    df_nifty_opt['symbol'] = df_nifty_opt.index         # Create symbol column

    # Get the CE/PE instrument data(instrument_token,last_price,type,symbol) where last_price is maximum but less than equal to option max price limit (e.g <=200)
    df_instrument_nifty_opt_ce = df_nifty_opt[(df_nifty_opt.type=='CE') & (df_nifty_opt.last_price==df_nifty_opt[(df_nifty_opt.type=='CE') & (df_nifty_opt.last_price<=nifty_opt_ce_max_price_limit)].last_price.max())]
    df_instrument_nifty_opt_pe = df_nifty_opt[(df_nifty_opt.type=='PE') & (df_nifty_opt.last_price==df_nifty_opt[(df_nifty_opt.type=='PE') & (df_nifty_opt.last_price<=nifty_opt_pe_max_price_limit)].last_price.max())]


    print("Call selected is:",df_instrument_nifty_opt_ce)
    print("Put  selected is :",df_instrument_nifty_opt_pe)


    # Get CE instrument token (instrument_token)
    instrument_token_ce = df_instrument_nifty_opt_ce.instrument_token[-1]

    # Get CE instrument token (instrument_token)
    instrument_token_pe = df_instrument_nifty_opt_pe.instrument_token[-1]

    # Get previous day data for CE and PE
    # We will get last five days of data and take the latest one so that even if previous day is a holiday we will get next trading day data
    from_date = datetime.date.today()-datetime.timedelta(days=5)
    to_date = datetime.date.today()-datetime.timedelta(days=1)
    df_hist_ce = pd.DataFrame(kite.historical_data(instrument_token_ce,from_date,to_date,'day'))

    print(f"Previous day OHLC for {df_instrument_nifty_opt_ce.symbol[-1]}:")
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

    print(f"Pivot Points for {df_instrument_nifty_opt_ce.symbol[-1]}:")
    print(nifty_opt_ce_pp,nifty_opt_ce_r1,nifty_opt_ce_r2,nifty_opt_ce_r3,nifty_opt_ce_r4)
    
    # Add pivot points to the instrument df
    # instrument_nifty_opt_ce[['PP','R1','R2','R3','R4']] = pd.DataFrame([[nifty_opt_ce_pp, nifty_opt_ce_r1, nifty_opt_ce_r2, nifty_opt_ce_r3, nifty_opt_ce_r4]], index=instrument_nifty_opt_ce.index)

    df_instrument_nifty_opt_ce.loc[df_instrument_nifty_opt_ce.index[-1],['PP','R1','R2','R3','R4']] = nifty_opt_ce_pp, nifty_opt_ce_r1, nifty_opt_ce_r2, nifty_opt_ce_r3, nifty_opt_ce_r4


    # Add ohlc data and last_price to the instrument df
    dict_tmp =  kite.ohlc(instrument_token_ce).get(str(instrument_token_ce))
    df_instrument_nifty_opt_ce = df_instrument_nifty_opt_ce.join(pd.DataFrame(dict_tmp['ohlc'], index=df_instrument_nifty_opt_ce.index))

    print("df_instrument_nifty_opt_ce:")
    print(df_instrument_nifty_opt_ce)

    # df_instrument_nifty_opt_ce = df_instrument_nifty_opt_ce.copy(deep=False)

    # tmp = float(dict_tmp['last_price'])
    # print(f"tmp={tmp}")
    # df_instrument_nifty_opt_ce.last_price[-1] = tmp
    # df_instrument_nifty_opt_ce['last_price'].iloc[-1] = float(dict_tmp['last_price'])
    # df_instrument_nifty_opt_ce.last_price[-1] = float(dict_tmp['last_price'])
    df_instrument_nifty_opt_ce.loc[df_instrument_nifty_opt_ce.index[-1],'last_price'] = float(dict_tmp['last_price'])

    print("df_instrument_nifty_opt_ce:=")
    print(df_instrument_nifty_opt_ce)


def place_call_orders():
    '''
    Place call orders and targets based on pivots/levels '''
    if instrument_nifty_opt_ce.R1>instrument_nifty_opt_ce.limit_price:
        qty = nifty_opt_base_lot * nifty_opt_per_lot_qty
        place_order(instrument_nifty_opt_ce.symbol,  )


def runShortStrangle():
    '''Runs short strangle at a given price range'''
    # Have to rethink about this strategy

def place_order(symbol,qty,transaction_type=kite.TRANSACTION_TYPE_SELL,order_type=kite.ORDER_TYPE_LIMIT,limit_price=None,tag="Algo"):
    try:
        order_id = kite.place_order(variety=kite.VARIETY_REGULAR,
                            exchange=kite.EXCHANGE_NFO,
                            tradingsymbol=symbol,
                            transaction_type=transaction_type,
                            quantity=qty,
                            product=kite.PRODUCT_NRML,
                            order_type=order_type,
                            price=limit_price,
                            validity=kite.VALIDITY_DAY,
                            tag=tag
                            )

        print(f"Order Placed. order_id={order_id}")
        return order_id
    except Exception as e:
        print(f"place_order(): Error placing order. {e}")


def process_orders(place_call_orders=False):
    '''Check the status of orders/squareoff/add positions'''

    print("In process_orders():")

    mtm = 0
    pos = 0

    # Check MTM price with the actual on portal
    df_pos = get_positions() 
    print(f"df_pos={df_pos}")
    
    if df_pos.empty:
        print("No Positions found.")
        if place_call_orders:
            # Refresh call and put 
            get_options()
            place_call_orders()

    else:

        mtm , pos = df_pos.loc[0,['m2m','quantity']]   # Get MTM and Net Positon
        
        print(f"pos={pos}")


        if abs(pos)>0:

            # net_margin_utilised = round(pd.DataFrame(kite.margins()).equity.utilised.get('debits')) 
            # Using the below as kite considers the margins blocked for open orders as well
            net_margin_utilised =  (abs(pos)/50) * 100000   # lot size to be parameterised for nifty/bank
            
            profit_target = round(net_margin_utilised * (profit_target_perc/100))
            print(f"mtm={mtm}, pos={pos}, net_margin_utilised={net_margin_utilised}, profit_target={profit_target}")
            
            if mtm > profit_target:
                # Squareoff 80% (In Case of Large Qtys) of the positions 
                print("mtm > profit_target; Squareoff")
                df_SqOff = pd.DataFrame(kite.positions().get('net'))[['tradingsymbol','m2m','quantity']]
                for indx in df_SqOff.index:
                    symbol = df_SqOff['tradingsymbol'][indx]
                    qty = df_SqOff['quantity'][indx] * -1
                    print(f"Placing Squareoff order for symbol={symbol},qty={qty}")
                    place_order(symbol,qty,kite.TRANSACTION_TYPE_BUY,kite.ORDER_TYPE_MARKET,None,"Algo")

                print("All Positions Squared Off. Exiting Algo...")
                exit_algo()
            else:
                    # Check if loss needs to be booked
                    current_mtm_perc = round((mtm / net_margin_utilised)*100,1)
                    print(f"current_mtm_perc={current_mtm_perc}, loss_limit_perc={loss_limit_perc}")
                    
                    if current_mtm_perc < 0:
                        if abs(current_mtm_perc) > loss_limit_perc:
                            print(f"Book Loss.(Placeholder Only)")
        
        else:
            print("No Active Positions Found")


def get_positions():
    '''Returns dataframe columns (m2m,quantity) with net values'''
    print("In get_positions():")

    # Calculae mtm manually as the m2m is 2-3 mins delayed as per public

    mtm = 0.0
    qty = 0
    try:
        # return pd.DataFrame(kite.positions().get('net'))[['m2m','quantity']].sum()
        dict_positions = kite.positions()["net"]

        for pos in dict_positions:
            mtm = mtm + ( float(pos["sell_value"]) - float(pos["buy_value"]) ) + ( float(pos["quantity"]) * float(pos["last_price"]) * float(pos["multiplier"]))
            qty = qty + int(pos["quantity"])
            print(pos["tradingsymbol"],mtm,qty)

        return pd.DataFrame([[mtm,qty]],columns = ['m2m', 'quantity'])

    except Exception as ex:
        print(f"Unable to fetch positions(m2m and qty) dataframe. Error : {ex}")
        return pd.DataFrame()


def exit_algo(): 
    print("In exit_algo():")
    # Reset stdout and std error
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    sys.exit(0)

#######################
######   TESTING   ####

# symbol='NIFTY22OCT17600CE'
# qty=50
# limit_price=300.0
# tag='STRADDLE_ORD'

# order_id=kite.place_order(variety=kite.VARIETY_REGULAR,exchange=kite.EXCHANGE_NFO,tradingsymbol=symbol,
#     transaction_type=kite.TRANSACTION_TYPE_SELL,quantity=qty,
#     product=kite.PRODUCT_NRML,order_type=kite.ORDER_TYPE_LIMIT,price=limit_price,validity=kite.VALIDITY_DAY,tag=tag)

# print(f"Order Placed. order_id={order_id}")

# Get current tradable Option details. Can be used during anytime of the day   
# get_options()


######## Strategy 1: Sell both CE and PE
# Keep 0.4 (40%) of the ltp as the SL for both
# Place 

######## Strategy 2: Sell CE at pivot resistance points , R2(qty=baselot) , R3(qty=baselot*2), R3(qty=baselot*3)
cur_HHMM = int(datetime.datetime.now().strftime("%H%M"))
previous_min = 0
print(f"cur_HHMM={cur_HHMM}")

get_options()

process_orders()

sys.exit(0)

# exit_algo()

# Process as per start and end of market timing
while cur_HHMM > 914 and cur_HHMM < 1532:
# while True:

    
    cur_min = datetime.datetime.now().minute 
    
    print(f"cur_min={cur_min}",flush=True)
    # Below if block will run after every time interval specifie in the .ini file. Used fo OHLC calculation if needed
    if( cur_min % interval == 0 and previous_min != cur_min):
        flg_min = cur_min     # Set the minute flag to run the code only once post the interval
        t1 = time.time()      # Set timer to record the processing time of all the indicators

        process_orders()

        # Find processing time and Log only if processing takes more than 2 seconds
        t2 = time.time() - t1
        print(f"t2={t2:.2f}")
        if t2 > 2.0: 
            print(f"Processing time(secs)= {t2:.2f}")


    # # Run short strangle strategy
    # if (cur_HHMM > short_strangle_time & short_strangle_flag == False):
    #     short_strangle_flag = True
    #     print("In Short Strangle condition.")

    previous_min = cur_min

    cur_HHMM = int(datetime.datetime.now().strftime("%H%M"))
 

    time.sleep(10)   # reduce to accomodate the processing delay, if any


print("====== Done ======", datetime.datetime.now(),flush=True)

exit_algo()