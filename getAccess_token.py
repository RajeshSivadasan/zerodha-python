#import requests
import configparser
from kiteconnect import KiteConnect
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import staleness_of
import datetime
import sys
sys.stdout = open("Log\getAccess_token_" + datetime.datetime.now().strftime("%Y%m%d") +".log" , "a")
print(datetime.datetime.now(),flush=True)


def getAccessToken():
    retval="-1"
    #Load parameters from the config file
    cfg=configparser.ConfigParser()
    cfg.read("config.ini")

    api_key = cfg.get("tokens", "api_key")
    secret_key = cfg.get("tokens", "secret_key")

    strURL = cfg.get("info", "KiteURL") + api_key
    strUID = cfg.get("info", "UID")
    strPwd = cfg.get("info", "PWD")
    strChrmDrvrPath = cfg.get("info", "ChromeDriverPath")

    #Find Request Token
    # get request token from url
    driver = webdriver.Chrome(strChrmDrvrPath)
    #driver = webdriver.Chrome(r'''D:\Python\chromedriver\chromedriver.exe''')
    #driver = webdriver.Chrome()
    driver.implicitly_wait(600) #implicitly wait for 10 seconds untill element is found
    driver.get(strURL)

    print("url=",strURL)

    uidxpath = r'''//*[@id="container"]/div/div/div[2]/form/div[1]/input'''
    pwdxpath = r'''//*[@id="container"]/div/div/div[2]/form/div[2]/input'''
    #btnxpath = r'''//*[@id="container"]/div/div/div[2]/form/div[3]/button'''
    btnxpath = r'''//*[@id="container"]/div/div/div[2]/form/div[4]/button'''


    driver.find_element_by_xpath(uidxpath).send_keys(strUID)
    driver.find_element_by_xpath(pwdxpath).send_keys(strPwd)
    driver.find_element_by_xpath(btnxpath).click()

    # Security questions page inputs
    secQ1xpath = r'''//*[@id="container"]/div/div/div[2]/form/div[2]/div/input'''
    secQ2xpath = r'''//*[@id="container"]/div/div/div[2]/form/div[3]/div/input'''
    secBtnxpath = r'''//*[@id="container"]/div/div/div[2]/form/div[4]/button'''

    #print("current url1=",driver.current_url)

    driver.find_element_by_xpath(secQ1xpath).send_keys("a")
    driver.find_element_by_xpath(secQ2xpath).send_keys("a")
    old_page = driver.find_element_by_tag_name('html')
    driver.find_element_by_xpath(secBtnxpath).click()
        
    WebDriverWait(driver, 10).until(staleness_of(old_page))

    strTokenURL = driver.current_url
    #print("current url2=",strTokenURL)

    driver.close()
    #driver.quit()

    pos=int(strTokenURL.find("?"))
    if pos>0:
        s2=strTokenURL[pos+1:]
        qs=dict(x.split('=') for x in s2.split('&'))
        if qs['status']=="success":
            request_token = qs['request_token']
            print("request_token=",request_token)
        else:
            print('unable to fetch request_token. status not success. strTokenURL=',strTokenURL)
            #exit()
            return retval
    else:
        print("? not found in request_token url")
        #exit()
        return retval


    kite = KiteConnect(api_key=api_key)
    data = kite.generate_session(request_token,secret_key)
    access_token=data["access_token"]
    cfg.set("info","access_token",access_token)
    #Below Can be used to check the difference. Day level. 
    cfg.set("info","TokenURLTime",datetime.datetime.now().strftime("%Y%m%d")) 

    with open('config.ini', 'w') as configfile:
        cfg.write(configfile)
        configfile.close()
    
    retval=access_token
    return retval

if __name__ == '__main__':
    access_token=getAccessToken()
    print("access_token=",access_token)
    if access_token=="-1":
        print("Unable to Fetch access token")
    