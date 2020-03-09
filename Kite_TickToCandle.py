import pandas as pd
import datetime
import time
import sqlite3
import sys
sys.stdout =  sys.stderr =  open(r'''Log\Kite_TickToCandle_''' + datetime.datetime.now().strftime("%Y%m%d") +".log" , "a")
print(str(datetime.datetime.now())+":Logging started.",flush=True)


data_folder=r'D:\data\2019'

#Get Ticks data 
strDBTick=data_folder + r"\TICKS_DB_"+datetime.datetime.now().strftime("%Y%m%d")+".db"
#strDBTick=data_folder + r'''\TICKS_DB_20190514.db'''
conTick = sqlite3.connect(strDBTick)
cursorTick = conTick.cursor()

strTableTicks="TICKS_"+datetime.datetime.now().strftime("%Y%m%d")
#strTableTicks='TICKS_20190514'
strTableCandle="Candle_"+datetime.datetime.now().strftime("%Y%m%d")
#strTableCandle="Candle_20190514"

interval_sec=60
resample_interval="1Min"    #'30S'


while(True):
    if (datetime.datetime.now().time()>datetime.time(15,30)):
        print("In break.Time greater than 3.30 pm.")
        break   
    time.sleep(interval_sec)

    t1=time.time()
    #strLimit=' where  timestamp is not null LIMIT 10000'
    strLimit=r''' where instrument_token=13427458 and timestamp>strftime('%Y-%m-%d %H:%M:00','now','localtime')'''
    #NIFTY19MAYFUT - 13427458
    #df=pd.read_sql_query("SELECT instrument_token, timestamp as ts, last_price FROM "+strTableTicks + strLimit,con=conTick,index_col="ts",parse_dates=True)
    df=pd.read_sql_query("SELECT instrument_token, timestamp as ts, last_price,volume FROM "+strTableTicks + strLimit,con=conTick,index_col="ts",parse_dates=['ts'])

    print("Time taken to read tick data= {0:.2f} ".format(time.time()-t1),flush=True)

    #print(df.shape)
    #print(df.head())
    #df.set_index(['ts'])
    #print(str(datetime.datetime.now()))

    #strFile=data_folder+r'''\Candle_'''+datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
    #df.to_csv(strFile)
    #df.to_csv(strFile,index=False)

    if(len(df)>0):
        t1=time.time()
        #print(df)
        #'instrument_token',
        #df_Candle=df['last_price'].resample(resample_interval).ohlc().dropna()
        df_Candle=df.groupby('instrument_token')['last_price'].resample(resample_interval).ohlc().dropna()
        #df_Candle = df['last_price'].resample(resample_interval).ohlc().dropna()
        #df_Candle=df.set_index('timestamp').groupby('instrument_token').resample('1Min')['last_price'].ffill()
        print("len(df_Candle):",len(df_Candle))
        df_Candle.to_sql(strTableCandle, conTick,if_exists='append', index=True)
        conTick.commit()
        print(str(datetime.datetime.now())+":Time taken to resample 1min candle= {0:.2f} ".format(time.time()-t1),flush=True)
        #print(df_Candle.head())
