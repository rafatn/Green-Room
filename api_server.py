from __future__ import annotations
import os, math, time
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title='Green Room API', version='5.5.0')

allowed = [x.strip() for x in os.getenv('CORS_ORIGINS','*').split(',') if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed, allow_credentials=False, allow_methods=['GET'], allow_headers=['*'])

FINNHUB_KEY=os.getenv('FINNHUB_API_KEY','').strip()
ALPHA_KEY=os.getenv('ALPHA_VANTAGE_API_KEY','').strip()

async def get_json(url, params=None):
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
        r=await c.get(url, params=params)
        r.raise_for_status()
        return r.json()

@app.get('/')
async def root():
    return {'name':'Green Room API','version':'5.5.0','docs':'/docs'}

@app.get('/api/health')
async def health():
    return {'ok':True,'providers':{'finnhub':bool(FINNHUB_KEY),'alpha_vantage':bool(ALPHA_KEY)}}

@app.get('/api/providers')
async def providers():
    return {'providers':[
        {'name':'Finnhub','configured':bool(FINNHUB_KEY),'freshness':'REALTIME'},
        {'name':'Alpha Vantage','configured':bool(ALPHA_KEY),'freshness':'HISTORICAL/EOD'},
    ]}

async def quote_finnhub(symbol):
    if not FINNHUB_KEY: return None
    d=await get_json('https://finnhub.io/api/v1/quote',{'symbol':symbol,'token':FINNHUB_KEY})
    if not d or d.get('c') in (None,0): return None
    return {'symbol':symbol,'price':d.get('c'),'change':d.get('d'),'percent_change':d.get('dp'),'currency':'USD','provider':'Finnhub','freshness':'REALTIME','timestamp':datetime.now(timezone.utc).isoformat()}

async def quote_alpha(symbol):
    if not ALPHA_KEY: return None
    d=await get_json('https://www.alphavantage.co/query',{'function':'GLOBAL_QUOTE','symbol':symbol,'apikey':ALPHA_KEY})
    q=d.get('Global Quote') or {}
    if not q.get('05. price'): return None
    return {'symbol':symbol,'price':float(q['05. price']),'change':float(q.get('09. change','nan')) if q.get('09. change') else None,'percent_change':float(str(q.get('10. change percent','0')).replace('%','')),'currency':'USD','provider':'Alpha Vantage','freshness':'END OF DAY','timestamp':q.get('07. latest trading day')}

@app.get('/api/quotes')
async def quotes(symbols: str):
    syms=[s.strip().upper() for s in symbols.split(',') if s.strip()][:30]
    out=[]
    for s in syms:
        item=None
        for fn in (quote_finnhub, quote_alpha):
            try:
                item=await fn(s)
                if item: break
            except Exception: pass
        out.append(item or {'symbol':s,'price':None,'change':None,'percent_change':None,'currency':'USD','provider':None,'freshness':'UNAVAILABLE','timestamp':None})
    return {'quotes':out}

def period_days(period):
    return {'1m':31,'3m':93,'6m':186,'1y':366,'5y':1826,'max':3650}.get(period,366)

async def history_finnhub(symbol, days):
    if not FINNHUB_KEY:return None
    now=int(time.time()); start=now-days*86400
    d=await get_json('https://finnhub.io/api/v1/stock/candle',{'symbol':symbol,'resolution':'D','from':start,'to':now,'token':FINNHUB_KEY})
    if d.get('s')!='ok':return None
    return [{'date':datetime.fromtimestamp(t,timezone.utc).date().isoformat(),'close':v} for t,v in zip(d.get('t',[]),d.get('c',[]))]

async def history_alpha(symbol):
    if not ALPHA_KEY:return None
    d=await get_json('https://www.alphavantage.co/query',{'function':'TIME_SERIES_DAILY_ADJUSTED','symbol':symbol,'outputsize':'full','apikey':ALPHA_KEY})
    ts=d.get('Time Series (Daily)')
    if not ts:return None
    return [{'date':k,'close':float(v['5. adjusted close'])} for k,v in sorted(ts.items())]

@app.get('/api/history')
async def history(symbol: str, period: str='1y'):
    symbol=symbol.upper(); days=period_days(period); pts=None; provider=None
    try:
        pts=await history_finnhub(symbol,days); provider='Finnhub' if pts else None
    except Exception: pts=None
    if not pts:
        try:
            allpts=await history_alpha(symbol); pts=allpts[-days:] if allpts else None; provider='Alpha Vantage' if pts else None
        except Exception: pts=None
    if not pts: return {'symbol':symbol,'period':period,'points':[],'provider':None,'freshness':'UNAVAILABLE','error':'No historical data available. Configure an API provider on the FastAPI server.'}
    return {'symbol':symbol,'period':period,'points':pts,'provider':provider,'freshness':'REALTIME/HISTORICAL' if provider=='Finnhub' else 'END OF DAY'}

def stats(points):
    vals=[float(x['close']) for x in points if x.get('close') is not None]
    if len(vals)<2:return 0,0,0
    rets=[vals[i]/vals[i-1]-1 for i in range(1,len(vals))]
    cagr=(vals[-1]/vals[0])**(252/max(1,len(rets)))-1
    mean=sum(rets)/len(rets); vol=(sum((r-mean)**2 for r in rets)/max(1,len(rets)-1))**0.5*math.sqrt(252)
    peak=vals[0]; mdd=0
    for v in vals:
        peak=max(peak,v); mdd=min(mdd,v/peak-1)
    return cagr,vol,mdd

def years_to_target(initial,monthly,target,annual,max_years):
    value=initial
    for m in range(1,max_years*12+1):
        value=value*(1+annual/12)+monthly
        if value>=target:return round(m/12,2)
    return None

@app.get('/api/dynamic-path')
async def dynamic_path(symbols:str, initial:float=10000, monthly:float=500, target:float=25000, max_years:int=10):
    rows=[]
    for s in [x.strip().upper() for x in symbols.split(',') if x.strip()][:30]:
        h=await history(s,'5y')
        cagr,vol,mdd=stats(h.get('points',[]))
        rows.append({'symbol':s,'historical_cagr':cagr,'volatility':vol,'max_drawdown':mdd,'years_to_target':years_to_target(initial,monthly,target,cagr,max_years) if h.get('points') else None,'error':not bool(h.get('points'))})
    return {'results':rows}

@app.get('/api/portfolio-path')
async def portfolio_path(symbols:str, weights:str, initial:float=10000, monthly:float=500, years:int=5):
    syms=[x.strip().upper() for x in symbols.split(',') if x.strip()]; ws=[float(x.strip()) for x in weights.split(',') if x.strip()]
    if len(syms)!=len(ws) or not syms:return {'error':'Number of weights must match selected companies.'}
    total=sum(ws)
    if total<=0:return {'error':'Weights must be positive.'}
    ws=[w/total for w in ws]
    cagr=[]; vols=[]
    for s in syms:
        h=await history(s,'5y'); a,v,_=stats(h.get('points',[])); cagr.append(a); vols.append(v)
    if any(not math.isfinite(x) for x in cagr):return {'error':'Historical data unavailable for one or more companies.'}
    annual=sum(w*a for w,a in zip(ws,cagr)); vol=sum(w*v for w,v in zip(ws,vols))
    value=initial; path=[{'month':0,'value':round(value,2)}]
    for m in range(1,years*12+1):
        value=value*(1+annual/12)+monthly; path.append({'month':m,'value':round(value,2)})
    return {'historical_cagr':annual,'volatility':vol,'path':path}
