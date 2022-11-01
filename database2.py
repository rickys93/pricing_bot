import sqlite3
import requests
from requests.auth import HTTPBasicAuth
import string

import datetime
import os
# from telegram import InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import Updater, CommandHandler, CallbackQueryHandler


dbApiKeys = './apiKeys.db'
database = "./dbfile.db"



##Get all rows from a table
def sqlSelectRows(strTableName, strWhereClause, selectOption = "*", database=database, orderBy = ''):
    ##First, get the column names
    lstCols = sqlDescribeTable(strTableName, database)
    try:
        conn = sqlite3.connect(database)
        c = conn.cursor()
        if strWhereClause != "":
            strQ = "SELECT " + selectOption + " FROM " + strTableName + " WHERE " + strWhereClause + ";"
        else:
            strQ = "SELECT " + selectOption + " FROM " + strTableName + ";"
        if orderBy:
            strQ = strQ[:-1] + ' ORDER BY ' + orderBy + ';'
        c.execute(strQ)
        lstRows = []

        if selectOption != '*':
            cols = selectOption.split(' ')
            for row in c:
                lstRow = {}
                for n in range(0, len(cols)):
                    col = cols[n].replace(',', '')
                    lstRow[col] = row[n]
                lstRows.append ( lstRow )
        else:
            for row in c:
                lstRow = {}
                for n in range(0, len(row)):
                    lstRow[lstCols[n]["name"]] = row[n]
                lstRows.append ( lstRow )

        return lstRows
    except sqlite3.Error as e:
        print ("ERROR in selecting row from table " + strTableName)
        print (strQ)
        print (strWhereClause)
        print (e)
        return []
    finally:
        conn.close()

def sqlMinRows(strTableName, strWhereClause, minColumn, database=database):
    ##First, get the column names

    lstCols = sqlDescribeTable(strTableName, database)
    try:
        conn = sqlite3.connect(database)
        c = conn.cursor()
        if strWhereClause != "":
            strQ = "SELECT MIN(" + minColumn + ") FROM " + strTableName + " WHERE " + strWhereClause + ";"
        else:
            strQ = "SELECT MIN(" + minColumn + ") FROM " + strTableName + ";"
        c.execute(strQ)
        lstRows = []
        for row in c:
            lstRow = {}
            result = sqlSelectRows(strTableName, minColumn + " = '" + str(row[0]) + "'", database=database)
            # for n in range(0, len(row)):
            #     lstRow[lstCols[n]["name"]] = row[n]
            # lstRows.append ( lstRow )

        return result
    except sqlite3.Error as e:
        print ("ERROR in selecting row from table " + strTableName)
        print (strQ)
        print (strWhereClause)
        print (e)
        return []
    finally:
        conn.close()

##Get all rows from a table
def sqlSelectMinMax(strTableName, strWhereClause, selectOption = "*", database=database):
    ##First, get the column names
    try:
        conn = sqlite3.connect(database)
        c = conn.cursor()
        lstCols = sqlDescribeTable(strTableName)
        if strWhereClause != "":
            strQ = "SELECT " + selectOption + " FROM " + strTableName + " WHERE " + strWhereClause + ";"
        else:
            strQ = "SELECT " + selectOption + " FROM " + strTableName + ";"
        c.execute(strQ)
        #minMax = c.fetchall()

        lstRows = []
        for row in c:
            lstRow = {}
            for n in range(0, len(row)):
                lstRow[lstCols[n]["name"]] = row[n]
            lstRows.append ( lstRow )

        return lstRows
    except sqlite3.Error as e:
        print ("ERROR in selecting row from table " + strTableName)
        print (strQ)
        print (strWhereClause)
        print (e)
        return []
    finally:
        conn.close()

##Get the table attributes
def sqlDescribeTable(strTableName, database=database):
    try:
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("PRAGMA table_info(" + strTableName + ")" )
        lstCols = []
        for row in c:
            lstCols.append ( { "name" : row[1], "type" : row[2] } )

        return lstCols
    except sqlite3.Error as e:
        print ("ERROR in creating table " + strTableName)
        print (e)
        return False
    finally:
        conn.close()

