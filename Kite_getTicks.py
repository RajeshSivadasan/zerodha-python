import pandas as pd
from kiteconnect import KiteConnect
from kiteconnect import KiteTicker
import datetime
import time
import sqlite3
import configparser

#This will be the first program to run after market starts as it deletes the 
#unwanted nifty and banknifty options

#Checks: comment line 23 sys.stdout, comment line 187 Tele(

# Perday = 6 hrs 15 mins = 375 mins = 22500 seconds
# 1,65,000 rows for 110 scrips per day
# 33 lacs rows per month (20 days)

#1.0 Run getAllInstrumentsDaily.py to get all the instruments
#1.1 Get BSE,NFO-FUT and NSE instruments for the current month. Check for near and farmonth later
#1.2 Get access token from ini file. Generate the token at 9.00 am
#1.3 Get for both NSE and BSE exchange
#1.4 Get current and near month for cash

import sys
sys.stdout = sys.stderr = open(r'''Log\Kite_getTicks_''' + datetime.datetime.now().strftime("%Y%m%d") +".log" , "a")
print(str(datetime.datetime.now())+":Logging started.",flush=True)


#Load parameters from the config file
cfg=configparser.ConfigParser()
cfg.read("config.ini")
api_key = cfg.get("tokens", "api_key")
access_token = cfg.get("info", "access_token")
currMnth = cfg.get("info", "curr_month")    #19JANFUT
nearMnth = cfg.get("info", "near_month")    #19FEBFUT
data_folder = cfg.get("info", "data_folder")    #19FEBFUT

cols=['instrument_token', 'exchange_token','tradingsymbol','name','last_price', 'expiry','strike', 'tick_size','lot_size', 'instrument_type', 'segment', 'exchange']


kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)
kws = KiteTicker(api_key,access_token)



# ---------------------------------------------------------------
#1. Read master instruments from Daily database
# --------------------------------------------------------------- 
#Read instrument tokens required for daily execution into a list 
strDB="Daily.db"
con = sqlite3.connect(strDB)


# Get a cursor object
cursor = con.cursor()

t1=time.time()
strTable="INSTRU_"+currMnth
strSQL="Select instrument_token,tradingsymbol from "+strTable + " where exchange='NFO'"
df_token_lst = pd.read_sql(strSQL, con)
print("Time taken to df= {0:.2f} ".format(time.time()-t1))

#lst_NFO_tokens = df_token_lst.instrument_token.head().tolist()
lst_NFO_tokens = df_token_lst.instrument_token.tolist()
print(str(datetime.datetime.now())+":len(lst_NFO_tokens)=",len(lst_NFO_tokens),flush=True)



print("lst_NFO_tokens:",lst_NFO_tokens)
df_cols=['timestamp','instrument_token','last_price','open','high','low','close','volume','oi']
#df = pd.DataFrame(data=[],columns=df_cols)

df = pd.DataFrame()

first_tick_flag = True
first_OHL_Save = False
interval_sec = 30
start_time = 0
end_time = 0

#Create Ticks database and table 
strDBTick=data_folder + r"\TICKS_DB_"+datetime.datetime.now().strftime("%Y%m%d")+".db"
conTick = sqlite3.connect(strDBTick)
cursorTick = conTick.cursor()

strTickTable="TICKS_"+datetime.datetime.now().strftime("%Y%m%d")
print("Tablename=",strTickTable,flush=True)

strSQL="CREATE TABLE IF NOT EXISTS "+ strTickTable +" (timestamp TIMESTAMP, instrument_token INT, last_price REAL, open REAL," \
+" high REAL, low REAL, close REAL, volume int, oi int )"
cursorTick.execute(strSQL)

conTick.commit()

lst_ticks=[]


def on_ticks(ws, ticks):

    global first_tick_flag,start_time,end_time,lst_ticks
    #RUNS FIRST TIME
    if first_tick_flag:
        first_tick_flag = False
        start_time = time.time()

    #RUNS PER TICK
    end_time = time.time()

    
    for t in ticks:
        #print(t)
        #Mode=FULL which has OI
        t1 = [t['timestamp'],t['instrument_token'],t['last_price'],t['ohlc']['open'],t['ohlc']['high'], t['ohlc']['low'],t['ohlc']['close'],t['volume'],t['oi']]
        lst_ticks.append(t1)
    
    #RUNS AT THE END OF INTERVAL/CANDLE ; Saves to the db
    if int(end_time - start_time) >=interval_sec:
        #print("start_time,end_time:",start_time,end_time)
        start_time = end_time
        t1=time.time()
        #print(str(datetime.datetime.now())+":Candle:len(lst_ticks)=",len(lst_ticks),flush=True)
        
        df=pd.DataFrame(lst_ticks, columns=df_cols)

        df.dropna(inplace=True)
    
        #df=pd.concat(lst_ticks)
        #df.append(lst_ticks,ignore_index=True)
           
        df.to_sql(strTickTable, conTick,if_exists='append', index=False)
        conTick.commit()
        print(str(datetime.datetime.now())+":Time taken to save df= {0:.2f}.#Ticks= ".format(time.time()-t1),len(lst_ticks),flush=True)
        #print(str(datetime.datetime.now())+":Data saved to ",strTickTable,flush=True)
        lst_ticks=[]



def on_connect(ws, response):
    try:
        ws.subscribe(lst_NFO_tokens)
        ws.set_mode(ws.MODE_FULL, lst_NFO_tokens)
        print("Websocket Connected")
    except Exception as ex:
            print("Exception occured on_connect:",ex)



def on_close(ws,code,reason):
    #ws.stop()
    print(str(datetime.datetime.now())+":Websocket Closed",flush=True)


kws.on_ticks = on_ticks
kws.on_connect = on_connect
kws.on_close = on_close

kws.connect()

print(str(datetime.datetime.now())+":Came in main thread",flush=True)


sys.exit(0)

print("Done.")

while True:
    #q=kite.ohlc(lst_Result)
    #q=kite.quote(lst_NFO_tokens)    #Limit of 500 with quote, check if ohlc can be used as it supports 1000 scrips
    #df=pd.DataFrame(lst_ticks, columns=df_cols)    
    #df=pd.DataFrame(q)

    #df.to_sql(strTable, con,if_exists='replace', index=False)
    #con.commit()
    q=kite.quote(lst_NFO_tokens)
    #df=pd.DataFrame(q)

    cursor.execute('BEGIN TRANSACTION')

    for t in q:
        strSQL="INSERT INTO " + strTable + " VALUES('" + str(q[t]['timestamp']) +"'," \
        + str(q[t]['instrument_token']) + "," + str(q[t]['last_price']) + "," + str(q[t]['last_price']) + "," + str(q[t]['last_price'])\
        + "," + str(q[t]['last_price']) + "," + str(q[t]['last_price']) + "," + str(q[t]['volume']) + "," + str(q[t]['oi']) + ")"

        #print(strSQL)
        cursor.execute(strSQL)
        #print(t,q[t]['timestamp'],q[t]['instrument_token'],q[t]['oi'],q[t]['volume'],q[t]['last_price'])
    cursor.execute('COMMIT')
    time.sleep(28)