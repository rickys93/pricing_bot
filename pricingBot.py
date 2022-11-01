#! /usr/bin/env python

from lbcapi import api
#from lib_data import *

import xmltodict
import datetime
import time
import json
import traceback
import requests
# import urllib2

from database2 import sqlCustomQuery, stringToDB, telegramSendMessage, sqlUpdateRows, sqlAddRow, asciifyString, sqlSelectRows, sqlDelRow, sqlMinRows, minsAgo, sqlSelectApiKeys, getConnectionByUser


class pricingBot(object):

    def __init__(self, apiKeys):
        self.apiKeys = apiKeys
        self.lstUsers = self.apiKeys['LBC']
        self.btcPriceMode = "cryptowatch"
        self.dicBTCPrice = {}
        self.dicPrices = {
            'BUY':{'eur':0, 'gbp':0},
            'SELL':{'eur':0, 'gbp':0}
        }
        self.dicPricesOld = {
            'BUY':{'eur':0, 'gbp':0},
            'SELL':{'eur':0, 'gbp':0}
        }
        self.dicPriceFloors = {
            'BUY':{'eur':0, 'gbp':0},
            'SELL':{'eur':0, 'gbp':0}
        }
        self.dicCountSkips = {
            'BUY':{'eur':0, 'gbp':0},
            'SELL':{'eur':0, 'gbp':0}
        }
        self.lstCurrencies = ['gbp', 'eur']
        self.dbPricingBot = r'C:\Users\aN4H3VPYitu\inetpub\vhosts\default\htdocs\api\App_Data\pricingBot.db'
        self.countSmallPriceChangeSell = 0
        self.dicCountSmallChange = {
            'BUY':{'eur':0, 'gbp':0},
            'SELL':{'eur':0, 'gbp':0}
        }
        self.advertError = 0
        self.skipEURCount = 0


    ##Refresh the exchange rates, do this daily
    def refresh_exchange_rates(self):
        try:
            res_gbp = self.oanda_api_call("instruments/GBP_USD/candles/?granularity=S10&count=1", "GET" )
            res_eur = self.oanda_api_call("instruments/EUR_USD/candles/?granularity=S10&count=1", "GET" )

            #print (json.dumps(res, indent=2) )

            self.dblExchangeRate_USD_GBP = 1 / float(res_gbp["candles"][0]["mid"]["c"])
            self.dblExchangeRate_USD_EUR = 1 / float(res_eur["candles"][0]["mid"]["c"])
        except Exception as e:
            print ("Failed to update exchange rates from OANDA")
            self.strConnStatus_ecb = "no connection"
            print (e)

    	##
    ##Make an actual call to the API
    def oanda_api_call(self, strEndpoint, strType = "GET", payload = {}):
        api_token = self.apiKeys['Oanda']['1']['key']
        api_base = "https://api-fxpractice.oanda.com/v3/"
        #print ("Starting oanda_api_call")
        if strType == "GET":
            headers = {'Authorization': 'Bearer ' + api_token}
            r = requests.get(api_base + strEndpoint, headers=headers)
        elif strType == "POST":
            headers = {'Authorization': 'Bearer ' + api_token, "Accept-Datetime-Format" : "RFC3339", "Content-Type" : "application/json"}
            if payload is not dict():
                r = requests.post(api_base + strEndpoint, headers=headers, data=payload)
            else:
                r = requests.post(api_base + strEndpoint, headers=headers)
        elif strType == "PUT":
            headers = {'Authorization': 'Bearer ' + api_token, "Accept-Datetime-Format" : "RFC3339", "Content-Type" : "application/json"}
            if payload is not dict():
                r = requests.put(api_base + strEndpoint, headers=headers, data=payload)
            else:
                r = requests.put(api_base + strEndpoint, headers=headers)
        else:
            print ("oanda_api_call method = " + strType )
        #print ("Returning data from oanda_api_call")
        return json.loads(r.text)

    ##
    ##
    ##Function to safely make API calls to local bitcoins
    def make_api_call(self, strURL):
        blnDataLeft = True
        ##Get data
        dtTimeStart = datetime.datetime.now()
        request = requests.get(strURL, headers={'User-Agent': 'Mozilla/5.0'})
        while blnDataLeft:
            if request.status_code == 200:
                try:
                    dicData = json.loads(request.content)
                except Exception as e:
                    print("JSON LOAD ERROR DETECTED")
                    ##Timings
                    return {"status" : "error", "message" : "JSON Load Error" }

                ##Check for pagination
                if "pagination" in dicData:
                    if "next" in dicData["pagination"]:
                        strURL = dicData["pagination"]["next"]
                    else:
                        blnDataLeft = False
                else:
                    blnDataLeft = False
                #Turn off Pagination, should only need the first page of results!
                blnDataLeft = False

            else:
                print("Error retrieving LBC marketplace data")
                return {"status" : "error", "message" : "LBC API error" }

            if "data" in dicData:
                return {"status" : "success", "data" : dicData["data"] }
            else:
                return {"status" : "error", "message" : "No Data Returned" }

    def updateTblPriceData(self, name, price):
        sqlUpdateRows('tblPriceData', 'name = "' + str(name) + '"', {'data':price}, database=self.dbPricingBot)
        

    ##Get the market price
    def refresh_market_price(self):
        try:
            if self.btcPriceMode == "cryptowatch":

                strURL = 'https://api.kraken.com/0/public/Ticker?pair=XBT{}'.format(self.currency.upper())

                lstPrices = []
                dblTotalPrice = 0
                apikey = self.apiKeys['Cryptowatch']['1']['key']
                request = requests.get(strURL, headers={'User-Agent': 'Mozilla/5.0'})
                dicData = json.loads(request.content)

                price = float(dicData["result"]["XXBTZ" + self.currency.upper()]["a"][0])
                self.dicBTCPrice[self.currency] = price
                self.updateTblPriceData(self.currency + '_btc_price', price)

                print('BTC/' + self.currency.upper() + ' Price = ' + str(self.dicBTCPrice[self.currency]))

				# add the btc price every 5 mins
                self.addBTCPrice()
        except Exception as e:
            # if e.reason == 'Too Many Requests':
            #     self.dicBTCPrice[self.currency] = float(self.getBTCPrice(self.currency))
            #     print("Too Many Requests on Cryptowatch, using Coindesk: Market Price = " + str ( self.dblMarketPrice ), "Message" )
            #     self.strConnStatus_exch = "connection available"
            # else:
                print ("Can't connect to exchange to get market price")
                print (e)
                self.strConnStatus_exch = "no connection"


    def addBTCPrice(self):
        fiveMinsAgo = minsAgo(5)
        if not sqlSelectRows('tblBtcPrice', 'created_at > "' + str(fiveMinsAgo) + '" and ' + self.currency + '_price IS NOT NULL'):
            sqlAddRow("tblBtcPrice", {"created_at" : str(datetime.datetime.now()).split('.')[0], self.currency + '_price':self.dicBTCPrice[self.currency]})

    def getBTCPrice(self):
        response = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json")
        price_data = response.json()
        gbp_price = price_data['bpi'][self.currency.upper()]['rate'].replace(',','')
        return gbp_price


    ##Get the market place data for display
    def refresh_adverts(self):

        # if we're selling, we need to get ads from buy-bitcoins-online and vice versa
        if self.buySell == 'SELL':
            buySell = 'buy'
        else:
            buySell = 'sell'

        ##Timing
        if self.currency == 'eur':
            strURL = "https://localbitcoins.com/{buySell}-bitcoins-online/{currency}/sepa-eu-bank-transfer/.json".format(buySell=buySell, currency=self.currency)
        elif self.currency == 'gbp':
            strURL = "https://localbitcoins.com/{buySell}-bitcoins-online/{currency}/c/bank-transfers/.json".format(buySell=buySell, currency=self.currency)
        dicData = self.make_api_call(strURL)

        self.lstSellAdvertsNew = []

        # clear ads from db
        sqlDelRow("tblLbcMarketplace" + self.currency.upper() + "_" + self.buySell, "", database=self.dbPricingBot)
        
        if dicData["status"] == "success":
            for ad in dicData["data"]["ad_list"]:
                ad = ad['data']
                dicAd = {}
                for key in ad:
                    if key in ['min_amount_available']:
                        continue
                    #If a profile
                    if key == "profile":
                        for p_key in ad[key]:
                            ad[key][p_key] = stringToDB(ad[key][p_key])
                            dicAd[p_key] = stringToDB(ad[key][p_key])
                    elif key in ['msg', 'bank_name']:
                        dicAd[key] = ''
                    else:
                        dicAd[key] = stringToDB(ad[key])


                ## only use ads that are bank transfer
                if dicAd['online_provider'] in ["NATIONAL_BANK", "SPECIFIC_BANK", 'SEPA']:

                    # add/update user to db 
                    if not sqlSelectRows("tblLbcProfiles", "username = '" + str(dicAd['username']) + "'", database=self.dbPricingBot):
                        sqlAddRow("tblLbcProfiles", ad['profile'], database=self.dbPricingBot)
                    else:
                        sqlUpdateRows("tblLbcProfiles", "username = '" + str(dicAd['username']) + "'", ad['profile'], database=self.dbPricingBot)

                    # add ad to db
                    sqlAddRow("tblLbcMarketplace" + self.currency.upper() + "_" + self.buySell, dicAd, database=self.dbPricingBot)
                                
                                
        else:
            print("Could not refresh Sell Adverts")

	##Tell us if an advert is one of ours, i.e. profile matches one of our usernames
    def ad_is_ours(self, ad):
        for u in self.lstUsers:
            if ad['username'].lower() == u.lower():
                return True
        return False

    def adPassedFilters(self, ad):

        blnPassFilters = True

        ### Test trade count is above minimum
        if '+' in str(ad['trade_count']):
            trade_count = int(str(ad['trade_count']).replace('+', '').replace(' ', ''))
        else:
            trade_count = int(str(ad['trade_count']).replace(' ', ''))

       
        if self.config['min_trades'] > trade_count:
            ## Failed test, don't add
            blnPassFilters = False


        ### Test top limit is high enough
        if ad["max_amount_available"] is None or ad["max_amount_available"] == "None":
            fltTopLimit = 0
        else:
            fltTopLimit = float(ad["max_amount_available"])

        if fltTopLimit < self.config['top_trade_limit']:
            ## Failed test, don't add
            blnPassFilters = False


        ### Test bottom limit is low enough
        if ad["min_amount"] is None or ad["min_amount"] == "None":
            fltBottomLimit = 0
        else:
            fltBottomLimit = float(ad["min_amount"])

        if fltBottomLimit > self.config['bottom_trade_limit']:
            ## Failed test, don't add
            blnPassFilters = False


        ### Test top/bottom limit spread is large enough
        if fltBottomLimit * int(self.config['top_bottom_spread']) > fltTopLimit:
            ## Failed test, don't add
            blnPassFilters = False


        ### Test that it's not our own ad
        if self.ad_is_ours(ad):
            ## Failed test, don't add
            blnPassFilters = False

        return blnPassFilters


    def whitelistBlacklist(self, profile, blnPassFilters):

        if profile['blacklist']:
            blnPassFilters = False

        elif profile['whitelist']:
            blnPassFilters = True

        return blnPassFilters

    def getLBCProfile(self, ad):
        profile = sqlSelectRows('tblLbcProfiles', 'username = "' + str(ad['username']) + '"', database=self.dbPricingBot)
        if profile:
            profile = profile[0]
            return profile
        else:
            print("Username not found in tblLBCProfiles while checking for whitelist blacklist...")


    def getBotConfig(self):
        lstConfigs = sqlSelectRows('tblBotsConfig', 'currency = "' + self.currency.upper() + '" AND buySell = "' + self.buySell.upper() + '"', database=self.dbPricingBot)       

        return lstConfigs[0]

    def filterFloorCeiling(self, BtcPrice, lstFilteredAdverts):
        if self.buySell == 'SELL':
            ####### SELL ADVERTS #######
            ## calculate the price floor for sell adverts
            self.dicPriceFloors[self.buySell][self.currency] = BtcPrice * (100 + float(self.config['price_floor_percent'])) / 100
            fltPriceCeiling = self.dicPriceFloors[self.buySell][self.currency] * 1.1
            ## filter out adverts below the floor price
            lstFilteredAdverts = list(filter(lambda ad: ad['temp_price'] > self.dicPriceFloors[self.buySell][self.currency], lstFilteredAdverts))

            ## filter out adverts above price ceiling
            lstFilteredAdverts = list(filter(lambda ad: ad['temp_price'] < fltPriceCeiling, lstFilteredAdverts))
        else:
            ####### BUY ADVERTS #######
            ## calculate the price floor for buy adverts
            self.dicPriceFloors[self.buySell][self.currency] = BtcPrice * (100 - float(self.config['price_floor_percent'])) / 100
            fltPriceCeiling = self.dicPriceFloors[self.buySell][self.currency] * 0.9

            ## filter out adverts above the floor price
            lstFilteredAdverts = list(filter(lambda ad: ad['temp_price'] < self.dicPriceFloors[self.buySell][self.currency], lstFilteredAdverts))

            ## filter out adverts below price ceiling
            lstFilteredAdverts = list(filter(lambda ad: ad['temp_price'] > fltPriceCeiling, lstFilteredAdverts))

        self.updateTblPriceData(self.currency + '_' + self.buySell.lower() +'_price_floor', self.dicPriceFloors[self.buySell][self.currency])
        print("Price floor = {}".format(self.dicPriceFloors[self.buySell][self.currency]))

        return lstFilteredAdverts

        
    def calculate_ad_price(self):
        tblMarketplace = "tblLbcMarketplace" + self.currency.upper() + '_' + self.buySell # table of lbc marketplace

        # targetting is an easy way to see which ads we are targetting
        sqlUpdateRows(tblMarketplace, '', {'targetting':0}, database=self.dbPricingBot)
   
        lstAdverts = sqlSelectRows(tblMarketplace, '', 'ad_id, max_amount_available, username, min_amount, temp_price, trade_count', database=self.dbPricingBot)

        lstFilteredAdverts = []

        for ad in lstAdverts:

            profile = self.getLBCProfile(ad)
            if not profile:
                continue

            blnPassFilters = self.adPassedFilters(ad)

            # override the filters with whitelist/blacklist
            blnPassFilters = self.whitelistBlacklist(profile, blnPassFilters)

            if blnPassFilters:
                lstFilteredAdverts.append(ad)

        self.tblLBCMarket = 'tblLBCMarket' + self.currency.upper()

        # every 1800 seconds, move up price floor for 25 seconds, to try and let others move up
        if self.buySell == 'SELL':
            self.increasePriceFloorEveryFor(1800, 25)

        # filter out adverts based on price floor and ceiling
        lstFilteredAdverts = self.filterFloorCeiling(self.dicBTCPrice[self.currency], lstFilteredAdverts)
        
        if self.buySell == 'SELL':
            self.updateLbcPrices(lstFilteredAdverts)

        for ad in lstFilteredAdverts:
            sqlUpdateRows(tblMarketplace, "username = '{}'".format(ad['username']), {'targetting':1}, database=self.dbPricingBot)

        return self.findAdPrice(lstFilteredAdverts)


    def updateLbcPrices(self, lstFilteredAdverts):
        
		# set all prices to 0 to restart market prices (this helps to later group traders with multiple accounts)
        sqlUpdateRows(self.tblLBCMarket, '', {'price':0}, database=self.dbPricingBot)

        for ad in lstFilteredAdverts:
            dic = {'ad_id':ad['ad_id'], 'price':ad['temp_price'], 'trader':ad['username']}

            # some traders have multiple accounts, with one pricing bot - so the tblLBCTraders groups all the accounts together by using the trader_name
            trader = sqlSelectRows('tblLbcTraders', 'lbc_usernames LIKE "%' + ad['username'] + '%"', database=self.dbPricingBot)
            if trader:
                dic['trader'] = trader[0]['trader_name']

            # not already in market db so we need to add
            if not sqlSelectRows(self.tblLBCMarket, 'trader = "' + dic['trader'] + '"', database=self.dbPricingBot):
                sqlAddRow(self.tblLBCMarket, dic, database=self.dbPricingBot)
            else:
                # if price is not 0, this group of traders has already been updated, doesn't need updating 
                if sqlSelectRows(self.tblLBCMarket, 'trader = "' + dic['trader'] + '" AND price = 0', database=self.dbPricingBot):
                    sqlUpdateRows(self.tblLBCMarket, 'trader = "' + dic['trader'] + '"', {'price':dic['price'], 'ad_id':dic['ad_id']}, database=self.dbPricingBot)


    def findUsernameFromPrice(self, price):
        target = sqlSelectRows( 'tblLbcMarketplace' + self.currency.upper() + '_' + self.buySell , 'temp_price = ' + str(price), database=self.dbPricingBot)
        target = target[0]['username']
        return target

    #### Object of this function: if more than 1 trader within [5 pounds] go with price normally, otherwise we go for the price above
    def giveChanceToMoveUp(self):
        if self.buySell == 'BUY':
            strQ = 'SELECT MAX(temp_price) FROM tblLbcMarketplace' + self.currency.upper() + '_' + self.buySell + ' WHERE targetting = 1'
            price = sqlCustomQuery(strQ, database=self.dbPricingBot)
            if price[0][0]:
                self.target = self.findUsernameFromPrice(price[0][0])
                return price[0][0]
            

        # find the current target price
        min_price = sqlMinRows(self.tblLBCMarket, 'price != 0', 'price', database=self.dbPricingBot)
        min_price = min_price[0]['price']

        # find any other traders within £5 of the target price
        other_traders = sqlSelectRows(self.tblLBCMarket, 'price < ' + str(min_price + 5) + ' AND price > ' + str(min_price - 5) + ' AND ignore = 0' , database=self.dbPricingBot)
        other_traders_inc_ignored = sqlSelectRows(self.tblLBCMarket, 'price < ' + str(min_price + 5) + ' AND price > ' + str(min_price - 5) , database=self.dbPricingBot)

        # if targetting only one trader then we try
        if len(other_traders) == 1:                          
            min_price = self.ignoreOrNot(other_traders, min_price)

        # not actually sure why this is here, but if all traders are ignored, then we still try and ignore them
        elif len(other_traders) == 0:
            min_price = self.ignoreOrNot(other_traders_inc_ignored, min_price)

        else:
            # multiple traders within £5, we go with normal price 
            # reset count for traders
            sqlUpdateRows(self.tblLBCMarket, '', {'count':0}, database=self.dbPricingBot)

        self.target = self.findUsernameFromPrice(min_price)
        return min_price

    def ignoreOrNot(self, other_traders, min_price):
        count = other_traders[0]['count']
        trader = other_traders[0]['trader']
        # ignore them 3 times (to give them a chance to move higher with us) 
        if count <= 2:
            print("Only targetting one trader, " + trader + ", ignoring them this time to see if they move up. Count = " + str(count + 1) + "/3.")
            next_min_price = sqlMinRows(self.tblLBCMarket, 'price != 0 AND price > ' + str(min_price), 'price', database=self.dbPricingBot)
            if next_min_price:
                min_price = next_min_price[0]['price']
                sqlUpdateRows(self.tblLBCMarket, 'trader = "' + trader + '"', {'count':count + 1}, database=self.dbPricingBot)
        # if they don't match us then continue targetting them another 22 times
        elif count <= 25:
            print("Trader " + trader + ", didn't move up, so retargetting them. Count = " + str(count - 2) + "/23." )
            sqlUpdateRows(self.tblLBCMarket, 'trader = "' + trader + '"', {'count':count + 1}, database=self.dbPricingBot)
        # then begin ignoring them again to give them another chance
        elif count > 25:
            print("Targetted " + trader + " 23 times, next time we try and ignore them again to see if they move up.")
            sqlUpdateRows(self.tblLBCMarket, 'trader = "' + trader + '"', {'count':0}, database=self.dbPricingBot)

        return min_price


    def findAdPrice(self, lstFilteredAdverts):
        ###OUTPUT
        if len(lstFilteredAdverts) == 0:
            price = self.dicPriceFloors[self.buySell][self.currency] * 1.01
            target = 'None'
        else:
            # if only one trader then we don't need to use this method (not ideal but will happen rarely)
            if len(lstFilteredAdverts) > 1:
                # function to try and give traders chance to move up when we're only matching one
                price = float( self.giveChanceToMoveUp() )
            else:
                price = float( lstFilteredAdverts[0]['temp_price'] )

        return price

    def increasePriceFloorEveryFor(self, every, For):
        if self.lastRefresh < datetime.datetime.now() - datetime.timedelta(seconds=every):
            print("Been 20 mins since last reset price, setting price floor 2 percent higher to try and move bots up")
            self.dicPriceFloors[self.buySell][self.currency] = self.dicPriceFloors[self.buySell][self.currency] * 1.02
            if self.lastRefresh < datetime.datetime.now() - datetime.timedelta(seconds=every+For):
                self.lastRefresh = datetime.datetime.now()

    def checkPriceNotChanged(self):
        # if price hasn't changed, do not update the advert prices
        if self.dicPricesOld[self.buySell][self.currency] == self.dicPrices[self.buySell][self.currency]:
            self.dicCountSkips[self.buySell][self.currency] += 1
            if self.dicCountSkips[self.buySell][self.currency] > 10:
                print("Price unchanged over 10 consecutive times. NOT SKIPPING {} ADS.".format(self.buySell))
                return False
            else:
                print("Price unchanged. SKIPPING {} ADS.".format(self.buySell))
                return True

    def checkSmallPriceChange(self):
        # if price has only changed a small amount, don't update trusted
        if abs(self.dicPricesOld[self.buySell][self.currency] - self.dicPrices[self.buySell][self.currency]) < 2:
            self.smallPriceChange = True
            self.dicCountSmallChange[self.buySell][self.currency] += 1
            if self.dicCountSmallChange[self.buySell][self.currency] < 6:
                print("Small price change. SKIPPING TRUSTED SELL ADS.")
        else:
            self.smallPriceChange = False
            self.dicCountSmallChange[self.buySell][self.currency] = 0


    ##Push the prices out to the actual adverts
    def refresh_ad_prices(self):

        print(self.buySell.capitalize() + " price = " + str(self.dicPrices[self.buySell][self.currency]))

        if self.checkPriceNotChanged():
            return

        self.dicCountSkips[self.buySell][self.currency] = 0

        self.checkSmallPriceChange()

        strQ = 'currency = "' + self.currency.upper() + '" AND buy_sell = "' + self.buySell + '" and slot_on = 1'
        lstSlots = sqlSelectRows('tblBotSlots', strQ , database=self.dbPricingBot)

        for s in lstSlots:
            ## this is to stop the trusted ads being updated if only small price change, to speed bot up
            if self.smallPriceChange and s['trusted'] and self.dicCountSmallChange[self.buySell][self.currency] < 6:
                continue
            else:
                # once it skips trusted ads 6 time, reset
                if self.dicCountSmallChange[self.buySell][self.currency] >= 6:
                    self.smallPriceChange = False
                    self.dicCountSmallChange[self.buySell][self.currency] = 0
                

                if self.buySell == 'BUY':
                    s['slot_price'] = self.dicPrices[self.buySell][self.currency] + s['amount_below']
                elif self.buySell == 'SELL':
                    s['slot_price'] = self.dicPrices[self.buySell][self.currency] - s['amount_below']

                print( "Target username = " + str(self.target) + ". Advert (" + str(s['ad_id']) +") price is " + str ( s['slot_price'] ))

                self.set_ad_price(s)

        self.dicPricesOld[self.buySell][self.currency] = self.dicPrices[self.buySell][self.currency]


    ##Change the price of a trade advert
    def set_ad_price(self, slot):

        dicPostData = { "price_equation" : str(slot['slot_price']) }
        strAPICall = '/api/ad-equation/' + str(slot['ad_id']) +  '/'

        ##Make the call
        try:
            user = slot['username']
            api_conn = getConnectionByUser(user)
            response = api_conn.call('POST', strAPICall, dicPostData)

            ##Print the response
            strResponse = json.dumps( json.loads(response._content), indent=2)
            if "Ad changed successfully" not in strResponse:
                self.advertError += 1
                print(json.dumps( json.loads(response._content), indent=2))
        except (ValueError, requests.ConnectionError) as e:
            print("ERROR: Failed to update advert, ignoring and carrying on")


    def main(self):
        self.lastRefresh = datetime.datetime.now()

        while True:
            print(str(datetime.datetime.now()) + '>>> Looping again:')
            for bs in ['SELL', 'BUY']:

                self.buySell = bs
                print('___________________________________')
                print('<< RUNNING BOT FOR {} ADVERTS >>'.format(self.buySell))
                for c in self.lstCurrencies:
                    self.currency = c
                    if self.currency == 'eur':
                        if self.skipEURCount < 5:
                            print('EUR Skip Count = ' + str(self.skipEURCount + 1) + '/5. Skipping...')
                            if self.buySell == 'BUY':
                                self.skipEURCount += 1
                            continue
                        else:
                            print('Skipped EUR 5 times, not skipping...')
                            self.skipEURCount = 0



                    self.config = self.getBotConfig()  
                    if self.config['bot_on']:
                        print('___________________________________')
                        print('Running for currency ' + str(c).upper() + '...')
                        self.refresh_market_price()
                        self.refresh_adverts()
                        self.dicPrices[self.buySell][self.currency] = self.calculate_ad_price()
                        self.updateTblPriceData(self.currency + '_' + self.buySell.lower() + '_price', self.dicPrices[self.buySell][self.currency])
                        self.refresh_ad_prices()
                    else:
                        print(str(self.currency.upper()) + ' ' + str(self.buySell) + ' bot turned off. Skipping adverts...')
            time.sleep(5)



if __name__ == '__main__':
    from database2 import sqlSelectApiKeys2

    environment = 'Live'

    # Load keys out of SQL
    apiKeys = sqlSelectApiKeys2(environment)
    p = pricingBot(apiKeys)
    url = "https://localbitcoins.com/sell-bitcoins-online/eur/c/sepa-eu-bank-transfer/.json"
    # response = p.make_api_call(url)

    # p.currency = 'EUR'
    # p.refresh_market_price()
    p.main()