##Update a table
def sqlUpdateRows(strTableName, strWhereClause, jsnData, database=database):
    ##First, get the column names
    try:
        conn = sqlite3.connect(database)
        c = conn.cursor()
        strSetClause = " SET "
        for key in jsnData:
            strSetClause += key + " = '" + str(jsnData[key]) + "', "
        strSetClause = strSetClause[:-2]
        if strWhereClause != "":
            strQ = "UPDATE " + strTableName +  strSetClause + " WHERE " + strWhereClause + ";"
        else:
            strQ = "UPDATE " + strTableName + strSetClause + ";"
        c.execute(strQ)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print ("ERROR in selecting row from table " + strTableName)
        print (strQ)
        print (strWhereClause)
        print (e)
        return False
    finally:
        conn.close()


##Add a row to the table
def sqlAddRow(strTableName, dicRow, database=database):
    try:
        conn = sqlite3.connect(database)
        c = conn.cursor()
        strQ = "INSERT INTO " + strTableName + " ("
        for key in dicRow:
            strQ += key + ","
        strQ = strQ[:-1]
        strQ += ") VALUES ('"
        for key in dicRow:
            result = str(safe_str(dicRow[key]))
            strQ += result + "','"
        strQ = strQ[:-2] + ");"
        #print(strQ)
        c.execute(strQ)
        conn.commit()
        return c.lastrowid
    except sqlite3.Error as e:
        print ("ERROR in adding row to table " + strTableName)
        print (e)
        print (dicRow)
    finally:
        conn.close()

def safe_str(obj):
    try: 
        return str(obj)
    except UnicodeEncodeError:
        return obj.encode('ascii', 'ignore').decode('ascii')
    return ""

##Add a row to the table
def sqlDelRow(strTableName, strWhereClause, database=database):
    try:
        conn = sqlite3.connect(database)
        c = conn.cursor()
        if strWhereClause == "":
            strQ = "DELETE FROM " + strTableName 
        else:
            strQ = "DELETE FROM " + strTableName 
            strQ += " WHERE " + strWhereClause
        #print(strQ)
        c.execute(strQ)
        conn.commit()
    except sqlite3.Error as e:
        print ("ERROR in deleting row from table " + strTableName)
        print (e)
    finally:
        conn.close()


def sqlSumRows(strTableName, sumColumn, strWhereClause, database=database):
    ##First, get the column names
    lstCols = sqlDescribeTable(strTableName)
    try:
        conn = sqlite3.connect(database)
        c = conn.cursor()
        if strWhereClause != "":
            strQ = "SELECT SUM(" + sumColumn + ") FROM " + strTableName + " WHERE " + strWhereClause + ";"
        else:
            strQ ="SELECT SUM(" + sumColumn + ") FROM " + strTableName + ";"
        #print ( "sqlSelectRows: " + strQ )
        c.execute(strQ)
        sum = c.fetchone()
        
        return sum
    except sqlite3.Error as e:
        print ("ERROR in selecting row from table " + strTableName)
        print (strQ)
        print (strWhereClause)
        print (e)
    finally:
        conn.close()

def sqlCustomQuery(strQ, database=database):
    try:
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute(strQ)
        result = c.fetchall()
        
        return result
    except sqlite3.Error as e:
        print ("ERROR in custom SQL query:" )
        print (strQ)
        print (e)
    finally:
        conn.close()



if __name__ == '__main__':
    c = sqlSelectRows('tblLBCCustomers', 'username = "TESTIES1111"')[0]
    import json
    from os import listdir
    from os.path import isfile, join

    # mypath = 'C:\\Users\\aN4H3VPYitu\\inetpub\\vhosts\\default\\htdocs\\api\\App_Data\\txMonitoring'
    # onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

    # for file in onlyfiles:
    #     with open(mypath + '\\' + file) as json_file:
    #         data = json.load(json_file)

    #     if 'transaction_id' in data:
    #         trade = sqlSelectRows('tblClosedTrades', 'transaction_id = ' + str(data['transaction_id']))[0]
    #         addLBCTMRuleBreak(data, trade)


