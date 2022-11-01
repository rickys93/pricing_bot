from flask import Flask, render_template, jsonify, request, flash
from turbo_flask import Turbo
import threading
import time
from database2 import sqlCustomQuery, sqlSelectRows, sqlUpdateRows


app = Flask(__name__)
app.secret_key = 'randomSecret'


turbo = Turbo(app)
database = r"C:\Users\rich_\OneDrive\Personal\Coding\Coinstand\pricing_bot\pricingBot.db"

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/bot-config', methods=["POST", "GET"])
def bot_config():
    lstFilters = ['min_trades', 'top_trade_limit', 'bottom_trade_limit', 'top_bottom_spread','price_floor_percent', 'bot_on']
    if request.method == "POST":
        form_values = request.form
        bot_config = {}
        currency = request.form['bot_on'].split('-')[0]
        buySell = request.form['bot_on'].split('-')[1]
        for f in lstFilters:
            if f == 'bot_on':
                if 'off' in request.form[f]:
                    bot_config[f] = 0
                else:
                    bot_config[f] = 1
                
            else:
                bot_config[f] = float(request.form[f])
        
        sqlUpdateRows('tblBotsConfig', 'currency = "' + currency.upper() + '" AND buySell = "' + buySell.upper() + '"', bot_config, database=database)
        flash('Looks like you have changed your name!')

        return render_template("bot-config.html")

    else:

        return render_template("bot-config.html")

@app.route('/gbp-sell-marketplace')
def gbp_sell_marketplace():
    return render_template("gbp-sell.html")

@app.route('/gbp-buy-marketplace')
def gbp_buy_marketplace():
    return render_template("gbp-buy.html")

@app.route('/eur-sell-marketplace')
def eur_sell_marketplace():
    return render_template("eur-sell.html")

@app.route('/eur-buy-marketplace')
def eur_buy_marketplace():
    return render_template("eur-buy.html")

@app.context_processor
def get_gbp_sell():
    ## get the price data to display above the table
    price_data_original =  sqlSelectRows('tblPriceData', '', database=database)
    price_data = {}
    for k in price_data_original:
        if k['data']:
            price_data[k['name']] = str(round(float(k['data']), 2))

    ## data to populate the tables
    gbp_sell = sqlSelectRows('tblLbcMarketplaceGBP_SELL', '', database=database, orderBy = 'temp_price')
    gbp_buy = sqlSelectRows('tblLbcMarketplaceGBP_BUY', '', database=database, orderBy = 'temp_price DESC')
    eur_sell = sqlSelectRows('tblLbcMarketplaceEUR_SELL', '', database=database, orderBy = 'temp_price')
    eur_buy = sqlSelectRows('tblLbcMarketplaceEUR_BUY', '', database=database, orderBy = 'temp_price DESC')

    ## get the config data
    config_data =  sqlSelectRows('tblBotsConfig', '', database=database)
    config = {'EUR':{'SELL':{},'BUY':{}},'GBP':{'SELL':{},'BUY':{}}}
    for marketplace in config_data:
        for k in marketplace:
            if k not in ['buySell','currency']:
                config[marketplace['currency']][marketplace['buySell']][k] = marketplace[k]


    return {'gbp_sell': gbp_sell, "gbp_buy":gbp_buy, "eur_sell":eur_sell, 
            "eur_buy":eur_buy, 'price_data':price_data, 'gbp_config':config['GBP'], 'eur_config':config['EUR']}



if __name__ == '__main__':
    app.run(debug=True)