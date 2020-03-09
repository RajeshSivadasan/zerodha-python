from kiteconnect import KiteConnect
import pandas as pd
import sqlite3
import time
import datetime
import configparser
import requests
import sys


#This program should be run on every thursday morning (banknifty weekly expiry) 
sys.stdout = open(r'''Log\getAllInstrumentsDaily_''' + datetime.datetime.now().strftime("%Y%m%d") +".log" , "a")
print(datetime.datetime.now(),flush=True)


# Functions Start
def Tele(strLogText):
    #print(strLogText)
    strTxt=strLogText[:4000]
    requests.get("https://api.telegram.org/"+strBotToken+"/sendMessage?chat_id="+strChatID+"&text="+strTxt)

# Functions End
#######################



#Load parameters from the config file
cfg=configparser.ConfigParser()
cfg.read("config.ini")
api_key = cfg.get("tokens", "api_key")
currMnth = cfg.get("info", "curr_month")    #19JANFUT
nearMnth = cfg.get("info", "near_month")
strChatID = cfg.get("info", "Tele_ChatID")
strBotToken = cfg.get("info", "Tele_BotToken")

##gets expiry date format for banknifty options, 3 is for thursday
d = datetime.date.today() + datetime.timedelta( (3-datetime.date.today().weekday()) % 7 )
currWeekExpiry = d.strftime("%d%b").upper()
print("currMnth,nearMnth,currWeekExpiry=",currMnth,nearMnth,currWeekExpiry)


kite = KiteConnect(api_key=api_key)

strDB="Instruments.db"
con = sqlite3.connect(strDB)

#------------------------------------------------------------
#1. Download all instruments daily and save in Instruments.db
#------------------------------------------------------------
t1=time.time()
print("t1={0:.2f}".format((t1)))
df = pd.DataFrame(kite.instruments())
print("Time taken to read kite.instruments() = {0:.2f} secs".format(time.time()-t1))
t1=time.time()
print("t1={0:.2f}".format((t1)))
strTable="INSTRU_"+currMnth
#strTable="INSTRU_"+datetime.datetime.now().strftime("%Y%m")
df.to_sql(strTable, con,if_exists='replace', index=False)
print("saved to database table ", strTable)
print("Time taken write to db = {0:.2f} secs".format(time.time()-t1))


#------------------------------------------------------------
#2. Source the required instrument token into the Daily database from the above dump, overwrite monthly table 
#------------------------------------------------------------
t1=time.time()
print(t1)

#Select current month future contracts and corresponding near month future contracts, NSE and BSE cash scripts
strSQL="select i.instrument_token,i.tradingsymbol,i.lot_size,i.strike,i.segment,case when  instr(i.tradingsymbol,'" + nearMnth + "')>0 then 'NFO_NEAR' else exchange end as exchange from " \
+"Symbol_Master s, "+strTable+" i where s.symbol= substr(i.tradingsymbol,1,instr(i.tradingsymbol,'"+ currMnth +"')-1) " \
+"or s.symbol=i.tradingsymbol or s.symbol= substr(i.tradingsymbol,1,instr(i.tradingsymbol,'" + nearMnth + "')-1)" \
+" union all" \
+" select instrument_token,tradingsymbol,lot_size,strike,segment,exchange from "+strTable \
+" where tradingsymbol like 'BANKNIFTY"+ currWeekExpiry + "%'" \
+" union all" \
+" select instrument_token,tradingsymbol,lot_size,strike,segment,exchange " \
+" from "+strTable+" where segment='NFO-OPT' and tradingsymbol like 'NIFTY" + currMnth[:5] + "%'" 

#Add near week banknifty options if its thursday
if (datetime.date.today().weekday()==3):
    d = datetime.date.today() + datetime.timedelta(7)
    nearWeekExpiry = d.strftime("%d%b").upper()
    strSQL=strSQL + " union all select instrument_token,tradingsymbol,lot_size,strike,segment,exchange from "+strTable \
    +" where tradingsymbol like 'BANKNIFTY"+ nearWeekExpiry + "%'"



print(strSQL)
df_Instr = pd.read_sql(strSQL, con)
con.close()
print("Time taken to read filtered tokens = {0:.2f} ".format(time.time()-t1))

#Create monthly fut inst token table
strDB="DAILY.db"
con = sqlite3.connect(strDB)
df_Instr.to_sql(strTable, con,if_exists='replace', index=False)
con.commit()

strMsg="Import of required instruments to the table "+strTable+" completed. " + str(len(df_Instr.index)) + " rows imported"

print(strMsg)
Tele(strMsg)