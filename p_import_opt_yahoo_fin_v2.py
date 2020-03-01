import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from scipy import stats
from yahoo_fin import options
from yahoo_fin import stock_info as si
from requests_html import HTMLSession
import seaborn as sns
import feather
import sys
sns.set()


# utility functions and some declarations
# -----------------
# for extraction of expiration date of local symbol
pd.set_option("display.precision", 2)


symbol = sys.argv[-1]

#symbol='TTD'

#to_date_conv("AAPL200117C00050000")
def to_date_conv(localSymbol):
    try:
        return datetime.strptime(localSymbol [len(symbol)+0:len(symbol)+6],"%y%m%d")
    except:
        return datetime.strptime('2099-12-31 00:00:00',"%Y-%m-%d %H:%M:%S")

column_rename ={"Contract Name":"opt_symbol",
                "Strike": "strike",
                "Ask": "ask",
                "Bid": "bid",
                "Volume": "opt_volume", 
                "Last Price":"opt_lastprice",
                "Open Interest": "open_interest",
                "Implied Volatility": "imp_vola", 
                "Last Trade Date": "last_trade_date"}
column_order_detail=['opt_symbol',
                    'ul_price',
                    'expiration',
                    'days',
                    'put_call',
                    'strike',
                    'opt_price',
                    'opt_timeval',
                    'opt_innerval',
                    'beven_price',
                    'beven_dist',
                    'beven_pct',
                    'pos_size',
                    'yield_max',
                    'yield_pa',
                    'ul_ymax',
                    'opt_pr_pct',
                    'imp_vola',
                    'opt_lastprice',
                    'mid',
                    'bid',
                    'ask',
                    'spread',
                    'opt_volume',
                    'open_interest',
                    'last_trade_date',
                    'last_trade_days']
column_order=  [ 'ul_price',
                 'days',
                 'put_call',
                 'strike',
                 'opt_price',
                 'opt_timeval',
                 'opt_innerval',
                 'beven_price',
                 'beven_pct',
                 'yield_max',
                 'yield_pa',
                 'ul_ymax',
                 'imp_vola',
                 'opt_pr_pct']

# -----------------
# main part
# -----------------

ul_price= si.get_live_price(symbol).round(1)

# get option chain first
l=options.get_expiration_dates(symbol)
count=0
df=pd.DataFrame()

# extract option chains by expiration dates

for x in l:
    count=count+1
    if count >= 0 and count <=100:
        df_calls=pd.DataFrame()
        df_puts=pd.DataFrame()
        try:
            expiration=datetime.strptime(x,"%B %d, %Y").strftime('%d/%m/%Y')
            da=options.get_options_chain(symbol,expiration)
            df_calls=df_calls.append(pd.DataFrame(da['calls']),ignore_index=True)
            df_puts =df_puts.append(pd.DataFrame(da['puts']),ignore_index=True)
            df_calls=df_calls.loc[(df_calls['Bid']!=0)&(df_calls['Ask']!=0)]
            df_calls=df_calls.loc[(df_calls['Bid']!='-')&(df_calls['Ask']!='-')]
            df_puts =df_puts.loc[(df_puts['Bid']!=0)&(df_puts['Ask']!=0)]
            df_puts =df_puts.loc[(df_puts['Bid']!='-')&(df_puts['Ask']!='-')]
            df=df.append(df_calls,ignore_index=True)
            df=df.append(df_puts,ignore_index=True)

            print("#",count,"  ",expiration, " C: ",len(df_calls)," P: ",len(df_puts))
            if count >10000:
                break
        except:
            print ("issue at expiration",x)

# 1 standardize data feed

# 1.1  rename columns
df=df.rename(columns=column_rename)

# 1.2  delete invalid records
df=df.loc[df["open_interest"].astype(str) !="-"]

# 1.3  filter input
#df=df.loc[df["open_interest"].astype(int) >=0]

# 1.4  directly assigned or transformed attributes 
df['ul_price']=ul_price
df['put_call']=df['opt_symbol'].apply(lambda x: 'C' if x.find('C00') >0 else 'P' )
df['imp_vola']=df['imp_vola'].astype(str).apply(lambda x: float(x.replace(',','').replace('%','')))
df['expiration']=df['opt_symbol'].apply(lambda x: to_date_conv(x) )

# 1.5  calculated and derived attributes
df['days']=df['expiration'].apply(lambda x: (x-datetime.now()).days)
df['last_trade_days']=df['last_trade_date'].apply(lambda x: (datetime.now()-datetime.strptime(x[0:10],"%Y-%m-%d")).days)
df['mid']=(df['ask'].astype(float)+df['bid'].astype(float))/2
df['spread']=(df['ask'].astype(float)-df['bid'].astype(float))/df['mid']
df['opt_price']=df['mid']
df['pos_size']=df['strike']*100

# 1.6  calculated values based on P/C 

def do_break_even (pos):
    if df.loc[pos,'put_call']=='C':
        df.loc[pos,'beven_price']=df.loc[pos,'strike']+df.loc[pos,'opt_price']
        df.loc[pos,'beven_dist']=df.loc[pos,'beven_price']-df.loc[pos,'ul_price']
        df.loc[pos,'opt_innerval']=df.loc[pos,'ul_price']-df.loc[pos,'strike']
    if df.loc[pos,'put_call']=='P':
        df.loc[pos,'beven_price']=df.loc[pos,'strike']-df.loc[pos,'opt_price']
        df.loc[pos,'beven_dist']=df.loc[pos,'ul_price']-df.loc[pos,'beven_price']
        df.loc[pos,'opt_innerval']=df.loc[pos,'strike']-df.loc[pos,'ul_price']
    df.loc[pos,'beven_pct']= df.loc[pos,'beven_dist']/df.loc[pos,'ul_price']*100
    df.loc[pos,'opt_timeval']= df.loc[pos,'opt_price']-max(0, df.loc[pos,'opt_innerval'])
    df.loc[pos,'opt_pr_pct']= ( df.loc[pos,'opt_timeval']/df.loc[pos,'opt_price'])*100
    df['yield_max']=(((df['ul_price']+df['opt_timeval'])/df['ul_price'])-1)*100
    df['yield_pa']=((((1+(df['yield_max']/100))**(1/(df["days"]/365.25)))-1)*100)
    df['ul_ymax']=df['ul_price']*(1+(df['yield_max']/100))

df.reset_index(inplace=True)
for x in df.index.values:
    do_break_even(x)


# 2.1 reset column_order
df=df[column_order_detail]


# 3.1 reports for CALLS
wcl=  (df['opt_price']>0) \
    & (df['days']>20) \
    & (df['put_call']=='C') \
    & (df['beven_pct']>0)
df_call=df.loc[wcl][column_order].sort_values('yield_pa',ascending=False).head(1000)

# 3.2 reports for PUTS

wcl=  (df['opt_price']>0) \
    & (df['days']>20) \
    & (df['put_call']=='P') \
    & (df['yield_pa']>5) \
    & (df['beven_pct']>0)
df_put=df.loc[wcl][column_order].sort_values('yield_pa',ascending=False).head(1000)


#file_feather="df_aapl_08012020"
#df.to_feather(file_feather)

# export df to excel
path="exp_"+symbol+"_"+datetime.now().strftime("%Y_%m_%d_%H00")+".xlsx"

print ("export to file", path)

writer = pd.ExcelWriter(path)
df.to_excel(writer,sheet_name='all')
df_call.to_excel(writer,sheet_name='call')
df_put.to_excel(writer,sheet_name='put')

writer.save()
writer.close()

print ("done", path)
