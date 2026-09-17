import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import plotly.graph_objects as go
from scipy import stats
import io

warnings.filterwarnings("ignore")

# ── Chart theme ───────────────────────────────────────────────
FONT    = "Inter,-apple-system,BlinkMacSystemFont,sans-serif"
C_BLUE  = "#2563eb"; C_INDIGO = "#4f46e5"; C_PURPLE = "#7c3aed"
C_GREEN = "#16a34a"; C_RED    = "#dc2626"; C_AMBER  = "#d97706"
C_TEAL  = "#0891b2"; C_GRAY   = "#6b7280"; C_DARK   = "#1e293b"
PALETTE = [C_BLUE,C_INDIGO,C_PURPLE,C_TEAL,C_GREEN,C_AMBER,C_RED,"#db2777","#0f766e"]

def base_layout(title="",height=400,margin=None,legend=True):
    m = margin or dict(l=60,r=30,t=50 if title else 30,b=50)
    return dict(
        title=dict(text=title,font=dict(size=14,color=C_DARK,family=FONT),x=0,xanchor="left",pad=dict(l=4)),
        height=height,plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
        font=dict(family=FONT,size=12,color=C_DARK),margin=m,showlegend=legend,
        legend=dict(bgcolor="rgba(0,0,0,0)",borderwidth=0,font=dict(size=11,color=C_GRAY)),
        xaxis=dict(showgrid=True,gridcolor="#f1f5f9",gridwidth=1,zeroline=False,
                   linecolor="#e2e8f0",linewidth=1,tickfont=dict(size=11,color=C_GRAY),
                   title_font=dict(size=12,color=C_GRAY)),
        yaxis=dict(showgrid=True,gridcolor="#f1f5f9",gridwidth=1,zeroline=False,
                   linecolor="#e2e8f0",linewidth=1,tickfont=dict(size=11,color=C_GRAY),
                   title_font=dict(size=12,color=C_GRAY)),
    )

def apply_theme(fig,title="",height=400,margin=None,legend=True):
    fig.update_layout(**base_layout(title,height,margin,legend))
    return fig

# ── Page config ───────────────────────────────────────────────
st.set_page_config(page_title="Valuation",layout="wide",initial_sidebar_state="collapsed")

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"],.stApp,button,input,label,p,div,span{
  font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif !important;
}
[data-testid="collapsedControl"]{display:none !important;}
header[data-testid="stHeader"]{display:none !important;}
.block-container{padding:0 !important;max-width:100% !important;}
[data-testid="stSidebar"]{display:none !important;}
div[data-testid="stMetric"]{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;}
div[data-testid="stNumberInput"] input,div[data-testid="stTextInput"] input{font-size:13px !important;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:2px;}

/* All buttons default: nav style */
div[data-testid="stButton"]>button{
  background:transparent !important;color:#6b7280 !important;
  border:0.5px solid transparent !important;font-weight:400 !important;
  text-align:left !important;justify-content:flex-start !important;
  padding:7px 10px !important;border-radius:8px !important;
  font-size:12px !important;width:100% !important;
  transition:all 0.12s !important;
}
div[data-testid="stButton"]>button:hover{
  background:#f1f5f9 !important;color:#1a1a2e !important;
  border-color:#e2e8f0 !important;
}
/* Hide Material icons injected by newer Streamlit versions */
div[data-testid="stButton"]>button [data-testid="stIconMaterial"],
div[data-testid="stButton"]>button span[aria-hidden="true"],
div[data-testid="stButton"]>button [class*="icon"],
div[data-testid="stButton"]>button svg{display:none !important;}

/* Run Valuation — blue filled button */
div[data-testid="stButton"]:has(button[key="run_val"])>button{
  background:#2563eb !important;color:#fff !important;
  font-weight:600 !important;border:none !important;
  text-align:center !important;justify-content:center !important;
  font-size:13px !important;padding:9px 10px !important;
}
div[data-testid="stButton"]:has(button[key="run_val"])>button:hover{
  background:#1d4ed8 !important;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# SECTOR COMPS
# ═══════════════════════════════════════════════════════════════
SECTOR_COMPS = {
    "Technology":["AAPL","MSFT","GOOGL","META","AMZN","ORCL","CRM","NVDA","AVGO","INTU"],
    "Consumer Cyclical":["AMZN","TSLA","HD","NKE","MCD","BKNG","TGT","LOW","SBUX"],
    "Healthcare":["JNJ","UNH","PFE","ABBV","MRK","TMO","ABT","LLY","AMGN","GILD"],
    "Financial Services":["JPM","BAC","WFC","GS","MS","BLK","SCHW","AXP","COF"],
    "Communication Services":["GOOGL","META","NFLX","DIS","T","VZ","CMCSA","SNAP"],
    "Industrials":["CAT","BA","HON","UPS","GE","RTX","LMT","DE","NOC"],
    "Consumer Defensive":["PG","KO","PEP","WMT","COST","CL","GIS","MDLZ"],
    "Energy":["XOM","CVX","COP","SLB","EOG","PSX","VLO","MPC"],
    "Utilities":["NEE","DUK","SO","D","EXC","SRE","AEP","XEL"],
    "Real Estate":["AMT","PLD","CCI","EQIX","SPG","O","PSA","WELL"],
    "Basic Materials":["LIN","APD","ECL","NEM","FCX","DOW","DD","ALB"],
}

# ═══════════════════════════════════════════════════════════════
# DATA FUNCTIONS
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def get_rf():
    try:
        df = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10",parse_dates=["DATE"])
        df = df[df["DGS10"]!="."]
        return float(df["DGS10"].iloc[-1])/100
    except: return 0.043

@st.cache_data(ttl=900)
def fetch_company(ticker):
    t = yf.Ticker(ticker)
    return t.info, t.history(period="5y"), t.financials, t.cashflow, t.balance_sheet

@st.cache_data(ttl=600)
def fetch_movers():
    universe = ["AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","AVGO","JPM","V",
                "UNH","XOM","WMT","MA","PG","JNJ","HD","COST","PEP","KO",
                "BAC","MRK","ABBV","CVX","CRM","NFLX","AMD","INTC","DIS","BA",
                "GE","MS","GS","ORCL","IBM","CSCO","PFE","LLY","QCOM","TXN"]
    rows = []
    try:
        data = yf.download(" ".join(universe),period="2d",interval="1d",
                           group_by="ticker",auto_adjust=True,progress=False)
        for t in universe:
            try:
                prices = data[t]["Close"].dropna() if t in data.columns.get_level_values(0) else pd.Series()
                if len(prices)>=2:
                    prev,curr = float(prices.iloc[-2]),float(prices.iloc[-1])
                    chg = curr-prev; pct = chg/prev*100 if prev else 0
                    rows.append({"ticker":t,"price":curr,"chg":chg,"pct":pct})
            except: pass
    except: pass
    if not rows: return [],[],[]
    df = pd.DataFrame(rows).dropna()
    df = df[df["pct"].abs()>0.01].sort_values("pct",ascending=False)
    gainers = df[df["pct"]>0].head(4).to_dict("records")
    losers  = df[df["pct"]<0].tail(4).to_dict("records")
    top7    = pd.concat([df.head(4),df.tail(3)]).drop_duplicates("ticker")
    top7    = top7.reindex(top7["pct"].abs().sort_values(ascending=False).index)
    return top7.to_dict("records"), gainers, losers

@st.cache_data(ttl=600)
def fetch_indices():
    syms = {"S&P 500":"^GSPC","Nasdaq":"^IXIC","Dow":"^DJI","VIX":"^VIX"}
    result = {}
    try:
        for name,sym in syms.items():
            data = yf.download(sym,period="2d",interval="1d",auto_adjust=True,progress=False)
            if len(data)>=2:
                prev,curr = float(data["Close"].iloc[-2]),float(data["Close"].iloc[-1])
                result[name] = {"price":curr,"chg":curr-prev,"pct":(curr-prev)/prev*100}
    except: pass
    return result

@st.cache_data(ttl=600)
def fetch_sparkline(ticker):
    try:
        data = yf.download(ticker,period="5d",interval="1h",auto_adjust=True,progress=False)
        return data["Close"].dropna().tolist()
    except: return []

@st.cache_data(ttl=3600)
def fetch_comps(tickers, exclude):
    rows = []
    for t in tickers:
        if t==exclude.upper(): continue
        try:
            info = yf.Ticker(t).info
            rows.append({"Ticker":t,"Name":info.get("shortName",t),
                         "EV/EBITDA":info.get("enterpriseToEbitda"),
                         "EV/Revenue":info.get("enterpriseToRevenue"),
                         "P/E (TTM)":info.get("trailingPE"),
                         "Fwd P/E":info.get("forwardPE"),
                         "Mkt Cap ($B)":round((info.get("marketCap") or 0)/1e9,1),
                         "Rev Growth":info.get("revenueGrowth"),
                         "EBITDA Margin":info.get("ebitdaMargins"),
                         "Gross Margin":info.get("grossMargins"),
                         "ROE":info.get("returnOnEquity")})
        except: pass
    return pd.DataFrame(rows)

def extract_financials(info, fin, cf, bs, ticker_sym):
    d = {}
    for k,ik in [("revenue","totalRevenue"),("ebitda","ebitda"),("net_income","netIncomeToCommon"),
                 ("gross_profit","grossProfits"),("total_debt","totalDebt"),("cash","totalCash"),
                 ("shares","sharesOutstanding"),("mkt_cap","marketCap"),("dividend","dividendRate"),
                 ("payout_ratio","payoutRatio"),("roe","returnOnEquity"),("roic","returnOnAssets"),
                 ("ebitda_margin","ebitdaMargins"),("gross_margin","grossMargins"),
                 ("rev_growth","revenueGrowth"),("earnings_growth","earningsGrowth"),
                 ("interest_expense","interestExpense"),("minority_interest","minorityInterest"),
                 ("preferred_stock","preferredStock"),("fwd_eps","forwardEps"),
                 ("trailing_eps","trailingEps"),("analyst_target","targetMeanPrice"),
                 ("enterprise_value","enterpriseValue")]:
        d[k] = info.get(ik) or 0
    d["price"]      = info.get("currentPrice") or info.get("regularMarketPrice") or 0
    d["beta"]       = info.get("beta") or 1.0
    d["pe"]         = info.get("trailingPE")
    d["fwd_pe"]     = info.get("forwardPE")
    d["ev_ebitda"]  = info.get("enterpriseToEbitda")
    d["ev_revenue"] = info.get("enterpriseToRevenue")
    d["sector"]     = info.get("sector") or "Unknown"
    d["industry"]   = info.get("industry") or "Unknown"
    d["name"]       = info.get("longName") or info.get("shortName") or ticker_sym
    d["country"]    = info.get("country") or ""
    d["description"]= info.get("longBusinessSummary") or ""
    d["shares"]     = d["shares"] or 1
    if not d["enterprise_value"]: d["enterprise_value"] = d["mkt_cap"]
    # Rev history
    rev_hist = []
    if fin is not None and not fin.empty:
        for idx in fin.index:
            if "revenue" in idx.lower():
                rev_hist = list(fin.loc[idx].dropna().values[::-1]); break
    d["rev_hist"] = rev_hist
    # FCF
    fcf = 0
    if cf is not None and not cf.empty:
        for idx in cf.index:
            if "free cash flow" in idx.lower():
                vals = cf.loc[idx].dropna()
                if len(vals): fcf = float(vals.iloc[0])
                break
        if fcf==0:
            ocf=capex=0
            for idx in cf.index:
                if "operating" in idx.lower() and "cash" in idx.lower():
                    vals = cf.loc[idx].dropna()
                    if len(vals): ocf = float(vals.iloc[0])
                if "capital" in idx.lower() or "capex" in idx.lower():
                    vals = cf.loc[idx].dropna()
                    if len(vals): capex = float(vals.iloc[0])
            fcf = ocf+capex
    d["fcf"] = fcf
    return d

# ═══════════════════════════════════════════════════════════════
# VALUATION ENGINES
# ═══════════════════════════════════════════════════════════════
def compute_wacc(d,rf,tax=0.21):
    beta = max(float(d["beta"] or 1.0),0.3)
    cost_eq = rf+beta*0.055
    dbt = d["total_debt"] or 0; mc = d["mkt_cap"] or 1
    cost_dbt = max(rf+0.015,0.04)
    if d["interest_expense"] and dbt>0:
        cost_dbt = max(min(abs(d["interest_expense"])/dbt,0.15),0.03)
    tc = mc+dbt; ew = mc/tc if tc>0 else 1.0; dw = dbt/tc if tc>0 else 0.0
    return round(ew*cost_eq+dw*cost_dbt*(1-tax),4),round(cost_eq,4),round(cost_dbt,4),round(ew,4),round(dw,4)

def estimate_growth(rev_hist):
    if len(rev_hist)>=2:
        rates=[(rev_hist[i]-rev_hist[i-1])/abs(rev_hist[i-1]) for i in range(1,len(rev_hist)) if rev_hist[i-1]]
        if rates: return float(np.median(rates))
    return 0.08

def dcf_2stage(fcf,g1,wacc,tg,years=5,debt=0,cash=0,shares=1):
    if not shares or not fcf: return 0,0,[]
    f=fcf; pvs=[]
    for i in range(1,years+1): f=f*(1+g1); pvs.append(f/(1+wacc)**i)
    tv = pvs[-1]*(1+wacc)**years*(1+tg)/(wacc-tg) if wacc>tg else 0
    ev = sum(pvs)+tv/(1+wacc)**years
    return (ev-debt+cash)/shares,ev,pvs

def dcf_3stage(fcf,g1,g2,wacc,tg,y1=3,y2=4,debt=0,cash=0,shares=1):
    if not shares or not fcf: return 0,0,[]
    f=fcf; pvs=[]; fcfs=[]
    for i in range(1,y1+1): f=f*(1+g1); pvs.append(f/(1+wacc)**i); fcfs.append(f)
    for i,gr in enumerate(np.linspace(g1,g2,y2),start=y1+1):
        f=f*(1+gr); pvs.append(f/(1+wacc)**i); fcfs.append(f)
    tv=fcfs[-1]*(1+tg)/(wacc-tg) if wacc>tg else 0
    ev=sum(pvs)+tv/(1+wacc)**(y1+y2)
    return (ev-debt+cash)/shares,ev,pvs

def dcf_mc(fcf,gm,gs,wm,ws,tg,n=10000,years=5,debt=0,cash=0,shares=1):
    np.random.seed(42); out=[]
    for _ in range(n):
        g=np.random.normal(gm,gs); w=max(np.random.normal(wm,ws),tg+0.01)
        tgr=min(np.random.normal(tg,0.005),w-0.01)
        f=fcf; pv=0
        for i in range(1,years+1): f=f*(1+g); pv+=f/(1+w)**i
        tv=f*(1+tgr)/(w-tgr) if w>tgr else 0
        out.append((pv+tv/(1+w)**years-debt+cash)/shares if shares else 0)
    return np.array(out)

def reverse_dcf(price,shares,debt,cash,fcf,wacc,tg,years=10):
    target=price*shares+debt-cash
    def ev_at(g):
        f=fcf; pv=0
        for i in range(1,years+1): f=f*(1+g); pv+=f/(1+wacc)**i
        tv=f*(1+tg)/(wacc-tg) if wacc>tg else 0
        return pv+tv/(1+wacc)**years
    lo,hi=-0.3,0.8
    if ev_at(lo)>target: return lo
    if ev_at(hi)<target: return hi
    for _ in range(60):
        mid=(lo+hi)/2
        if ev_at(mid)<target: lo=mid
        else: hi=mid
    return round((lo+hi)/2,4)

def ddm_gordon(div,g,ke):
    return div*(1+g)/(ke-g) if ke>g and div else None

def ddm_multistage(div,g1,g2,ke,years=5):
    if ke<=g2 or not div: return None
    d=div; pvs=[]
    for i in range(1,years+1): d=d*(1+g1); pvs.append(d/(1+ke)**i)
    return sum(pvs)+d*(1+g2)/(ke-g2)/(1+ke)**years

def comps_implied(d,cdf):
    res={}; debt=d["total_debt"]; cash=d["cash"]; shares=d["shares"]
    ev2eq=lambda ev:(ev-debt+cash)/shares if shares else 0
    if d["ebitda"]>0:
        med=cdf["EV/EBITDA"].dropna().median()
        if pd.notna(med): res["EV/EBITDA Comps"]=ev2eq(d["ebitda"]*med)
    if d["revenue"]>0:
        med=cdf["EV/Revenue"].dropna().median()
        if pd.notna(med): res["EV/Revenue Comps"]=ev2eq(d["revenue"]*med)
    if d["net_income"]>0:
        med=cdf["P/E (TTM)"].dropna().median()
        if pd.notna(med): res["P/E Comps"]=(d["net_income"]*med)/shares if shares else 0
    return res

def comps_regression(d,cdf):
    sub=cdf[["EV/EBITDA","Rev Growth"]].dropna()
    if len(sub)<3 or not d["ebitda"] or d["ebitda"]<=0: return None,None,None
    x=sub["Rev Growth"].values; y=sub["EV/EBITDA"].values
    sl,ic,r,_,_=stats.linregress(x,y)
    cg=d["rev_growth"] or estimate_growth(d["rev_hist"])
    imp=max(ic+sl*cg,1.0)
    debt=d["total_debt"]; cash=d["cash"]; shares=d["shares"]
    return (d["ebitda"]*imp-debt+cash)/shares,imp,r**2

def sensitivity_table(fcf,wm,gm,tg,debt,cash,shares,years):
    wr=np.arange(wm-0.02,wm+0.025,0.005)
    gr=np.arange(gm-0.04,gm+0.045,0.010)
    rows={}
    for g in gr:
        row={}
        for w in wr:
            if w<=tg: row[round(w,3)]=np.nan
            else:
                p,_,_=dcf_2stage(fcf,g,w,tg,years,debt,cash,shares)
                row[round(w,3)]=round(p,2)
        rows[round(g,3)]=row
    df=pd.DataFrame(rows).T; df.index.name="Growth Rate"; df.columns.name="WACC"
    return df

def build_excel(d,wacc,cost_eq,rf,tg,g1,fcf_base,years,cdf,bars):
    buf=io.BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as writer:
        pd.DataFrame({"Metric":list(d.keys()),"Value":list(d.values())}).to_excel(writer,sheet_name="Overview",index=False)
        if bars:
            pd.DataFrame([{"Method":n,"Bear":lo,"Base":mid,"Bull":hi} for n,lo,hi,mid in bars]).to_excel(writer,sheet_name="Valuation Summary",index=False)
        if cdf is not None and not cdf.empty:
            cdf.to_excel(writer,sheet_name="Comparable Companies",index=False)
        sensitivity_table(fcf_base,wacc,g1,tg,d["total_debt"],d["cash"],d["shares"],years).to_excel(writer,sheet_name="DCF Sensitivity")
    buf.seek(0); return buf.getvalue()

# ═══════════════════════════════════════════════════════════════
# FORMATTING
# ═══════════════════════════════════════════════════════════════
def fB(v):
    if v is None: return "N/A"
    s="-$" if v<0 else "$"; av=abs(v)
    if av>=1e12: return f"{s}{av/1e12:.2f}T"
    if av>=1e9:  return f"{s}{av/1e9:.1f}B"
    if av>=1e6:  return f"{s}{av/1e6:.0f}M"
    return f"{s}{av:,.0f}"
def fp(v): return "N/A" if v is None else f"{v*100:.1f}%"
def fx(v):
    if v is None or (isinstance(v,float) and (np.isnan(v) or np.isinf(v))): return "N/A"
    return f"{v:.1f}x"

def initial_circle(ticker, size=28):
    colors=["#2563eb","#7c3aed","#0891b2","#059669","#d97706","#dc2626","#db2777","#0f766e"]
    c=colors[sum(ord(x) for x in ticker)%len(colors)]
    initials=ticker[:2].upper()
    return (f"<span style='display:inline-flex;align-items:center;justify-content:center;"
            f"width:{size}px;height:{size}px;border-radius:50%;background:{c};"
            f"font-size:{int(size*0.33)}px;font-weight:700;color:#fff;flex-shrink:0;"
            f"font-family:Inter,sans-serif;'>{initials}</span>")

def mini_sparkline(prices,color="#2563eb",width=80,height=30):
    if not prices or len(prices)<2: return ""
    mn,mx=min(prices),max(prices); rng=mx-mn or 1
    pts=[(int(i/(len(prices)-1)*(width-2)+1),int(height-2-(p-mn)/rng*(height-4)+1)) for i,p in enumerate(prices)]
    poly=" ".join(f"{x},{y}" for x,y in pts)
    fill=poly+f" {width-1},{height-1} 1,{height-1}"
    uid=f"sp{abs(hash(str(prices[:3])))%99999}"
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<defs><linearGradient id="{uid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity="0.2"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
            f'</linearGradient></defs>'
            f'<polygon points="{fill}" fill="url(#{uid})"/>'
            f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"/></svg>')

GLOSSARY={
    "Market Cap":"Share price × shares outstanding — total equity market value.",
    "Enterprise Value":"Market Cap + debt − cash. The full acquisition cost of the business.",
    "Revenue":"Total sales before any costs. Also called the top line.",
    "EBITDA":"Earnings Before Interest, Tax, Depreciation & Amortisation. A cash-flow proxy.",
    "FCF":"Free Cash Flow — operating cash flow minus capex.",
    "Net Income":"Bottom-line profit after all expenses and taxes.",
    "Gross Margin":"Gross profit ÷ revenue. Measures pricing power.",
    "EBITDA Margin":"EBITDA ÷ revenue. Measures operating efficiency.",
    "EV/EBITDA":"Capital-structure-neutral valuation multiple. Lower = cheaper.",
    "EV/Revenue":"EV ÷ Revenue. Used for high-growth companies.",
    "P/E TTM":"Price ÷ trailing 12-month earnings per share.",
    "Fwd P/E":"Price ÷ next year's estimated earnings per share.",
    "WACC":"Weighted Average Cost of Capital — the DCF discount rate.",
    "Beta":"Sensitivity to market moves. Beta 1.5 = stock moves 1.5× the market.",
    "Net Debt":"Total debt minus cash. Positive = net debt; negative = net cash.",
    "ND/EBITDA":"Leverage ratio. Above 4× is considered high.",
    "ROE":"Return on Equity — net income ÷ shareholders equity.",
    "Rev Growth":"Year-over-year revenue growth rate.",
    "Risk-Free Rate":"10-year US Treasury yield — the baseline for WACC.",
}

def tt(label):
    tip=GLOSSARY.get(label,""); 
    if not tip: return ""
    safe=tip.replace("'","&#39;").replace('"',"&quot;")
    return (f'<span style="position:relative;display:inline-flex;align-items:center;"'
            f' onmouseenter="this.querySelector(\'span.tb\').style.display=\'block\'"'
            f' onmouseleave="this.querySelector(\'span.tb\').style.display=\'none\'">'
            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:13px;height:13px;border-radius:50%;background:#e2e8f0;color:#6b7280;'
            f'font-size:8px;font-weight:700;cursor:default;flex-shrink:0;margin-left:3px;">?</span>'
            f'<span class="tb" style="display:none;position:absolute;bottom:calc(100% + 6px);'
            f'left:50%;transform:translateX(-50%);background:#1e293b;color:#f1f5f9;'
            f'font-size:11px;line-height:1.5;padding:7px 10px;border-radius:6px;width:200px;'
            f'white-space:normal;z-index:9999;box-shadow:0 4px 16px rgba(0,0,0,.4);'
            f'font-family:Inter,sans-serif;font-weight:400;text-transform:none;letter-spacing:0;">'
            f'{safe}</span></span>')

# ═══════════════════════════════════════════════════════════════
# CONCEPT B: KEY FINANCIALS RENDERER
# Horizontal band table with sector-relative progress bars
# ═══════════════════════════════════════════════════════════════
def sector_percentile(value, sector_values):
    """Return 0-100 percentile of value within sector_values list."""
    if not sector_values or value is None: return 50
    valid = [v for v in sector_values if v is not None and not np.isnan(v)]
    if not valid: return 50
    below = sum(1 for v in valid if v <= value)
    return round(below/len(valid)*100)

def bar_html(pct, color="#2563eb"):
    """Thin progress bar showing sector percentile."""
    w = max(2, min(100, pct))
    return (f"<div style='height:3px;background:#f1f5f9;border-radius:2px;margin-top:5px;overflow:hidden;'>"
            f"<div style='width:{w}%;height:100%;background:{color};border-radius:2px;'></div></div>")

def key_financials_band(d, cdf):
    """Render the Concept B horizontal band key financials table."""
    price = d["price"]; is_pos = True  # placeholder, updated below
    chg_pct = d.get("rev_growth",0) or 0  # we'll show day change if available

    # Pull sector arrays for percentile bars
    def sect(col): return cdf[col].dropna().tolist() if cdf is not None and col in cdf.columns and not cdf.empty else []

    ev_ebitda_sect  = sect("EV/EBITDA")
    ev_rev_sect     = sect("EV/Revenue")
    pe_sect         = sect("P/E (TTM)")
    em_sect         = sect("EBITDA Margin")
    gm_sect         = sect("Gross Margin")
    rg_sect         = sect("Rev Growth")
    roe_sect        = sect("ROE")

    # Row 1 cells: Market Cap, EV, Revenue, EBITDA, FCF
    row1 = [
        ("Market Cap",    fB(d["mkt_cap"]),    None,             "",      []),
        ("Enterprise Value", fB(d["enterprise_value"]), None,   "",      []),
        ("Revenue",       fB(d["revenue"]),     fp(d["rev_growth"]), C_GREEN if (d["rev_growth"] or 0)>0 else C_RED, rg_sect),
        ("EBITDA",        fB(d["ebitda"]),      fp(d["ebitda_margin"])+" margin", "#6b7280", em_sect),
        ("FCF",           fB(d["fcf"]) if d["fcf"] else "N/A", None, "", []),
    ]
    # Row 2 cells: Gross Margin, EBITDA Margin, EV/EBITDA, P/E TTM, WACC
    row2 = [
        ("Gross Margin",  fp(d["gross_margin"]),  "vs sector",  C_GREEN, gm_sect),
        ("EBITDA Margin", fp(d["ebitda_margin"]), "vs sector",  C_GREEN, em_sect),
        ("EV/EBITDA",     fx(d["ev_ebitda"]),     "vs sector",  C_AMBER, ev_ebitda_sect),
        ("P/E TTM",       fx(d["pe"]),            f"Fwd {fx(d['fwd_pe'])}", "#6b7280", pe_sect),
        ("WACC",          fp(d.get("_wacc",None)), f"Beta {float(d['beta']):.2f}", "#6b7280", []),
    ]

    def cell_html(label, value, sub, sub_color, sect_vals):
        pct = sector_percentile(None, sect_vals)
        # Try to get actual numeric value for percentile
        raw = None
        raw_map = {
            "Gross Margin": d["gross_margin"], "EBITDA Margin": d["ebitda_margin"],
            "EV/EBITDA": d["ev_ebitda"], "P/E TTM": d["pe"], "Rev Growth": d["rev_growth"],
            "Revenue": d["rev_growth"], "EBITDA": d["ebitda_margin"], "ROE": d["roe"],
        }
        raw = raw_map.get(label)
        if raw and sect_vals: pct = sector_percentile(raw, sect_vals)
        bar = bar_html(pct, C_BLUE) if sect_vals else ""
        sub_html = (f"<div style='font-size:10px;color:{sub_color};margin-top:2px;'>{sub}</div>" if sub else "")
        tip = tt(label)
        return (
            f"<div style='padding:12px 16px;border-right:0.5px solid #f1f5f9;'>"
            f"<div style='display:flex;align-items:center;margin-bottom:3px;'>"
            f"<span style='font-size:10px;color:#9ca3af;text-transform:uppercase;letter-spacing:0.05em;'>{label}</span>{tip}</div>"
            f"<div style='font-size:15px;font-weight:500;color:#1a1a2e;'>{value}</div>"
            f"{sub_html}{bar}</div>"
        )

    def row_html(cells):
        return (f"<div style='display:grid;grid-template-columns:repeat({len(cells)},1fr);"
                f"border-bottom:0.5px solid #f1f5f9;'>"
                + "".join(cell_html(*c) for c in cells) + "</div>")

    # Company header
    is_pos_chg = (d.get("rev_growth") or 0) >= 0
    badge_bg   = "#dcfce7" if is_pos_chg else "#fee2e2"
    badge_col  = "#16a34a" if is_pos_chg else "#dc2626"
    badge_txt  = f"▲ +{d['rev_growth']*100:.1f}% Rev YoY" if is_pos_chg else f"▼ {d['rev_growth']*100:.1f}% Rev YoY"

    header = f"""
    <div style='padding:14px 18px;display:flex;align-items:center;
                justify-content:space-between;border-bottom:0.5px solid #e2e8f0;
                background:#f8fafc;border-radius:12px 12px 0 0;'>
      <div>
        <span style='font-size:14px;font-weight:500;color:#1a1a2e;'>{d['name']}</span>
        <span style='font-size:11px;color:#9ca3af;margin-left:8px;'>{d['sector']} · {d['industry']}</span>
      </div>
      <div style='display:flex;align-items:center;gap:12px;'>
        <span style='font-size:26px;font-weight:500;color:#1a1a2e;'>${price:,.2f}</span>
        <span style='font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;
                     background:{badge_bg};color:{badge_col};'>{badge_txt}</span>
      </div>
    </div>"""

    st.markdown(
        f"<div style='border:0.5px solid #e2e8f0;border-radius:12px;overflow:hidden;margin-bottom:16px;'>"
        f"{header}{row_html(row1)}{row_html(row2)}</div>",
        unsafe_allow_html=True)

def section_hdr(text):
    st.markdown(
        f"<p style='font-size:1rem;font-weight:600;color:#1a1a2e;"
        f"border-left:3px solid #2563eb;padding-left:0.7rem;"
        f"margin:1.2rem 0 0.6rem;font-family:Inter,sans-serif;'>{text}</p>",
        unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════
for k,v in [("page","home"),("ticker",""),("val_data",None),
             ("val_loaded",False),("val_rf",0.043),("comps_data",None)]:
    if k not in st.session_state: st.session_state[k]=v

# ═══════════════════════════════════════════════════════════════
# LAYOUT
# ═══════════════════════════════════════════════════════════════
col_sb, col_main = st.columns([1,5],gap="small")

# ─── SIDEBAR ──────────────────────────────────────────────────
with col_sb:
    # Brand — no subtitle
    st.markdown("""
    <div style='padding:14px 4px 10px;border-bottom:0.5px solid #e2e8f0;margin-bottom:4px;'>
      <div style='font-size:13px;font-weight:600;letter-spacing:0.04em;color:#1a1a2e;'>Valuation</div>
    </div>""", unsafe_allow_html=True)

    # Home — styled as a real button using markdown
    home_active = st.session_state.page=="home"
    home_bg  = "#eff6ff" if home_active else "transparent"
    home_col = "#2563eb" if home_active else "#6b7280"
    home_fw  = "600" if home_active else "400"
    home_border = "0.5px solid #bfdbfe" if home_active else "0.5px solid #e2e8f0"
    st.markdown(
        f"<div style='margin:4px 0;padding:8px 10px;border-radius:8px;"
        f"background:{home_bg};border:{home_border};cursor:pointer;"
        f"font-size:12px;font-weight:{home_fw};color:{home_col};"
        f"display:flex;align-items:center;gap:6px;' "
        f"onclick=\"window.location.reload()\">Home</div>",
        unsafe_allow_html=True)
    # Streamlit button for actual click handling
    if st.button("Home", key="nav_home_btn", use_container_width=True):
        st.session_state.page="home"; st.rerun()

    # Company pill + valuation nav
    if st.session_state.val_loaded and st.session_state.val_data:
        d   = st.session_state.val_data
        tok = st.session_state.ticker
        circle = initial_circle(tok, size=24)
        st.markdown(f"""
        <div style='margin:8px 0 4px;padding:8px 8px;background:#f8fafc;
                    border:0.5px solid #e2e8f0;border-radius:8px;
                    display:flex;align-items:center;gap:8px;'>
          {circle}
          <div>
            <div style='font-size:12px;font-weight:600;color:#1a1a2e;'>{tok}</div>
            <div style='font-size:10px;color:#16a34a;font-weight:500;'>${d["price"]:,.2f}</div>
          </div>
        </div>""", unsafe_allow_html=True)

        _has_div = (d.get("dividend") or 0) > 0
        pages = [("Overview","overview"),("DCF Analysis","dcf"),
                 ("Scenarios","scenarios"),("Reverse DCF","rdcf"),
                 ("Comps","comps")]
        if _has_div:
            pages.append(("DDM","ddm"))
        pages += [("Football Field","ff"),("Sensitivity","sens")]
        for label,key in pages:
            active = st.session_state.page==key
            if active:
                st.markdown(
                    f"<div style='padding:7px 10px;border-radius:8px;background:#eff6ff;"
                    f"border:0.5px solid #bfdbfe;font-size:12px;font-weight:600;"
                    f"color:#2563eb;margin:1px 0;'>{label}</div>",
                    unsafe_allow_html=True)
                st.button(label,key=f"nav_{key}",use_container_width=True)
            else:
                if st.button(label,key=f"nav_{key}",use_container_width=True):
                    st.session_state.page=key; st.rerun()

    st.divider()
    st.markdown("<div style='font-size:10px;color:#9ca3af;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;'>Value a company</div>",unsafe_allow_html=True)
    ticker_input = st.text_input("Ticker",value=st.session_state.ticker,
                                  placeholder="AAPL, MSFT…",
                                  label_visibility="collapsed").upper().strip()
    run_pressed  = st.button("Run Valuation",key="run_val",use_container_width=True)
    if run_pressed and ticker_input:
        st.session_state.ticker=ticker_input
        st.session_state.val_loaded=False; st.session_state.val_data=None
        st.session_state.comps_data=None; st.session_state.page="overview"
        st.rerun()

# ─── FETCH DATA ───────────────────────────────────────────────
if st.session_state.ticker and not st.session_state.val_loaded:
    with col_main:
        with st.spinner(f"Loading {st.session_state.ticker}..."):
            try:
                rf = get_rf()
                info,hist,fin,cf,bs = fetch_company(st.session_state.ticker)
                d  = extract_financials(info,fin,cf,bs,st.session_state.ticker)
                if d["price"]>0:
                    wacc_v,_,_,_,_ = compute_wacc(d,rf)
                    d["_wacc"] = wacc_v
                    st.session_state.val_data=d; st.session_state.val_rf=rf
                    st.session_state.val_loaded=True
                    # Pre-fetch comps
                    base=SECTOR_COMPS.get(d["sector"],["AAPL","MSFT","GOOGL","AMZN","META"])
                    st.session_state.comps_data=fetch_comps(tuple(base[:8]),st.session_state.ticker)
                    st.rerun()
                else: st.error(f"No price data for {st.session_state.ticker}.")
            except Exception as e: st.error(f"Could not load {st.session_state.ticker}: {e}")

# ─── MAIN CONTENT ─────────────────────────────────────────────
with col_main:
    page = st.session_state.page

    # ── HOME ──────────────────────────────────────────────────
    if page=="home":
        indices = fetch_indices()
        if indices:
            rfv = st.session_state.val_rf or get_rf()
            parts=[]
            for name,v in indices.items():
                col=C_GREEN if v["pct"]>=0 else C_RED; sgn="+" if v["pct"]>=0 else ""
                parts.append(f"<span style='margin-right:18px;'>"
                              f"<span style='font-size:11px;color:#9ca3af;'>{name}</span>&nbsp;"
                              f"<span style='font-size:11px;font-weight:500;color:#1a1a2e;'>{v['price']:,.0f}</span>&nbsp;"
                              f"<span style='font-size:11px;color:{col};'>{sgn}{v['pct']:.2f}%</span></span>")
            parts.append(f"<span><span style='font-size:11px;color:#9ca3af;'>10Y UST</span>&nbsp;"
                          f"<span style='font-size:11px;font-weight:500;color:#1a1a2e;'>{rfv*100:.2f}%</span></span>")
            st.markdown(f"<div style='padding:8px 4px 12px;border-bottom:0.5px solid #e2e8f0;margin-bottom:16px;display:flex;flex-wrap:wrap;'>{''.join(parts)}</div>",unsafe_allow_html=True)

        st.markdown("<h2 style='font-size:18px;font-weight:500;color:#1a1a2e;margin-bottom:3px;'>Today's biggest movers</h2>",unsafe_allow_html=True)
        st.markdown("<p style='font-size:12px;color:#9ca3af;margin-bottom:12px;'>Top US equities by absolute % price change — live via Yahoo Finance</p>",unsafe_allow_html=True)

        with st.spinner("Fetching market movers..."):
            result=fetch_movers()
            movers,gainers,losers=(result if len(result)==3 else ([],[],[]))

        if movers:
            st.markdown("""<div style='display:grid;grid-template-columns:2fr 1fr 1fr 1fr;
                          border-bottom:0.5px solid #e2e8f0;padding:5px 8px;
                          font-size:10px;text-transform:uppercase;letter-spacing:0.06em;color:#9ca3af;'>
                          <span>Company</span><span>Trend</span>
                          <span style='text-align:right'>Price</span>
                          <span style='text-align:right'>Change</span></div>""",unsafe_allow_html=True)
            for m in movers:
                t=m["ticker"]; is_pos=m["pct"]>=0
                col=C_GREEN if is_pos else C_RED
                bg="#dcfce7" if is_pos else "#fee2e2"
                sgn="+" if is_pos else ""
                spark=mini_sparkline(fetch_sparkline(t),col,80,30)
                circle=initial_circle(t,size=30)
                st.markdown(f"""<div style='display:grid;grid-template-columns:2fr 1fr 1fr 1fr;
                             align-items:center;padding:8px 8px;border-bottom:0.5px solid #f8fafc;'
                             onmouseover="this.style.background='#f8fafc'"
                             onmouseout="this.style.background='transparent'">
                  <div style='display:flex;align-items:center;gap:10px;'>
                    {circle}
                    <div>
                      <div style='font-size:13px;font-weight:600;color:#1a1a2e;'>{t}</div>
                    </div>
                  </div>
                  <div>{spark}</div>
                  <div style='text-align:right;'>
                    <div style='font-size:12px;font-weight:500;color:#1a1a2e;'>${m["price"]:,.2f}</div>
                    <div style='font-size:10px;color:{col};'>{sgn}${abs(m["chg"]):.2f}</div>
                  </div>
                  <div style='text-align:right;'>
                    <span style='display:inline-flex;align-items:center;gap:2px;font-size:11px;
                                 font-weight:600;padding:3px 8px;border-radius:20px;
                                 background:{bg};color:{col};'>{sgn}{abs(m["pct"]):.2f}%</span>
                  </div>
                </div>""",unsafe_allow_html=True)

            st.markdown("<div style='height:14px;'></div>",unsafe_allow_html=True)
            gc,lc=st.columns(2)
            with gc:
                rows="".join(f"<div style='display:flex;justify-content:space-between;padding:4px 0;border-bottom:0.5px solid #f1f5f9;font-size:11px;'><span style='color:#2563eb;font-weight:500;'>{g['ticker']}</span><span style='color:{C_GREEN};'>+{g['pct']:.2f}%</span></div>" for g in gainers)
                st.markdown(f"<div style='background:#f8fafc;border:0.5px solid #e2e8f0;border-radius:10px;padding:12px 14px;'><div style='font-size:11px;font-weight:500;color:#6b7280;margin-bottom:8px;'>Top gainers</div>{rows}</div>",unsafe_allow_html=True)
            with lc:
                rows="".join(f"<div style='display:flex;justify-content:space-between;padding:4px 0;border-bottom:0.5px solid #f1f5f9;font-size:11px;'><span style='color:#2563eb;font-weight:500;'>{l['ticker']}</span><span style='color:{C_RED};'>{l['pct']:.2f}%</span></div>" for l in losers)
                st.markdown(f"<div style='background:#f8fafc;border:0.5px solid #e2e8f0;border-radius:10px;padding:12px 14px;'><div style='font-size:11px;font-weight:500;color:#6b7280;margin-bottom:8px;'>Top losers</div>{rows}</div>",unsafe_allow_html=True)
        else:
            st.info("Market data unavailable. Enter a ticker to begin a valuation.")

    # ── VALUATION PAGES ───────────────────────────────────────
    elif st.session_state.val_loaded and st.session_state.val_data:
        d   = st.session_state.val_data
        rf  = st.session_state.val_rf
        tok = st.session_state.ticker
        cdf = st.session_state.comps_data if st.session_state.comps_data is not None else pd.DataFrame()

        # ── Assumptions collapsible (on every page) ───────────
        with st.expander("Assumptions", expanded=False):
            ac1,ac2,ac3=st.columns(3)
            with ac1:
                st.markdown("**DCF**")
                dcf_scenario = st.selectbox("Model",["2-Stage","3-Stage","Monte Carlo","All Three"],key="dcf_type")
                g1_pct       = st.number_input("Growth Yr 1 (%)",value=10.0,step=0.5,format="%.1f",key="g1")
                tg_pct       = st.number_input("Terminal Growth (%)",value=2.5,step=0.1,format="%.1f",key="tg")
                g2_pct       = st.number_input("Fade Growth (%)",value=5.0,step=0.5,format="%.1f",key="g2") if "3-Stage" in dcf_scenario or dcf_scenario=="All Three" else 5.0
                wacc_override= st.number_input("WACC Override (0=auto)",value=0.0,step=0.1,format="%.1f",key="wacc_ov")
                proj_years   = st.slider("Projection Years",5,10,5,key="pyears")
                tax_pct      = st.slider("Tax Rate (%)",10,35,21,key="tax")
            with ac2:
                st.markdown("**Monte Carlo**")
                mc_gs=st.slider("Growth Std Dev (%)",1.0,15.0,5.0,key="mc_gs")/100
                mc_ws=st.slider("WACC Std Dev (%)",0.5,5.0,1.5,key="mc_ws")/100
                n_sims=st.select_slider("Simulations",[1000,5000,10000,25000],value=10000,key="nsims")
                st.markdown("**Margin-Based FCF**")
                use_margin=st.checkbox("Enable",value=False,key="use_margin")
                ebitda_m=st.slider("EBITDA Margin (%)",5,60,20,key="emarg")/100 if use_margin else 0.20
                fcf_conv=st.slider("FCF/EBITDA Conv (%)",30,90,60,key="fconv")/100 if use_margin else 0.60
            with ac3:
                st.markdown("**Scenarios**")
                bull_g1=st.number_input("Bull Growth (%)",value=g1_pct+5,step=0.5,format="%.1f",key="bull_g")
                bull_tg=st.number_input("Bull Terminal (%)",value=tg_pct+0.5,step=0.1,format="%.1f",key="bull_tg")
                bull_wa=st.number_input("Bull WACC adj (pp)",value=-0.5,step=0.1,format="%.1f",key="bull_wa")
                bear_g1=st.number_input("Bear Growth (%)",value=max(g1_pct-5,0),step=0.5,format="%.1f",key="bear_g")
                bear_tg=st.number_input("Bear Terminal (%)",value=max(tg_pct-0.5,0.5),step=0.1,format="%.1f",key="bear_tg")
                bear_wa=st.number_input("Bear WACC adj (pp)",value=1.0,step=0.1,format="%.1f",key="bear_wa")
                st.markdown("**Comps**")
                manual_comps=st.text_input("Custom comp tickers",placeholder="MSFT,GOOGL",key="mcomps")

        # Derived values
        tax_rate=tax_pct/100
        wacc,cost_eq,cost_dbt,e_wt,d_wt=compute_wacc(d,rf,tax_rate)
        if wacc_override>0: wacc=wacc_override/100
        d["_wacc"]=wacc
        g1=g1_pct/100; g2=g2_pct/100
        terminal_g=min(tg_pct/100,wacc-0.005)
        bull_wacc=max(wacc+bull_wa/100,terminal_g+0.01)
        bear_wacc=wacc+bear_wa/100
        bull_tg_v=min(bull_tg/100,bull_wacc-0.005)
        bear_tg_v=min(bear_tg/100,bear_wacc-0.005)
        hist_growth=estimate_growth(d["rev_hist"])
        current_price=d["price"]; debt=d["total_debt"] or 0
        cash=d["cash"] or 0; shares=d["shares"] or 1

        if d["fcf"] and d["fcf"]!=0: fcf_base=d["fcf"]; fcf_note=None
        elif d["ebitda"] and d["ebitda"]!=0: fcf_base=d["ebitda"]*0.5; fcf_note="Using 50% EBITDA as FCF proxy."
        elif d["net_income"] and d["net_income"]!=0: fcf_base=d["net_income"]; fcf_note="Using net income as FCF proxy."
        else: fcf_base=1e8; fcf_note="No FCF available — using $100M placeholder."
        if use_margin and d["revenue"]>0: fcf_base=d["revenue"]*ebitda_m*fcf_conv
        active_fcf=fcf_base

        if manual_comps:
            extra=[t.strip().upper() for t in manual_comps.split(",") if t.strip()]
            base=list(dict.fromkeys(extra+SECTOR_COMPS.get(d["sector"],[])))
            cdf=fetch_comps(tuple(base[:8]),tok)

        if fcf_note: st.warning(fcf_note)
        if d["ebitda"]>0 and debt>0:
            lev=debt/d["ebitda"]
            if lev>6: st.error(f"High leverage: ND/EBITDA = {lev:.1f}x")
            elif lev>4: st.warning(f"Elevated leverage: ND/EBITDA = {lev:.1f}x")

        # ── PAGE: OVERVIEW ────────────────────────────────────
        if page=="overview":
            # Concept B key financials band
            key_financials_band(d, cdf)

            # DDM note if no dividend
            if not (d.get("dividend") or 0) > 0:
                st.markdown(
                    "<div style='font-size:11px;color:#9ca3af;margin:-4px 0 8px;"
                    "display:flex;align-items:center;gap:5px;'>"
                    "<span style='display:inline-flex;align-items:center;justify-content:center;"
                    "width:14px;height:14px;border-radius:50%;background:#e2e8f0;"
                    "font-size:8px;color:#9ca3af;font-weight:700;'>i</span>"
                    "DDM not shown — this company does not pay a dividend.</div>",
                    unsafe_allow_html=True)

            # ── Two-column layout ─────────────────────────────
            col_left, col_right = st.columns(2, gap="medium")

            # ── LEFT: mini football field + EV bridge ─────────
            with col_left:
                # Build valuation snapshot bars
                snap_bars = []
                ps2,_,_ = dcf_2stage(active_fcf,g1,wacc,terminal_g,proj_years,debt,cash,shares)
                if ps2 and ps2>0:
                    snap_bars.append(("2-Stage DCF",    ps2*0.82, ps2*1.18, ps2,    C_BLUE))
                mc_snap = dcf_mc(active_fcf,g1,mc_gs,wacc,mc_ws,terminal_g,
                                  3000,proj_years,debt,cash,shares)
                mc_snap = mc_snap[np.isfinite(mc_snap)]
                if len(mc_snap):
                    snap_bars.append(("Monte Carlo P50",
                                      float(np.percentile(mc_snap,10)),
                                      float(np.percentile(mc_snap,90)),
                                      float(np.percentile(mc_snap,50)), C_PURPLE))
                if not cdf.empty:
                    ev2eq = lambda ev:(ev-debt+cash)/shares if shares else 0
                    ev_eb = cdf["EV/EBITDA"].dropna()
                    if len(ev_eb)>=2 and d["ebitda"]>0:
                        snap_bars.append(("EV/EBITDA Comps",
                                          ev2eq(d["ebitda"]*ev_eb.quantile(0.25)),
                                          ev2eq(d["ebitda"]*ev_eb.quantile(0.75)),
                                          ev2eq(d["ebitda"]*ev_eb.median()), C_GREEN))
                if d["analyst_target"]:
                    at = d["analyst_target"]
                    snap_bars.append(("Analyst Target", at*0.88, at*1.12, at, "#db2777"))

                snap_bars = [(n,lo,hi,mid,c) for n,lo,hi,mid,c in snap_bars
                              if lo>0 and hi>0 and hi<current_price*15]

                if snap_bars:
                    all_lo  = [lo  for _,lo,_,_,_ in snap_bars]
                    all_hi  = [hi  for _,_,hi,_,_ in snap_bars]
                    x_min   = max(0, min(all_lo)*0.80)
                    x_max   = max(all_hi)*1.20
                    x_range = x_max - x_min or 1
                    def norm(v): return (v-x_min)/x_range*100
                    curr_pct = norm(current_price)

                    rows_html = ""
                    for name,lo,hi,mid,color in snap_bars:
                        lo_p  = norm(lo); hi_p = norm(hi)
                        mid_p = norm(mid); w   = hi_p - lo_p
                        rows_html += f"""
                        <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>
                          <div style='font-size:11px;color:#6b7280;width:130px;
                                      flex-shrink:0;text-align:right;'>{name}</div>
                          <div style='flex:1;height:26px;background:#f8fafc;border-radius:20px;position:relative;'>
                            <div style='position:absolute;left:{curr_pct:.1f}%;width:1.5px;
                                        height:100%;background:#1a1a2e;opacity:.18;top:0;
                                        border-radius:1px;z-index:3;'></div>
                            <div style='position:absolute;left:{lo_p:.1f}%;width:{w:.1f}%;
                                        height:100%;border-radius:20px;background:{color};
                                        opacity:.82;display:flex;align-items:center;
                                        justify-content:space-between;padding:0 8px;z-index:2;'>
                              <span style='font-size:9px;font-weight:600;color:#fff;
                                           white-space:nowrap;'>${lo:,.0f}</span>
                              <span style='font-size:9px;font-weight:600;color:#fff;
                                           white-space:nowrap;'>${hi:,.0f}</span>
                            </div>
                            <div style='position:absolute;left:{mid_p:.1f}%;width:10px;
                                        height:10px;border-radius:50%;background:#fff;
                                        border:2px solid {color};top:8px;
                                        transform:translateX(-50%);z-index:4;
                                        box-shadow:0 1px 3px rgba(0,0,0,.15);'></div>
                          </div>
                        </div>"""

                    curr_label = f"""
                    <div style='display:flex;align-items:center;gap:10px;margin-bottom:4px;'>
                      <div style='width:130px;flex-shrink:0;'></div>
                      <div style='flex:1;position:relative;height:14px;'>
                        <div style='position:absolute;left:{curr_pct:.1f}%;
                                    transform:translateX(-50%);font-size:9px;
                                    font-weight:600;color:#6b7280;white-space:nowrap;'>
                          ▼ ${current_price:,.2f}</div>
                      </div>
                    </div>"""

                    st.markdown(
                        f"<div style='border:0.5px solid #e2e8f0;border-radius:12px;"
                        f"padding:14px 16px;margin-bottom:10px;'>"
                        f"<div style='font-size:10px;font-weight:500;text-transform:uppercase;"
                        f"letter-spacing:.07em;color:#9ca3af;margin-bottom:12px;'>"
                        f"Valuation snapshot</div>"
                        f"{curr_label}{rows_html}"
                        f"<div style='font-size:10px;color:#9ca3af;margin-top:6px;"
                        f"margin-left:140px;display:flex;align-items:center;gap:10px;'>"
                        f"<span>White dot = base case</span>"
                        f"<span>Pill ends = range</span></div></div>",
                        unsafe_allow_html=True)

                # EV bridge
                st.markdown(
                    "<div style='border:0.5px solid #e2e8f0;border-radius:12px;"
                    "padding:14px 16px;'>"
                    "<div style='font-size:10px;font-weight:500;text-transform:uppercase;"
                    "letter-spacing:.07em;color:#9ca3af;margin-bottom:12px;'>"
                    "Enterprise value to equity bridge</div>",
                    unsafe_allow_html=True)

                bridge_items = [
                    ("Enterprise Value",   d["enterprise_value"],  C_BLUE,  "absolute"),
                    ("(−) Total Debt",     -debt,                  C_RED,   "relative"),
                    ("(+) Cash",           cash,                   C_GREEN, "relative"),
                    ("(−) Minority",       -(d["minority_interest"] or 0), C_RED, "relative"),
                    ("= Equity Value",     d["mkt_cap"],           C_DARK,  "total"),
                ]
                max_val = max(abs(d["enterprise_value"] or 1), abs(d["mkt_cap"] or 1))
                bridge_rows = ""
                for label, val, color, kind in bridge_items:
                    if val == 0: continue
                    pct = abs(val)/max_val*88 if max_val else 40
                    is_total = kind=="total"
                    fw = "600" if is_total else "500"
                    bridge_rows += (
                        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:7px;'>"
                        f"<div style='font-size:11px;color:#6b7280;width:130px;flex-shrink:0;'>{label}</div>"
                        f"<div style='flex:1;height:18px;border-radius:3px;background:{color};"
                        f"opacity:.8;width:{pct:.0f}%;display:flex;align-items:center;"
                        f"padding-left:8px;'>"
                        f"<span style='font-size:10px;font-weight:{fw};color:#fff;"
                        f"white-space:nowrap;'>{fB(val)}</span></div></div>")

                st.markdown(
                    f"{bridge_rows}</div>",
                    unsafe_allow_html=True)

            # ── RIGHT: description + key flags ────────────────
            with col_right:
                # Business description
                desc = d["description"] or ""
                short_desc = desc[:600]+"…" if len(desc)>600 else desc
                st.markdown(
                    f"<div style='border:0.5px solid #e2e8f0;border-radius:12px;"
                    f"padding:14px 16px;margin-bottom:10px;'>"
                    f"<div style='font-size:10px;font-weight:500;text-transform:uppercase;"
                    f"letter-spacing:.07em;color:#9ca3af;margin-bottom:10px;'>About the company</div>"
                    f"<div style='font-size:12px;color:#6b7280;line-height:1.7;'>{short_desc}</div>"
                    f"</div>",
                    unsafe_allow_html=True)

                # Auto-generated key flags
                flags = []
                # Leverage
                lev = (debt-cash)/d["ebitda"] if d["ebitda"] and d["ebitda"]>0 else None
                if lev is not None:
                    if lev < 1.0:  flags.append(("pos", f"Low leverage — ND/EBITDA {lev:.1f}x"))
                    elif lev > 4:  flags.append(("neg", f"High leverage — ND/EBITDA {lev:.1f}x"))
                # Valuation vs sector
                if not cdf.empty and d["ev_ebitda"]:
                    med = cdf["EV/EBITDA"].dropna().median()
                    if pd.notna(med):
                        if d["ev_ebitda"] > med*1.15:
                            flags.append(("neg", f"EV/EBITDA {d['ev_ebitda']:.1f}x above sector median {med:.1f}x"))
                        elif d["ev_ebitda"] < med*0.85:
                            flags.append(("pos", f"EV/EBITDA {d['ev_ebitda']:.1f}x below sector median {med:.1f}x"))
                # Margins
                if d["ebitda_margin"] and d["ebitda_margin"]>0.30:
                    flags.append(("pos", f"Strong EBITDA margin {d['ebitda_margin']*100:.1f}%"))
                elif d["ebitda_margin"] and d["ebitda_margin"]<0.10:
                    flags.append(("neg", f"Thin EBITDA margin {d['ebitda_margin']*100:.1f}%"))
                # Revenue growth
                if d["rev_growth"] and d["rev_growth"]>0.15:
                    flags.append(("pos", f"Strong revenue growth {d['rev_growth']*100:.1f}% YoY"))
                elif d["rev_growth"] and d["rev_growth"]<0:
                    flags.append(("neg", f"Revenue declining {d['rev_growth']*100:.1f}% YoY"))
                # Historical CAGR vs current growth
                if hist_growth < -0.02 and (d["rev_growth"] or 0) > 0.05:
                    flags.append(("neg", f"Hist. rev CAGR {hist_growth*100:.1f}% — near-term growth needs to improve"))
                # Analyst upside
                if d["analyst_target"]:
                    up_an = (d["analyst_target"]-current_price)/current_price*100
                    if up_an > 15:
                        flags.append(("pos", f"Analyst consensus target ${d['analyst_target']:.0f} — {up_an:+.0f}% upside"))
                    elif up_an < -10:
                        flags.append(("neg", f"Analyst consensus target ${d['analyst_target']:.0f} — {up_an:+.0f}% downside"))

                if flags:
                    flag_rows = "".join(
                        f"<div style='display:flex;align-items:flex-start;gap:8px;"
                        f"font-size:12px;margin-bottom:7px;'>"
                        f"<span style='color:{'#16a34a' if kind=='pos' else '#dc2626'};"
                        f"font-weight:700;flex-shrink:0;font-size:13px;'>{'↑' if kind=='pos' else '↓'}</span>"
                        f"<span style='color:#6b7280;line-height:1.5;'>{msg}</span></div>"
                        for kind,msg in flags[:6])
                    st.markdown(
                        f"<div style='border:0.5px solid #e2e8f0;border-radius:12px;"
                        f"padding:14px 16px;'>"
                        f"<div style='font-size:10px;font-weight:500;text-transform:uppercase;"
                        f"letter-spacing:.07em;color:#9ca3af;margin-bottom:10px;'>Key flags</div>"
                        f"{flag_rows}</div>",
                        unsafe_allow_html=True)

        # ── PAGE: DCF ─────────────────────────────────────────
        elif page=="dcf":
            # ── Model switcher header ─────────────────────────
            st.markdown(
                f"<div style='display:flex;align-items:center;justify-content:space-between;"
                f"margin-bottom:16px;padding-bottom:12px;border-bottom:0.5px solid #e2e8f0;'>"
                f"<div>"
                f"<div style='font-size:18px;font-weight:500;color:#1a1a2e;'>DCF Analysis</div>"
                f"<div style='font-size:11px;color:#9ca3af;margin-top:2px;'>"
                f"{d['name']} · FCF {fB(active_fcf)} · WACC {fp(wacc)} · Beta {float(d['beta']):.2f}</div>"
                f"</div></div>",
                unsafe_allow_html=True)

            dcf_model = st.radio(
                "Model",
                ["2-Stage","3-Stage","Monte Carlo"],
                horizontal=True,
                key="dcf_model_radio",
                label_visibility="collapsed"
            )

            all_dcf={}; mc_results=None; mc_p10=mc_p50=mc_p90=0.0

            # ── 2-STAGE & 3-STAGE: timeline layout ────────────
            if dcf_model in ["2-Stage","3-Stage"]:
                if dcf_model=="2-Stage":
                    ps,ev,pvs=dcf_2stage(active_fcf,g1,wacc,terminal_g,proj_years,debt,cash,shares)
                    # Build raw FCF series
                    raw_fcfs=[]; f=active_fcf
                    for _ in range(proj_years):
                        f=f*(1+g1); raw_fcfs.append(f)
                    gr_rates=[g1]*proj_years
                    label="2-Stage DCF"
                else:
                    ps,ev,pvs=dcf_3stage(active_fcf,g1,g2,wacc,terminal_g,3,max(proj_years-3,1),debt,cash,shares)
                    raw_fcfs=[]; gr_rates=[]; f=active_fcf
                    for i in range(1,proj_years+1):
                        gr=g1 if i<=3 else g1+(g2-g1)*(i-3)/max(proj_years-3,1)
                        f=f*(1+gr); raw_fcfs.append(f); gr_rates.append(gr)
                    label="3-Stage DCF"

                all_dcf[label]=ps
                up=(ps-current_price)/current_price*100 if current_price else 0
                tv_pv=max((ps*shares)-sum(pvs)+debt-cash,0)

                # ── Summary strip ─────────────────────────────
                col_a,col_b,col_c,col_d=st.columns(4)
                col_a.metric("Implied price",f"${ps:,.2f}")
                col_b.metric("Current price",f"${current_price:,.2f}")
                col_c.metric("Upside / downside",f"{up:+.1f}%",
                             delta_color="normal" if up>0 else "inverse")
                tv_pct=tv_pv/(tv_pv+sum(pvs))*100 if (tv_pv+sum(pvs))>0 else 0
                col_d.metric("Terminal value %",f"{tv_pct:.0f}%")

                # ── Timeline ──────────────────────────────────
                nodes=[{"label":"Base","fcf":active_fcf,"pv":None,"gr":None,"is_tv":False,"is_base":True}]
                for i,(fcf_v,pv_v,gr_v) in enumerate(zip(raw_fcfs,pvs,gr_rates)):
                    nodes.append({"label":f"Yr {i+1}","fcf":fcf_v,"pv":pv_v,"gr":gr_v,"is_tv":False,"is_base":False})
                nodes.append({"label":"TV","fcf":tv_pv/(1+wacc)**proj_years*((wacc-terminal_g)/(1+terminal_g)) if wacc>terminal_g else 0,
                              "pv":tv_pv,"gr":terminal_g,"is_tv":True,"is_base":False})

                n=len(nodes)
                dot_row=""; label_row=""; fcf_row=""; pv_row=""; gr_row=""
                for i,node in enumerate(nodes):
                    is_last=i==n-1
                    dot_col = "#7c3aed" if node["is_tv"] else ("#9ca3af" if node["is_base"] else "#2563eb")
                    w=f"calc(100%/{n})"
                    connector="" if is_last else (
                        "<div style='position:absolute;top:5px;left:50%;right:0;"
                        "height:0.5px;background:#e2e8f0;z-index:0;'></div>")
                    dot_row+=(f"<div style='flex:1;display:flex;flex-direction:column;align-items:center;"
                               f"position:relative;z-index:1;'>"
                               f"{connector}"
                               f"<div style='width:10px;height:10px;border-radius:50%;"
                               f"background:{dot_col};border:2px solid #fff;"
                               f"z-index:2;flex-shrink:0;'></div></div>")
                    label_row+=(f"<div style='flex:1;text-align:center;font-size:10px;"
                                 f"color:#9ca3af;padding-top:2px;'>{node['label']}</div>")
                    fcf_v=node["fcf"]
                    fcf_row+=(f"<div style='flex:1;text-align:center;font-size:11px;"
                               f"font-weight:500;color:#1a1a2e;'>{fB(fcf_v) if fcf_v else '—'}</div>")
                    pv_v=node["pv"]
                    pv_row+=(f"<div style='flex:1;text-align:center;font-size:10px;"
                              f"color:#6b7280;'>{fB(pv_v) if pv_v else '—'}</div>")
                    gr_v=node["gr"]
                    gr_col="#16a34a" if gr_v and gr_v>0 else "#9ca3af"
                    gr_row+=(f"<div style='flex:1;text-align:center;font-size:10px;"
                              f"color:{gr_col};'>{fp(gr_v) if gr_v is not None else '—'}</div>")

                st.markdown(f"""
                <div style='border:0.5px solid #e2e8f0;border-radius:12px;padding:16px 12px;
                            margin:16px 0;overflow-x:auto;'>
                  <div style='font-size:10px;font-weight:500;text-transform:uppercase;
                              letter-spacing:.07em;color:#9ca3af;margin-bottom:14px;'>
                    FCF projection timeline — {label}</div>
                  <div style='display:flex;position:relative;margin-bottom:4px;'>{dot_row}</div>
                  <div style='display:flex;margin-bottom:6px;'>{label_row}</div>
                  <div style='display:flex;border-top:0.5px solid #f1f5f9;padding-top:8px;margin-bottom:3px;'>
                    <div style='font-size:10px;color:#9ca3af;width:60px;flex-shrink:0;'>FCF</div>
                    <div style='display:flex;flex:1;'>{fcf_row}</div>
                  </div>
                  <div style='display:flex;margin-bottom:3px;'>
                    <div style='font-size:10px;color:#9ca3af;width:60px;flex-shrink:0;'>PV</div>
                    <div style='display:flex;flex:1;'>{pv_row}</div>
                  </div>
                  <div style='display:flex;'>
                    <div style='font-size:10px;color:#9ca3af;width:60px;flex-shrink:0;'>Growth</div>
                    <div style='display:flex;flex:1;'>{gr_row}</div>
                  </div>
                  <div style='display:flex;align-items:center;gap:14px;margin-top:12px;
                              padding-top:10px;border-top:0.5px solid #f1f5f9;'>
                    <div style='display:flex;align-items:center;gap:5px;font-size:10px;color:#6b7280;'>
                      <div style='width:8px;height:8px;border-radius:50%;background:#2563eb;'></div>
                      Forecast FCFs
                    </div>
                    <div style='display:flex;align-items:center;gap:5px;font-size:10px;color:#6b7280;'>
                      <div style='width:8px;height:8px;border-radius:50%;background:#7c3aed;'></div>
                      Terminal value (PV)
                    </div>
                    <div style='font-size:10px;color:#6b7280;margin-left:auto;'>
                      PV = present value discounted at WACC {fp(wacc)}
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # ── Scenario strip ───────────────────────────
                ps_bear,_,_=dcf_2stage(active_fcf,bear_g1/100,bear_wacc,bear_tg_v,proj_years,debt,cash,shares)
                ps_bull,_,_=dcf_2stage(active_fcf,bull_g1/100,bull_wacc,bull_tg_v,proj_years,debt,cash,shares)
                up_bear=(ps_bear-current_price)/current_price*100
                up_bull=(ps_bull-current_price)/current_price*100

                st.markdown(f"""
                <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:0 0 16px;'>
                  <div style='border:0.5px solid #e2e8f0;border-radius:10px;padding:12px 14px;'>
                    <div style='font-size:10px;text-transform:uppercase;letter-spacing:.06em;
                                color:#9ca3af;margin-bottom:5px;'>Bear case</div>
                    <div style='font-size:17px;font-weight:500;color:#1a1a2e;'>${ps_bear:,.2f}</div>
                    <div style='font-size:11px;color:#dc2626;margin-top:2px;'>{up_bear:+.1f}%</div>
                  </div>
                  <div style='border:0.5px solid #bfdbfe;border-radius:10px;padding:12px 14px;
                              background:#eff6ff;'>
                    <div style='font-size:10px;text-transform:uppercase;letter-spacing:.06em;
                                color:#2563eb;margin-bottom:5px;'>Base case</div>
                    <div style='font-size:17px;font-weight:500;color:#2563eb;'>${ps:,.2f}</div>
                    <div style='font-size:11px;color:#16a34a;margin-top:2px;'>{up:+.1f}%</div>
                  </div>
                  <div style='border:0.5px solid #e2e8f0;border-radius:10px;padding:12px 14px;'>
                    <div style='font-size:10px;text-transform:uppercase;letter-spacing:.06em;
                                color:#9ca3af;margin-bottom:5px;'>Bull case</div>
                    <div style='font-size:17px;font-weight:500;color:#1a1a2e;'>${ps_bull:,.2f}</div>
                    <div style='font-size:11px;color:#16a34a;margin-top:2px;'>{up_bull:+.1f}%</div>
                  </div>
                </div>
                <div style='font-size:11px;color:#9ca3af;margin-bottom:16px;'>
                  Scenarios use separate growth and WACC assumptions set in Assumptions above.
                  <span style='color:#2563eb;cursor:pointer;'> See full scenario analysis →</span>
                </div>
                """, unsafe_allow_html=True)

            # ── MONTE CARLO: histogram layout ─────────────────
            elif dcf_model=="Monte Carlo":
                with st.spinner(f"Running {n_sims:,} simulations..."):
                    raw=dcf_mc(active_fcf,g1,mc_gs,wacc,mc_ws,terminal_g,n_sims,proj_years,debt,cash,shares)
                mc_results=raw[np.isfinite(raw)]
                mc_p10=float(np.percentile(mc_results,10))
                mc_p50=float(np.percentile(mc_results,50))
                mc_p90=float(np.percentile(mc_results,90))
                prob_up=(mc_results>current_price).mean()*100

                # Summary strip
                col_a,col_b,col_c,col_d=st.columns(4)
                col_a.metric("P10 — Bear",f"${mc_p10:,.2f}")
                col_b.metric("P50 — Base",f"${mc_p50:,.2f}",
                             f"{(mc_p50-current_price)/current_price*100:+.1f}%",
                             delta_color="normal" if mc_p50>current_price else "inverse")
                col_c.metric("P90 — Bull",f"${mc_p90:,.2f}")
                col_d.metric("Prob > current",f"{prob_up:.0f}%")

                # Histogram
                p1,p99=np.percentile(mc_results,1),np.percentile(mc_results,99)
                mc_cl=mc_results[(mc_results>=p1)&(mc_results<=p99)]
                fig_mc=go.Figure()
                fig_mc.add_trace(go.Histogram(
                    x=mc_cl,nbinsx=60,name="Simulations",
                    marker=dict(color=C_BLUE,opacity=0.75,line=dict(width=0))))
                fig_mc.add_vline(x=current_price,line_width=2,line_dash="dash",
                                  line_color=C_RED,
                                  annotation_text=f"Current  ${current_price:.2f}",
                                  annotation_position="top right",
                                  annotation=dict(font=dict(size=11,color=C_RED,family=FONT)))
                fig_mc.add_vline(x=mc_p50,line_width=1.5,line_dash="dot",
                                  line_color=C_GREEN,
                                  annotation_text=f"P50  ${mc_p50:.2f}",
                                  annotation_position="top left",
                                  annotation=dict(font=dict(size=11,color=C_GREEN,family=FONT)))
                fig_mc.add_vrect(x0=mc_p10,x1=mc_p90,
                                  fillcolor=C_BLUE,opacity=0.06,layer="below",line_width=0)
                apply_theme(fig_mc,f"Monte Carlo DCF — {n_sims:,} simulations",
                             height=380,legend=False)
                fig_mc.update_layout(
                    xaxis=dict(title="Implied share price ($)",tickprefix="$"),
                    yaxis=dict(title="Frequency"))
                st.plotly_chart(fig_mc,use_container_width=True)

                # Shaded region explanation
                st.markdown(
                    f"<div style='background:#f8fafc;border:0.5px solid #e2e8f0;"
                    f"border-radius:8px;padding:10px 14px;font-size:12px;color:#6b7280;'>"
                    f"Shaded band shows the P10–P90 range (${mc_p10:,.0f} – ${mc_p90:,.0f}). "
                    f"Growth sampled from N({g1*100:.1f}%, {mc_gs*100:.1f}% σ), "
                    f"WACC from N({wacc*100:.1f}%, {mc_ws*100:.1f}% σ) across {n_sims:,} paths."
                    f"</div>",
                    unsafe_allow_html=True)

                # Compact scenario strip
                ps_bear,_,_=dcf_2stage(active_fcf,bear_g1/100,bear_wacc,bear_tg_v,proj_years,debt,cash,shares)
                ps_bull,_,_=dcf_2stage(active_fcf,bull_g1/100,bull_wacc,bull_tg_v,proj_years,debt,cash,shares)
                up_bear=(ps_bear-current_price)/current_price*100
                up_bull=(ps_bull-current_price)/current_price*100
                st.markdown(f"""
                <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:14px;'>
                  <div style='border:0.5px solid #e2e8f0;border-radius:10px;padding:12px 14px;'>
                    <div style='font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#9ca3af;margin-bottom:5px;'>Bear case</div>
                    <div style='font-size:17px;font-weight:500;color:#1a1a2e;'>${ps_bear:,.2f}</div>
                    <div style='font-size:11px;color:#dc2626;margin-top:2px;'>{up_bear:+.1f}%</div>
                  </div>
                  <div style='border:0.5px solid #bfdbfe;border-radius:10px;padding:12px 14px;background:#eff6ff;'>
                    <div style='font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#2563eb;margin-bottom:5px;'>Base case</div>
                    <div style='font-size:17px;font-weight:500;color:#2563eb;'>${mc_p50:,.2f}</div>
                    <div style='font-size:11px;color:#16a34a;margin-top:2px;'>{(mc_p50-current_price)/current_price*100:+.1f}%</div>
                  </div>
                  <div style='border:0.5px solid #e2e8f0;border-radius:10px;padding:12px 14px;'>
                    <div style='font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#9ca3af;margin-bottom:5px;'>Bull case</div>
                    <div style='font-size:17px;font-weight:500;color:#1a1a2e;'>${ps_bull:,.2f}</div>
                    <div style='font-size:11px;color:#16a34a;margin-top:2px;'>{up_bull:+.1f}%</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            # ── WACC decomposition ────────────────────────────
            if st.toggle("Show WACC decomposition",value=False,key="wacc_tog"):
                wd=pd.DataFrame({
                    "Component":["Cost of equity","After-tax cost of debt","WACC"],
                    "Rate":[fp(cost_eq),fp(cost_dbt*(1-tax_rate)),fp(wacc)],
                    "Weight":[fp(e_wt),fp(d_wt),"100%"],
                    "Contribution":[fp(cost_eq*e_wt),fp(cost_dbt*(1-tax_rate)*d_wt),fp(wacc)]})
                st.dataframe(wd,hide_index=True,use_container_width=True)
                st.caption(f"CAPM: Rf {fp(rf)} + Beta {float(d['beta']):.2f} × ERP 5.5% = {fp(cost_eq)}")

        # ── PAGE: SCENARIOS ───────────────────────────────────
        elif page=="scenarios":
            # Page header
            st.markdown(
                f"<div style='margin-bottom:16px;padding-bottom:12px;border-bottom:0.5px solid #e2e8f0;'>"
                f"<div style='font-size:18px;font-weight:500;color:#1a1a2e;'>Scenario Analysis</div>"
                f"<div style='font-size:11px;color:#9ca3af;margin-top:2px;'>"
                f"{d['name']} · Current price ${current_price:,.2f} · "
                f"Adjust assumptions in the panel above</div></div>",
                unsafe_allow_html=True)

            # Compute all three scenarios
            sc_cfg = {
                "Bear": (bear_g1/100, bear_tg_v, bear_wacc),
                "Base": (g1,          terminal_g, wacc),
                "Bull": (bull_g1/100, bull_tg_v,  bull_wacc),
            }
            sc_res = {}
            for sn,(sg,stg,sw) in sc_cfg.items():
                ps,ev,_ = dcf_2stage(active_fcf,sg,sw,stg,proj_years,debt,cash,shares)
                tv_pv   = max((ps*shares) - sum(_) + debt - cash, 0) if ps else 0
                tv_pct  = tv_pv/(ev) * 100 if ev and ev>0 else 0
                sc_res[sn] = {"price":ps,"ev":ev,"g":sg,"tg":stg,"wacc":sw,"tv_pct":tv_pct}

            # ── Scenario cards ─────────────────────────────────
            sc_styles = {
                "Bear": {"hbg":"#fef2f2","hbd":"#fca5a5","lbl_col":"#dc2626","up_col":"#dc2626","arrow":"▼"},
                "Base": {"hbg":"#dbeafe","hbd":"#bfdbfe","lbl_col":"#2563eb","up_col":"#2563eb","arrow":"▲"},
                "Bull": {"hbg":"#dcfce7","hbd":"#86efac","lbl_col":"#16a34a","up_col":"#16a34a","arrow":"▲"},
            }
            cards_html = ""
            for sn, res in sc_res.items():
                st_ = sc_styles[sn]
                up  = (res["price"] - current_price) / current_price * 100 if current_price else 0
                arrow = "▼" if up < 0 else "▲"
                bd_outer = f"border:0.5px solid {st_['hbd']};"
                bd_head  = f"border-bottom:0.5px solid {st_['hbd']};"
                cards_html += f"""
                <div style='border-radius:12px;overflow:hidden;{bd_outer}'>
                  <div style='padding:14px 16px;background:{st_["hbg"]};{bd_head}'>
                    <div style='font-size:10px;font-weight:600;text-transform:uppercase;
                                letter-spacing:.07em;color:{st_["lbl_col"]};margin-bottom:6px;'>
                      {sn} case</div>
                    <div style='font-size:26px;font-weight:500;color:#1a1a2e;'>${res['price']:,.2f}</div>
                    <div style='font-size:12px;font-weight:600;margin-top:3px;color:{st_["up_col"]};'>
                      {arrow} {up:+.1f}% vs current</div>
                  </div>
                  <div style='padding:12px 16px;background:#fff;'>
                    <div style='display:flex;justify-content:space-between;padding:4px 0;
                                border-bottom:0.5px solid #f1f5f9;font-size:11px;'>
                      <span style='color:#6b7280;'>FCF growth</span>
                      <span style='color:#1a1a2e;font-weight:500;'>{fp(res["g"])}</span></div>
                    <div style='display:flex;justify-content:space-between;padding:4px 0;
                                border-bottom:0.5px solid #f1f5f9;font-size:11px;'>
                      <span style='color:#6b7280;'>Terminal growth</span>
                      <span style='color:#1a1a2e;font-weight:500;'>{fp(res["tg"])}</span></div>
                    <div style='display:flex;justify-content:space-between;padding:4px 0;
                                border-bottom:0.5px solid #f1f5f9;font-size:11px;'>
                      <span style='color:#6b7280;'>WACC</span>
                      <span style='color:#1a1a2e;font-weight:500;'>{fp(res["wacc"])}</span></div>
                    <div style='display:flex;justify-content:space-between;padding:4px 0;
                                border-bottom:0.5px solid #f1f5f9;font-size:11px;'>
                      <span style='color:#6b7280;'>Implied EV</span>
                      <span style='color:#1a1a2e;font-weight:500;'>{fB(res["ev"])}</span></div>
                    <div style='display:flex;justify-content:space-between;padding:4px 0;
                                font-size:11px;'>
                      <span style='color:#6b7280;'>TV % of EV</span>
                      <span style='color:#1a1a2e;font-weight:500;'>{res["tv_pct"]:.0f}%</span></div>
                  </div>
                </div>"""

            st.markdown(
                f"<div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;"
                f"margin-bottom:14px;'>{cards_html}</div>",
                unsafe_allow_html=True)

            # ── Impact bars ────────────────────────────────────
            bear_g  = bear_g1/100; bull_g  = bull_g1/100
            bear_tg_r = bear_tg_v; bull_tg_r = bull_tg_v
            bear_w  = bear_wacc;  bull_w  = bull_wacc

            def impact_bar(label, bear_val, base_val, bull_val, fmt_fn, invert=False):
                """Render one impact bar row. invert=True means higher = worse (e.g. WACC)."""
                total = abs(bull_val - bear_val) or 1
                bear_pct = abs(base_val - bear_val) / total * 100
                bull_pct = abs(bull_val - base_val) / total * 100
                if invert:
                    bear_col, bull_col = "#86efac", "#fca5a5"
                else:
                    bear_col, bull_col = "#fca5a5", "#86efac"
                return (
                    f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:9px;'>"
                    f"<div style='font-size:11px;color:#6b7280;width:130px;flex-shrink:0;'>{label}</div>"
                    f"<div style='flex:1;height:8px;background:#f1f5f9;border-radius:4px;"
                    f"position:relative;overflow:visible;'>"
                    f"<div style='position:absolute;left:0;width:{bear_pct:.0f}%;height:100%;"
                    f"background:{bear_col};border-radius:4px 0 0 4px;opacity:.85;'></div>"
                    f"<div style='position:absolute;left:{bear_pct:.0f}%;width:{bull_pct:.0f}%;height:100%;"
                    f"background:{bull_col};opacity:.85;border-radius:0 4px 4px 0;'></div>"
                    f"<div style='position:absolute;left:{bear_pct:.0f}%;width:2px;height:160%;"
                    f"background:#2563eb;top:-30%;border-radius:1px;'></div>"
                    f"</div>"
                    f"<div style='font-size:10px;color:#9ca3af;width:80px;text-align:right;flex-shrink:0;'>"
                    f"{fmt_fn(bear_val)} → {fmt_fn(bull_val)}</div></div>"
                )

            impact_html = (
                impact_bar("FCF growth rate", bear_g,   g1,         bull_g,   fp)
                + impact_bar("WACC",          bear_w,   wacc,       bull_w,   fp, invert=True)
                + impact_bar("Terminal growth",bear_tg_r,terminal_g,bull_tg_r,fp)
            )

            legend = (
                "<div style='display:flex;align-items:center;gap:14px;margin-top:10px;"
                "font-size:10px;color:#9ca3af;'>"
                "<span style='display:flex;align-items:center;gap:4px;'>"
                "<span style='width:10px;height:8px;background:#fca5a5;border-radius:2px;"
                "display:inline-block;'></span>Bear</span>"
                "<span style='display:flex;align-items:center;gap:4px;'>"
                "<span style='width:2px;height:12px;background:#2563eb;display:inline-block;"
                "border-radius:1px;'></span>Base</span>"
                "<span style='display:flex;align-items:center;gap:4px;'>"
                "<span style='width:10px;height:8px;background:#86efac;border-radius:2px;"
                "display:inline-block;'></span>Bull</span></div>"
            )

            st.markdown(
                f"<div style='border:0.5px solid #e2e8f0;border-radius:12px;"
                f"padding:14px 16px;margin-bottom:4px;'>"
                f"<div style='font-size:10px;font-weight:500;text-transform:uppercase;"
                f"letter-spacing:.07em;color:#9ca3af;margin-bottom:12px;'>"
                f"What drives the range — assumption impact</div>"
                f"{impact_html}{legend}</div>",
                unsafe_allow_html=True)

        # ── PAGE: REVERSE DCF ─────────────────────────────────
        elif page=="rdcf":
            # Page header
            st.markdown(
                f"<div style='margin-bottom:16px;padding-bottom:12px;border-bottom:0.5px solid #e2e8f0;'>"
                f"<div style='font-size:18px;font-weight:500;color:#1a1a2e;'>Reverse DCF</div>"
                f"<div style='font-size:11px;color:#9ca3af;margin-top:2px;'>"
                f"What growth rate is the market pricing in at ${current_price:,.2f}?</div></div>",
                unsafe_allow_html=True)

            # Base implied growth
            implied_g = reverse_dcf(current_price,shares,debt,cash,active_fcf,wacc,terminal_g,proj_years)
            gap       = implied_g - g1

            # ── Stat strip ────────────────────────────────────
            ca,cb,cc,cd = st.columns(4)
            ca.metric("Market-implied growth", fp(implied_g))
            cb.metric("Your base case",        fp(g1))
            delta_col = "normal" if gap < 0 else "inverse"
            cc.metric("Gap", f"{gap*100:+.1f}pp",
                      "Market more pessimistic" if gap<0 else "Market more optimistic",
                      delta_color=delta_col)
            cd.metric("Analyst estimate", fp(d["earnings_growth"]) if d["earnings_growth"] else "N/A")

            # ── WACC switcher ─────────────────────────────────
            st.markdown(
                "<div style='font-size:10px;color:#9ca3af;margin:14px 0 5px;"
                "text-transform:uppercase;letter-spacing:.06em;'>WACC assumption</div>",
                unsafe_allow_html=True)
            wacc_options = [wacc-0.02, wacc-0.01, wacc, wacc+0.01, wacc+0.02]
            wacc_labels  = [f"{w*100:.1f}%" for w in wacc_options]
            wacc_default = wacc_labels[2]
            sel_wacc_label = st.radio(
                "WACC", wacc_labels, index=2,
                horizontal=True, label_visibility="collapsed", key="rdcf_wacc")
            sel_wacc = wacc_options[wacc_labels.index(sel_wacc_label)]

            # Recompute implied growth at selected WACC
            implied_g_sel = reverse_dcf(current_price,shares,debt,cash,active_fcf,
                                         sel_wacc,terminal_g,proj_years)

            # ── Chart ─────────────────────────────────────────
            price_range = np.linspace(current_price*0.4, current_price*2.2, 80)
            ig_arr      = np.array([
                reverse_dcf(p,shares,debt,cash,active_fcf,sel_wacc,terminal_g,proj_years)
                for p in price_range])
            mask = np.isfinite(ig_arr) & (ig_arr > -0.5) & (ig_arr < 1.0)
            x_vals = ig_arr[mask]*100
            y_vals = price_range[mask]

            fig_r = go.Figure()

            # Fill under curve
            fig_r.add_trace(go.Scatter(
                x=x_vals, y=y_vals, mode="lines",
                line=dict(color=C_BLUE, width=2.5),
                fill="tozeroy", fillcolor="rgba(37,99,235,0.06)",
                showlegend=False))

            # Current price hline
            fig_r.add_hline(
                y=current_price, line_width=1.5, line_dash="dash", line_color=C_RED)

            # Vertical markers — implied, analyst, base case
            # Stagger annotation y positions to avoid overlap
            markers = []
            if np.isfinite(implied_g_sel):
                markers.append(("implied", implied_g_sel*100, C_BLUE,
                                 f"Implied {implied_g_sel*100:.1f}%", 0.92))
            if d["earnings_growth"] and np.isfinite(d["earnings_growth"]):
                markers.append(("analyst", d["earnings_growth"]*100, C_AMBER,
                                 f"Analyst {d['earnings_growth']*100:.1f}%", 0.78))
            markers.append(("base", g1*100, C_DARK,
                             f"Base {g1*100:.1f}%", 0.64))
            markers.append(("hist", hist_growth*100, C_GRAY,
                             f"Hist {hist_growth*100:.1f}%", 0.50))

            # Sort by x so stagger is left-to-right
            markers.sort(key=lambda m: m[1])

            # Assign staggered y positions to avoid overlap
            # Use yref="paper" for annotation y
            y_positions = [0.90, 0.76, 0.62, 0.50]
            for i,(key, x_val, color, label, _) in enumerate(markers):
                ypos = y_positions[i % len(y_positions)]
                fig_r.add_vline(
                    x=x_val,
                    line_width=1.5 if key=="implied" else 1.0,
                    line_dash="solid" if key=="implied" else "dot",
                    line_color=color,
                    annotation_text=label,
                    annotation_position="top left",
                    annotation=dict(
                        font=dict(size=10, color=color, family=FONT),
                        yref="paper",
                        y=ypos,
                        yanchor="bottom",
                        bgcolor="rgba(255,255,255,0.85)",
                        borderpad=3,
                    ))

            # Current price annotation on the right
            fig_r.add_annotation(
                x=x_vals.max() if len(x_vals) else 15,
                y=current_price,
                text=f"Current  ${current_price:.2f}",
                showarrow=False,
                xanchor="right",
                font=dict(size=10, color=C_RED, family=FONT),
                bgcolor="rgba(255,255,255,0.85)",
                borderpad=3,
            )

            apply_theme(fig_r,
                        f"Stock Price vs Market-Implied FCF Growth — WACC {sel_wacc*100:.1f}%",
                        height=420, legend=False)
            fig_r.update_layout(
                xaxis=dict(title="Market-Implied FCF Growth Rate (%)", ticksuffix="%"),
                yaxis=dict(title="Stock Price ($)", tickprefix="$"))
            st.plotly_chart(fig_r, use_container_width=True)

            # ── Insight box ───────────────────────────────────
            gap_sel = implied_g_sel - g1
            if gap_sel > 0.05:
                msg  = (f"At a {sel_wacc*100:.1f}% WACC, the market prices in "
                        f"{implied_g_sel*100:.1f}% FCF growth — {abs(gap_sel)*100:.1f}pp "
                        f"above your base case of {g1*100:.1f}%. "
                        f"The stock appears expensive relative to your assumptions.")
                mc = "#991b1b"; mbg = "#fef2f2"; mbd = "#fca5a5"
            elif gap_sel < -0.05:
                msg  = (f"At a {sel_wacc*100:.1f}% WACC, the market prices in only "
                        f"{implied_g_sel*100:.1f}% FCF growth — {abs(gap_sel)*100:.1f}pp "
                        f"below your base case of {g1*100:.1f}%. "
                        f"If your assumption is correct, the stock may be undervalued.")
                mc = "#14532d"; mbg = "#f0fdf4"; mbd = "#86efac"
            else:
                msg  = (f"At a {sel_wacc*100:.1f}% WACC, the market-implied growth of "
                        f"{implied_g_sel*100:.1f}% is broadly in line with your base case "
                        f"of {g1*100:.1f}%. The stock appears fairly valued on these assumptions.")
                mc = "#1e3a5f"; mbg = "#eff6ff"; mbd = "#bfdbfe"

            st.markdown(
                f"<div style='background:{mbg};border:0.5px solid {mbd};"
                f"border-radius:8px;padding:12px 14px;font-size:12px;"
                f"color:{mc};line-height:1.6;margin-top:4px;'>{msg}</div>",
                unsafe_allow_html=True)

            # ── WACC sensitivity table ────────────────────────
            st.markdown(
                "<div style='font-size:10px;font-weight:500;text-transform:uppercase;"
                "letter-spacing:.07em;color:#9ca3af;margin:16px 0 8px;'>"
                "Implied growth at different WACC levels</div>",
                unsafe_allow_html=True)
            tbl_rows = []
            for w in wacc_options:
                ig = reverse_dcf(current_price,shares,debt,cash,active_fcf,w,terminal_g,proj_years)
                gap_w = ig - g1
                if gap_w > 0.05:    sig = "Expensive"
                elif gap_w < -0.05: sig = "Value"
                else:               sig = "Fair"
                tbl_rows.append({
                    "WACC":            f"{w*100:.1f}%",
                    "Implied Growth":  f"{ig*100:.1f}%",
                    "vs Base Case":    f"{gap_w*100:+.1f}pp",
                    "Signal":          sig,
                })
            st.dataframe(pd.DataFrame(tbl_rows), use_container_width=True, hide_index=True)

        # ── PAGE: COMPS ───────────────────────────────────────
        elif page=="comps":
            st.markdown(
                f"<div style='margin-bottom:16px;padding-bottom:12px;border-bottom:0.5px solid #e2e8f0;'>"
                f"<div style='font-size:18px;font-weight:500;color:#1a1a2e;'>Comparable Company Analysis</div>"
                f"<div style='font-size:11px;color:#9ca3af;margin-top:2px;'>"
                f"Sector: {d['sector']} · {d['industry']}</div></div>",
                unsafe_allow_html=True)

            if cdf.empty:
                st.warning("No comp data available. Try adding custom tickers in Assumptions.")
            else:
                # ── Implied price cards ───────────────────────
                cp = comps_implied(d, cdf)
                reg_price, reg_mult, r2 = comps_regression(d, cdf)
                if reg_price:
                    cp["Regression Implied"] = reg_price

                if cp:
                    # Get median multiples for subtitle
                    med_ev_eb = cdf["EV/EBITDA"].dropna().median()
                    med_ev_rv = cdf["EV/Revenue"].dropna().median()
                    med_pe    = cdf["P/E (TTM)"].dropna().median()
                    mult_map  = {
                        "EV/EBITDA Comps":   (med_ev_eb, d["ev_ebitda"], "EV/EBITDA"),
                        "EV/Revenue Comps":  (med_ev_rv, d["ev_revenue"], "EV/Revenue"),
                        "P/E Comps":         (med_pe,    d["pe"],         "P/E TTM"),
                        "Regression Implied":(reg_mult,  d["ev_ebitda"],  "Reg. multiple"),
                    }
                    cards_html = ""
                    for method, price in cp.items():
                        up  = (price - current_price) / current_price * 100
                        col = "#16a34a" if up >= 0 else "#dc2626"
                        arr = "▲" if up >= 0 else "▼"
                        med_m, subj_m, mult_label = mult_map.get(method, (None, None, ""))
                        sub = ""
                        if med_m and pd.notna(med_m):
                            sub = (f"Sector median {med_m:.1f}x"
                                   + (f" · {tok} {subj_m:.1f}x" if subj_m and pd.notna(subj_m) else ""))
                        cards_html += (
                            f"<div style='border:0.5px solid #e2e8f0;border-radius:10px;padding:12px 14px;'>"
                            f"<div style='font-size:10px;text-transform:uppercase;letter-spacing:.06em;"
                            f"color:#9ca3af;margin-bottom:4px;'>{method}</div>"
                            f"<div style='font-size:20px;font-weight:500;color:#1a1a2e;'>${price:,.2f}</div>"
                            f"<div style='font-size:11px;font-weight:600;margin-top:3px;color:{col};'>"
                            f"{arr} {up:+.1f}%</div>"
                            f"<div style='font-size:10px;color:#9ca3af;margin-top:2px;'>{sub}</div>"
                            f"</div>")
                    n_cols = len(cp)
                    st.markdown(
                        f"<div style='display:grid;grid-template-columns:repeat({n_cols},1fr);"
                        f"gap:8px;margin-bottom:14px;'>{cards_html}</div>",
                        unsafe_allow_html=True)

                # ── Comps table ───────────────────────────────
                # Build display df
                cols_show = ["Ticker","Name","Mkt Cap ($B)","EV/EBITDA","EV/Revenue",
                             "P/E (TTM)","Fwd P/E","EBITDA Margin","Rev Growth","ROE"]
                disp = cdf[cols_show].copy()
                for col in ["EV/EBITDA","EV/Revenue","P/E (TTM)","Fwd P/E"]:
                    disp[col] = disp[col].apply(lambda x: f"{x:.1f}x" if pd.notna(x) else "N/A")
                for col in ["EBITDA Margin","Rev Growth","ROE"]:
                    disp[col] = disp[col].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A")

                # Median row
                med_row = {"Ticker":"Median","Name":"Sector median",
                           "Mkt Cap ($B)":"—",
                           "EV/EBITDA": fx(cdf["EV/EBITDA"].dropna().median()),
                           "EV/Revenue":fx(cdf["EV/Revenue"].dropna().median()),
                           "P/E (TTM)": fx(cdf["P/E (TTM)"].dropna().median()),
                           "Fwd P/E":   fx(cdf["Fwd P/E"].dropna().median()),
                           "EBITDA Margin":fp(cdf["EBITDA Margin"].dropna().median()),
                           "Rev Growth":fp(cdf["Rev Growth"].dropna().median()),
                           "ROE":       fp(cdf["ROE"].dropna().median())}

                # Subject row
                em_s = fp(d["ebitda"]/d["revenue"]) if d["revenue"] else "N/A"
                subj_row = {"Ticker":f"★ {tok}","Name":d["name"][:22],
                            "Mkt Cap ($B)":round((d["mkt_cap"] or 0)/1e9,1),
                            "EV/EBITDA":fx(d["ev_ebitda"]),"EV/Revenue":fx(d["ev_revenue"]),
                            "P/E (TTM)":fx(d["pe"]),"Fwd P/E":fx(d["fwd_pe"]),
                            "EBITDA Margin":em_s,"Rev Growth":fp(d["rev_growth"]),
                            "ROE":fp(d["roe"])}

                full_tbl = pd.concat(
                    [pd.DataFrame([subj_row]), disp, pd.DataFrame([med_row])],
                    ignore_index=True)

                # Render as HTML table so we can highlight subject and median
                thead_html = "".join(
                    f"<th style='padding:8px 10px;font-size:10px;text-transform:uppercase;"
                    f"letter-spacing:.05em;color:#9ca3af;font-weight:500;"
                    f"text-align:{'left' if i==0 or i==1 else 'right'};'>{c}</th>"
                    for i,c in enumerate(cols_show))

                def row_html_fn(row, i, n):
                    is_subj  = str(row["Ticker"]).startswith("★")
                    is_med   = row["Ticker"] == "Median"
                    is_last  = i == n - 1
                    bg = "#eff6ff" if is_subj else ("#f8fafc" if is_med else "transparent")
                    bd = "border-bottom:0.5px solid #f1f5f9;" if not is_last else ""
                    cells = ""
                    for ci,col in enumerate(cols_show):
                        val   = row[col]
                        align = "left" if ci <= 1 else "right"
                        color = "#2563eb" if is_subj and ci == 0 else ("#9ca3af" if is_med else "#1a1a2e")
                        fw    = "600" if is_subj and ci == 0 else "400"
                        # Colour positive/negative for Rev Growth and ROE
                        if col in ["Rev Growth","ROE"] and "%" in str(val):
                            try:
                                num = float(str(val).replace("%",""))
                                if num > 0:   color = "#16a34a"
                                elif num < 0: color = "#dc2626"
                            except: pass
                        cells += (f"<td style='padding:9px 10px;font-size:12px;"
                                  f"color:{color};font-weight:{fw};text-align:{align};'>{val}</td>")
                    return f"<tr style='background:{bg};{bd}'>{cells}</tr>"

                rows_html = "".join(
                    row_html_fn(full_tbl.iloc[i], i, len(full_tbl))
                    for i in range(len(full_tbl)))

                st.markdown(
                    f"<div style='border:0.5px solid #e2e8f0;border-radius:12px;"
                    f"overflow:hidden;margin-bottom:14px;overflow-x:auto;'>"
                    f"<table style='width:100%;border-collapse:collapse;'>"
                    f"<thead><tr style='background:#f8fafc;border-bottom:0.5px solid #e2e8f0;'>"
                    f"{thead_html}</tr></thead>"
                    f"<tbody>{rows_html}</tbody></table></div>",
                    unsafe_allow_html=True)

                # ── Bubble scatter below ───────────────────────
                sub_sc = cdf[["EV/EBITDA","Rev Growth","Ticker","Mkt Cap ($B)"]].dropna()
                if len(sub_sc) >= 3:
                    x_sc  = sub_sc["Rev Growth"].values
                    y_sc  = sub_sc["EV/EBITDA"].values
                    x_p5, x_p95 = np.percentile(x_sc,5),  np.percentile(x_sc,95)
                    y_p5, y_p95 = np.percentile(y_sc,5),  np.percentile(y_sc,95)
                    x_pad = (x_p95-x_p5)*0.3 or 0.05
                    y_pad = (y_p95-y_p5)*0.3 or 2
                    sl,ic,_,_,_ = stats.linregress(x_sc, y_sc)
                    x_fit = np.linspace(x_sc.min(), x_sc.max(), 60)

                    fig_sc2 = go.Figure()
                    fig_sc2.add_trace(go.Scatter(
                        x=x_fit*100, y=ic+sl*x_fit, mode="lines",
                        line=dict(color=C_GRAY, dash="dot", width=1.5),
                        name="Regression line"))
                    for _, row in sub_sc.iterrows():
                        sz = max(8, min(28, row["Mkt Cap ($B)"]**0.38*3.5)) if row["Mkt Cap ($B)"] else 10
                        fig_sc2.add_trace(go.Scatter(
                            x=[row["Rev Growth"]*100], y=[row["EV/EBITDA"]],
                            mode="markers+text", text=[row["Ticker"]],
                            textposition="top center",
                            textfont=dict(size=10, color=C_BLUE, family=FONT),
                            marker=dict(size=sz, color=C_BLUE, opacity=0.75,
                                        line=dict(color="white", width=1.5)),
                            showlegend=False))
                    if d["ev_ebitda"] and d["rev_growth"]:
                        fig_sc2.add_trace(go.Scatter(
                            x=[d["rev_growth"]*100], y=[d["ev_ebitda"]],
                            mode="markers+text", text=[f"[{tok}]"],
                            textposition="top center",
                            textfont=dict(size=11, color=C_RED, family=FONT),
                            marker=dict(size=16, color=C_RED, symbol="diamond",
                                        line=dict(color="white", width=2)),
                            showlegend=False))
                    apply_theme(fig_sc2,
                                "EV/EBITDA vs Revenue Growth — Comps + Regression",
                                height=420)
                    fig_sc2.update_layout(
                        xaxis=dict(title="Revenue Growth (%)", ticksuffix="%",
                                   range=[x_p5*100-x_pad*100, x_p95*100+x_pad*100]),
                        yaxis=dict(title="EV/EBITDA (x)", ticksuffix="x",
                                   range=[max(0, y_p5-y_pad), y_p95+y_pad]))
                    st.plotly_chart(fig_sc2, use_container_width=True)

        # ── PAGE: DDM ─────────────────────────────────────────
        elif page=="ddm":
            div_annual = d["dividend"] or 0
            st.markdown(
                f"<div style='margin-bottom:16px;padding-bottom:12px;border-bottom:0.5px solid #e2e8f0;'>"
                f"<div style='font-size:18px;font-weight:500;color:#1a1a2e;'>Dividend Discount Model</div>"
                f"<div style='font-size:11px;color:#9ca3af;margin-top:2px;'>"
                f"Annual dividend ${div_annual:.2f} · Payout ratio {fp(d['payout_ratio'])} · "
                f"Cost of equity {fp(cost_eq)}</div></div>",
                unsafe_allow_html=True)

            # ── Stat strip ────────────────────────────────────
            # Estimate historical dividend CAGR from rev_hist as proxy (use earnings growth if available)
            div_growth_hist = d["earnings_growth"] or hist_growth or 0.05
            # Clamp to reasonable range
            div_growth_hist = max(min(div_growth_hist, 0.20), 0.01)

            ca,cb,cc,cd = st.columns(4)
            ca.metric("Annual Dividend",    f"${div_annual:.2f}")
            cb.metric("Gordon Growth",       f"${ddm_gordon(div_annual,terminal_g,cost_eq):,.2f}" if ddm_gordon(div_annual,terminal_g,cost_eq) else "N/A")
            ms_val = ddm_multistage(div_annual,g1,terminal_g,cost_eq,5)
            cc.metric("Multi-Stage DDM",    f"${ms_val:,.2f}" if ms_val else "N/A")
            cd.metric("Payout Ratio",       fp(d["payout_ratio"]))

            # ── Matrix + payout side by side ──────────────────
            col_left, col_right = st.columns(2)

            with col_left:
                # DDM matrix: div_growth rows × ke cols
                # Use historical div growth as base row
                base_dg = round(div_growth_hist, 3)
                dg_range = sorted(set([
                    round(max(base_dg - 0.015, 0.005), 3),
                    round(max(base_dg - 0.005, 0.005), 3),
                    base_dg,
                    round(base_dg + 0.010, 3),
                    round(base_dg + 0.020, 3),
                ]))
                ke_range = [
                    round(cost_eq - 0.02, 3),
                    round(cost_eq - 0.01, 3),
                    round(cost_eq,        3),
                    round(cost_eq + 0.01, 3),
                ]

                # Header
                ke_labels = [f"{k*100:.1f}%" for k in ke_range]
                thead = "".join(
                    f"<th style='padding:8px 10px;font-size:10px;text-transform:uppercase;"
                    f"letter-spacing:.05em;color:#9ca3af;font-weight:500;text-align:center;"
                    f"border-right:0.5px solid #f1f5f9;'>{lbl}</th>"
                    for lbl in ke_labels)

                # Active ke column index
                active_ke_idx = 2  # cost_eq column

                rows_html = ""
                for dg in dg_range:
                    is_base_row = (dg == base_dg)
                    row_bg = "#eff6ff" if is_base_row else "transparent"
                    dg_label = f"{dg*100:.1f}%{' ✓' if is_base_row else ''}"
                    dg_color = "#2563eb" if is_base_row else "#6b7280"
                    cells = f"<td style='padding:9px 10px;font-size:11px;color:{dg_color};" \
                            f"font-weight:{'500' if is_base_row else '400'};'>{dg_label}</td>"
                    for ki,ke in enumerate(ke_range):
                        val = ddm_gordon(div_annual, dg, ke)
                        is_active_cell = is_base_row and ki == active_ke_idx
                        if val and val > 0:
                            up = (val - current_price) / current_price * 100
                            col_v = "#2563eb" if is_active_cell else ("#16a34a" if val > current_price else "#dc2626")
                            fw = "700" if is_active_cell else "500"
                            cell_txt = f"${val:,.0f}"
                        else:
                            col_v = "#9ca3af"; fw = "400"; cell_txt = "N/A"
                        cells += (f"<td style='padding:9px 10px;font-size:12px;"
                                  f"color:{col_v};font-weight:{fw};text-align:center;"
                                  f"border-right:0.5px solid #f1f5f9;'>{cell_txt}</td>")
                    rows_html += (f"<tr style='background:{row_bg};"
                                  f"border-bottom:0.5px solid #f8fafc;'>{cells}</tr>")

                st.markdown(
                    f"<div style='font-size:10px;font-weight:500;text-transform:uppercase;"
                    f"letter-spacing:.07em;color:#9ca3af;margin-bottom:8px;'>"
                    f"DDM implied price — div growth × cost of equity</div>"
                    f"<div style='font-size:10px;color:#9ca3af;margin-bottom:8px;'>"
                    f"✓ Base row uses historical earnings growth {div_growth_hist*100:.1f}% · "
                    f"Base column uses CAPM cost of equity {cost_eq*100:.1f}%</div>"
                    f"<div style='border:0.5px solid #e2e8f0;border-radius:12px;"
                    f"overflow:hidden;margin-bottom:4px;'>"
                    f"<table style='width:100%;border-collapse:collapse;'>"
                    f"<thead><tr style='background:#f8fafc;border-bottom:0.5px solid #e2e8f0;'>"
                    f"<th style='padding:8px 10px;font-size:10px;text-transform:uppercase;"
                    f"letter-spacing:.05em;color:#9ca3af;font-weight:500;text-align:left;'>"
                    f"Div growth \ ke</th>{thead}</tr></thead>"
                    f"<tbody>{rows_html}</tbody></table></div>",
                    unsafe_allow_html=True)

            with col_right:
                # Payout sustainability panel
                payout = d["payout_ratio"] or 0
                fcf_payout = (div_annual * shares / d["fcf"] * 100) if d["fcf"] and d["fcf"] > 0 else None
                ring_pct   = min(payout * 100, 100)
                # SVG ring: circumference of r=30 circle = 188.5
                circ = 188.5
                dash_fill = circ * (ring_pct / 100)
                dash_offset = circ - dash_fill

                ring_color = "#16a34a" if payout < 0.5 else ("#d97706" if payout < 0.75 else "#dc2626")
                sustain_label = "Very safe" if payout < 0.4 else ("Moderate" if payout < 0.6 else "At risk")
                sustain_color = "#16a34a" if payout < 0.4 else ("#d97706" if payout < 0.6 else "#dc2626")

                sus_rows = [
                    ("Earnings payout ratio", fp(d["payout_ratio"]), sustain_color),
                    ("FCF payout ratio",       f"{fcf_payout:.1f}%" if fcf_payout else "N/A",
                     "#16a34a" if fcf_payout and fcf_payout < 50 else "#d97706"),
                    ("Dividend / FCF",         sustain_label, sustain_color),
                    ("Hist. earnings growth",  fp(div_growth_hist), "#1a1a2e"),
                    ("Cost of equity",         fp(cost_eq), "#1a1a2e"),
                    ("Gordon implied",
                     f"${ddm_gordon(div_annual,terminal_g,cost_eq):,.2f}" if ddm_gordon(div_annual,terminal_g,cost_eq) else "N/A",
                     "#2563eb"),
                ]

                sus_html = "".join(
                    f"<div style='display:flex;justify-content:space-between;padding:6px 0;"
                    f"border-bottom:0.5px solid #f1f5f9;font-size:11px;'>"
                    f"<span style='color:#6b7280;'>{lbl}</span>"
                    f"<span style='font-weight:500;color:{col};'>{val}</span></div>"
                    for lbl, val, col in sus_rows)

                st.markdown(
                    f"<div style='font-size:10px;font-weight:500;text-transform:uppercase;"
                    f"letter-spacing:.07em;color:#9ca3af;margin-bottom:8px;'>"
                    f"Payout sustainability</div>"
                    f"<div style='border:0.5px solid #e2e8f0;border-radius:12px;padding:16px;'>"
                    f"<div style='display:flex;align-items:center;gap:20px;margin-bottom:16px;'>"
                    f"<svg width='90' height='90' viewBox='0 0 80 80'>"
                    f"<circle cx='40' cy='40' r='30' fill='none' stroke='#f1f5f9' stroke-width='10'/>"
                    f"<circle cx='40' cy='40' r='30' fill='none' stroke='{ring_color}' stroke-width='10'"
                    f" stroke-dasharray='{circ}'"
                    f" stroke-dashoffset='{dash_offset:.1f}'"
                    f" stroke-linecap='round' transform='rotate(-90 40 40)'/>"
                    f"<text x='40' y='37' text-anchor='middle' font-size='11'"
                    f" font-weight='600' fill='#1a1a2e' font-family='Inter,sans-serif'>"
                    f"{payout*100:.0f}%</text>"
                    f"<text x='40' y='50' text-anchor='middle' font-size='8'"
                    f" fill='#9ca3af' font-family='Inter,sans-serif'>payout</text>"
                    f"</svg>"
                    f"<div style='display:flex;flex-direction:column;gap:6px;'>"
                    f"<div style='display:flex;align-items:center;gap:6px;font-size:11px;color:#6b7280;'>"
                    f"<div style='width:10px;height:10px;border-radius:2px;background:{ring_color};'></div>"
                    f"Dividends paid</div>"
                    f"<div style='display:flex;align-items:center;gap:6px;font-size:11px;color:#6b7280;'>"
                    f"<div style='width:10px;height:10px;border-radius:2px;background:#f1f5f9;"
                    f"border:0.5px solid #e2e8f0;'></div>Retained earnings</div>"
                    f"<div style='font-size:11px;color:{sustain_color};font-weight:500;"
                    f"margin-top:4px;'>{sustain_label}</div>"
                    f"</div></div>"
                    f"{sus_html}</div>",
                    unsafe_allow_html=True)

        # ── PAGE: FOOTBALL FIELD ──────────────────────────────
        elif page=="ff":
            st.markdown(
                f"<div style='margin-bottom:16px;padding-bottom:12px;border-bottom:0.5px solid #e2e8f0;'>"
                f"<div style='font-size:18px;font-weight:500;color:#1a1a2e;'>Valuation Football Field</div>"
                f"<div style='font-size:11px;color:#9ca3af;margin-top:2px;'>"
                f"{d['name']} · {tok} · Pill = Bear–Bull range · White dot = base case</div></div>",
                unsafe_allow_html=True)

            # ── Build bars ────────────────────────────────────
            bars = []
            ev2eq = lambda ev: (ev-debt+cash)/shares if shares else 0

            # 2-Stage DCF
            ps2,_,_ = dcf_2stage(active_fcf,g1,wacc,terminal_g,proj_years,debt,cash,shares)
            if ps2 and ps2 > 0:
                bars.append(("2-Stage DCF", ps2*0.82, ps2*1.18, ps2, C_BLUE))

            # Monte Carlo P10–P90
            with st.spinner("Running Monte Carlo..."):
                raw = dcf_mc(active_fcf,g1,mc_gs,wacc,mc_ws,terminal_g,
                             min(n_sims,5000),proj_years,debt,cash,shares)
            mc_r = raw[np.isfinite(raw)]
            if len(mc_r):
                bars.append(("Monte Carlo P10–P90",
                             float(np.percentile(mc_r,10)),
                             float(np.percentile(mc_r,90)),
                             float(np.percentile(mc_r,50)), C_PURPLE))

            # Scenario Range
            bs_r,_,_ = dcf_2stage(active_fcf,bear_g1/100,bear_wacc,bear_tg_v,proj_years,debt,cash,shares)
            bu_r,_,_ = dcf_2stage(active_fcf,bull_g1/100,bull_wacc,bull_tg_v,proj_years,debt,cash,shares)
            ba_r,_,_ = dcf_2stage(active_fcf,g1,wacc,terminal_g,proj_years,debt,cash,shares)
            if bs_r and bu_r and bs_r>0:
                bars.append(("Scenario Range", bs_r, bu_r, ba_r, C_TEAL))

            # EV/EBITDA Comps
            if not cdf.empty:
                ev_eb = cdf["EV/EBITDA"].dropna()
                if len(ev_eb)>=2 and d["ebitda"]>0:
                    bars.append(("EV/EBITDA Comps",
                                 ev2eq(d["ebitda"]*ev_eb.quantile(0.25)),
                                 ev2eq(d["ebitda"]*ev_eb.quantile(0.75)),
                                 ev2eq(d["ebitda"]*ev_eb.median()), C_GREEN))
                pe_v = cdf["P/E (TTM)"].dropna()
                if len(pe_v)>=2 and d["net_income"]>0:
                    bars.append(("P/E Comps",
                                 (d["net_income"]*pe_v.quantile(0.25))/shares,
                                 (d["net_income"]*pe_v.quantile(0.75))/shares,
                                 (d["net_income"]*pe_v.median())/shares, C_AMBER))

            # Analyst Consensus
            if d["analyst_target"]:
                at = d["analyst_target"]
                bars.append(("Analyst Consensus", at*0.88, at*1.12, at, "#db2777"))

            # Filter out garbage values
            bars = [(n,lo,hi,mid,c) for n,lo,hi,mid,c in bars
                    if lo>0 and hi>0 and hi<current_price*15 and lo<current_price*15]

            if not bars:
                st.warning("Not enough data to build football field.")
            else:
                # ── Stat strip ────────────────────────────────
                all_mids = [mid for _,_,_,mid,_ in bars]
                consensus_mid = np.mean(all_mids)
                methods_above = sum(1 for m in all_mids if m > current_price)
                up_consensus  = (consensus_mid - current_price)/current_price*100

                ca,cb,cc,cd = st.columns(4)
                ca.metric("Consensus mid",       f"${consensus_mid:,.2f}")
                cb.metric("Current price",        f"${current_price:,.2f}")
                cc.metric("Upside to consensus",  f"{up_consensus:+.1f}%",
                          delta_color="normal" if up_consensus>0 else "inverse")
                cd.metric("Methods above current", f"{methods_above} of {len(bars)}")

                # ── Pill bar chart ────────────────────────────
                all_lo  = [lo  for _,lo,_,_,_ in bars]
                all_hi  = [hi  for _,_,hi,_,_ in bars]
                x_min   = max(0, min(all_lo)*0.80)
                x_max   = max(all_hi)*1.20
                x_range = x_max - x_min or 1

                # Normalise to 0–100 for percentage positioning
                def norm(v): return (v - x_min) / x_range * 100
                curr_pct = norm(current_price)

                # Build pill rows as HTML
                rows_html = ""
                for name,lo,hi,mid,color in bars:
                    lo_pct  = norm(lo)
                    hi_pct  = norm(hi)
                    mid_pct = norm(mid)
                    width   = hi_pct - lo_pct

                    rows_html += f"""
                    <div style='display:flex;align-items:center;gap:12px;margin-bottom:12px;'>
                      <div style='font-size:12px;color:#6b7280;width:160px;
                                  flex-shrink:0;text-align:right;'>{name}</div>
                      <div style='flex:1;height:32px;background:#f8fafc;
                                  border-radius:20px;position:relative;'>
                        <!-- Current price line -->
                        <div style='position:absolute;left:{curr_pct:.1f}%;width:1.5px;
                                    height:100%;background:#1a1a2e;opacity:.18;
                                    top:0;border-radius:1px;z-index:3;'></div>
                        <!-- Pill -->
                        <div style='position:absolute;left:{lo_pct:.1f}%;width:{width:.1f}%;
                                    height:100%;border-radius:20px;
                                    background:{color};opacity:.82;
                                    display:flex;align-items:center;
                                    justify-content:space-between;
                                    padding:0 10px;z-index:2;'>
                          <span style='font-size:10px;font-weight:600;color:#fff;
                                       white-space:nowrap;'>${lo:,.0f}</span>
                          <span style='font-size:10px;font-weight:600;color:#fff;
                                       white-space:nowrap;'>${hi:,.0f}</span>
                        </div>
                        <!-- Base dot -->
                        <div style='position:absolute;left:{mid_pct:.1f}%;
                                    width:12px;height:12px;border-radius:50%;
                                    background:#fff;border:2px solid {color};
                                    top:10px;transform:translateX(-50%);z-index:4;
                                    box-shadow:0 1px 3px rgba(0,0,0,.15);'></div>
                      </div>
                    </div>"""

                # Current price label — pinned above bars
                curr_label_html = f"""
                <div style='display:flex;align-items:center;gap:12px;margin-bottom:4px;'>
                  <div style='width:160px;flex-shrink:0;'></div>
                  <div style='flex:1;position:relative;height:16px;'>
                    <div style='position:absolute;left:{curr_pct:.1f}%;
                                transform:translateX(-50%);
                                font-size:10px;font-weight:600;
                                color:#6b7280;white-space:nowrap;'>
                      ▼ Current ${current_price:,.2f}
                    </div>
                  </div>
                </div>"""

                # Legend
                legend_html = f"""
                <div style='display:flex;align-items:center;gap:16px;
                            margin-top:10px;margin-left:172px;
                            font-size:10px;color:#9ca3af;'>
                  <span>Pill ends = Bear / Bull range</span>
                  <span style='display:flex;align-items:center;gap:4px;'>
                    <span style='width:10px;height:10px;border-radius:50%;
                                 background:#fff;border:2px solid #6b7280;
                                 display:inline-block;'></span>
                    Base case implied price
                  </span>
                  <span style='display:flex;align-items:center;gap:4px;'>
                    <span style='width:1.5px;height:12px;background:#1a1a2e;
                                 opacity:.3;display:inline-block;
                                 border-radius:1px;'></span>
                    Current price
                  </span>
                </div>"""

                st.markdown(
                    f"<div style='border:0.5px solid #e2e8f0;border-radius:12px;"
                    f"padding:18px 20px;margin-top:8px;'>"
                    f"{curr_label_html}{rows_html}{legend_html}</div>",
                    unsafe_allow_html=True)

                # Excel export
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                try:
                    xl = build_excel(d,wacc,cost_eq,rf,terminal_g,g1,
                                     active_fcf,proj_years,cdf,
                                     [(n,lo,hi,mid) for n,lo,hi,mid,_ in bars])
                    st.download_button(
                        "Download full model as Excel", xl,
                        f"{tok}_valuation.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                except Exception as ex:
                    st.caption(f"Excel export unavailable: {ex}")

        # ── PAGE: SENSITIVITY ─────────────────────────────────
        elif page=="sens":
            st.markdown(
                f"<div style='margin-bottom:16px;padding-bottom:12px;border-bottom:0.5px solid #e2e8f0;'>"
                f"<div style='font-size:18px;font-weight:500;color:#1a1a2e;'>Sensitivity Analysis</div>"
                f"<div style='font-size:11px;color:#9ca3af;margin-top:2px;'>"
                f"WACC {fp(wacc)} · Growth {fp(g1)} · Terminal {fp(terminal_g)} · "
                f"Green = above current price · Red = below</div></div>",
                unsafe_allow_html=True)

            # ── Compute base implied and breakeven ────────────
            base_implied,_,_ = dcf_2stage(active_fcf,g1,wacc,terminal_g,proj_years,debt,cash,shares)
            base_gap = (base_implied - current_price)/current_price*100 if current_price else 0

            # Breakeven growth at base WACC
            def breakeven_growth(w):
                """Binary search for FCF growth rate that gives implied = current_price."""
                lo, hi = -0.20, 0.80
                def price_at(g):
                    p,_,_ = dcf_2stage(active_fcf,g,w,terminal_g,proj_years,debt,cash,shares)
                    return p
                if price_at(hi) < current_price: return hi
                if price_at(lo) > current_price: return lo
                for _ in range(60):
                    mid = (lo+hi)/2
                    if price_at(mid) < current_price: lo = mid
                    else: hi = mid
                return round((lo+hi)/2, 4)

            be_g = breakeven_growth(wacc)

            # ── Stat strip ────────────────────────────────────
            ca,cb,cc,cd = st.columns(4)
            ca.metric("Base implied",   f"${base_implied:,.2f}",
                      f"{base_gap:+.1f}%",
                      delta_color="normal" if base_gap>0 else "inverse")
            cb.metric("Current price",  f"${current_price:,.2f}")
            cc.metric("Gap to current", f"{base_gap:+.1f}%",
                      delta_color="normal" if base_gap>0 else "inverse")
            cd.metric("Breakeven growth at base WACC", fp(be_g))

            # ── Heatmap + breakeven table ─────────────────────
            col_left, col_right = st.columns(2)

            with col_left:
                sens = sensitivity_table(active_fcf,wacc,g1,terminal_g,debt,cash,shares,proj_years)
                z    = sens.values.astype(float)
                z_finite = z[np.isfinite(z)]
                z_lo = np.percentile(z_finite,5)  if len(z_finite) else 0
                z_hi = np.percentile(z_finite,95) if len(z_finite) else 1

                fig_h = go.Figure(data=go.Heatmap(
                    z=np.clip(z,z_lo,z_hi),
                    x=[f"{v*100:.1f}%" for v in sens.columns],
                    y=[f"{v*100:.1f}%" for v in sens.index],
                    colorscale=[[0.0,"#ef4444"],[0.35,"#fca5a5"],
                                [0.5,"#fef9c3"],[0.65,"#86efac"],[1.0,"#16a34a"]],
                    zmid=current_price, zmin=z_lo, zmax=z_hi,
                    text=[[f"${v:.0f}" if np.isfinite(v) else "N/A" for v in row] for row in z],
                    texttemplate="%{text}",
                    textfont=dict(size=10,family=FONT,color="#1e293b"),
                    hovertemplate="Growth: %{y}<br>WACC: %{x}<br>Price: %{text}<extra></extra>",
                    colorbar=dict(title="Price ($)",tickprefix="$",
                                  tickfont=dict(size=10,family=FONT),
                                  thickness=12)))
                apply_theme(fig_h, "WACC × FCF Growth — Implied Price", height=420, legend=False)
                fig_h.update_layout(
                    xaxis=dict(title="WACC"),
                    yaxis=dict(title="FCF Growth Rate"),
                    margin=dict(l=80,r=20,t=50,b=60))
                st.plotly_chart(fig_h, use_container_width=True)

            with col_right:
                # Breakeven table
                wacc_range = [wacc-0.02, wacc-0.01, wacc, wacc+0.01, wacc+0.02]

                def verdict(be, base):
                    diff = be - base
                    if diff < -0.03:   return "Well achievable", "#16a34a"
                    elif diff < 0:     return "Achievable",      "#16a34a"
                    elif diff < 0.02:  return "Near base",       "#d97706"
                    elif diff < 0.05:  return "Stretch",         "#d97706"
                    elif diff < 0.10:  return "Demanding",       "#dc2626"
                    else:              return "Very demanding",   "#dc2626"

                tbl_rows = []
                for w in wacc_range:
                    be = breakeven_growth(w)
                    diff = be - g1
                    verd, vcol = verdict(be, g1)
                    is_base = (w == wacc)
                    tbl_rows.append((w, be, diff, verd, vcol, is_base))

                thead = (
                    "<tr style='background:#f8fafc;border-bottom:0.5px solid #e2e8f0;'>"
                    + "".join(
                        f"<th style='padding:8px 10px;font-size:10px;text-transform:uppercase;"
                        f"letter-spacing:.05em;color:#9ca3af;font-weight:500;"
                        f"text-align:{'left' if i==0 else 'center'};'>{h}</th>"
                        for i,h in enumerate(["WACC","Breakeven g","vs base","Verdict"]))
                    + "</tr>")

                rows_html = ""
                for w, be, diff, verd, vcol, is_base in tbl_rows:
                    bg = "#eff6ff" if is_base else "transparent"
                    w_col = "#2563eb" if is_base else "#6b7280"
                    w_fw  = "600" if is_base else "400"
                    w_lbl = f"{w*100:.1f}%{' ✓' if is_base else ''}"
                    diff_col = "#16a34a" if diff < 0 else "#dc2626"
                    rows_html += (
                        f"<tr style='background:{bg};border-bottom:0.5px solid #f8fafc;'>"
                        f"<td style='padding:9px 10px;font-size:12px;color:{w_col};"
                        f"font-weight:{w_fw};'>{w_lbl}</td>"
                        f"<td style='padding:9px 10px;font-size:12px;font-weight:500;"
                        f"color:#1a1a2e;text-align:center;'>{be*100:.1f}%</td>"
                        f"<td style='padding:9px 10px;font-size:12px;font-weight:500;"
                        f"color:{diff_col};text-align:center;'>{diff*100:+.1f}pp</td>"
                        f"<td style='padding:9px 10px;font-size:12px;font-weight:500;"
                        f"color:{vcol};text-align:center;'>{verd}</td></tr>")

                # Auto insight
                be_base = tbl_rows[2][1]  # breakeven at base WACC
                diff_base = be_base - g1
                if diff_base < 0:
                    insight = (f"At {wacc*100:.1f}% WACC, your base case growth of {g1*100:.1f}% "
                               f"<em>exceeds</em> the {be_base*100:.1f}% needed to justify the current price. "
                               f"The stock appears undervalued on these assumptions.")
                    ins_bg = "#f0fdf4"; ins_bd = "#86efac"; ins_col = "#14532d"
                else:
                    insight = (f"At {wacc*100:.1f}% WACC, justifying the current price requires "
                               f"{be_base*100:.1f}% FCF growth — {diff_base*100:.1f}pp above your "
                               f"base case of {g1*100:.1f}%. "
                               f"{'A modest stretch.' if diff_base<0.03 else 'A meaningful stretch.'}")
                    ins_bg = "#fffbeb" if diff_base < 0.05 else "#fef2f2"
                    ins_bd = "#fde68a" if diff_base < 0.05 else "#fca5a5"
                    ins_col = "#92400e" if diff_base < 0.05 else "#991b1b"

                st.markdown(
                    f"<div style='font-size:10px;font-weight:500;text-transform:uppercase;"
                    f"letter-spacing:.07em;color:#9ca3af;margin-bottom:8px;'>"
                    f"Breakeven growth rate — what FCF growth justifies current price?</div>"
                    f"<div style='border:0.5px solid #e2e8f0;border-radius:12px;"
                    f"overflow:hidden;margin-bottom:10px;'>"
                    f"<table style='width:100%;border-collapse:collapse;'>"
                    f"<thead>{thead}</thead>"
                    f"<tbody>{rows_html}</tbody></table></div>"
                    f"<div style='background:{ins_bg};border:0.5px solid {ins_bd};"
                    f"border-radius:8px;padding:10px 13px;font-size:12px;"
                    f"color:{ins_col};line-height:1.6;'>{insight}</div>",
                    unsafe_allow_html=True)

                if st.toggle("Show raw sensitivity table", value=False, key="raw_sens"):
                    raw_df = sens.copy()
                    raw_df.columns = [f"WACC {v*100:.1f}%" for v in raw_df.columns]
                    raw_df.index   = [f"Growth {v*100:.1f}%" for v in raw_df.index]
                    st.dataframe(raw_df.style.format("${:.2f}"), use_container_width=True)

    elif page!="home":
        with col_main:
            st.info("Enter a ticker in the bottom left and click Run Valuation to begin.")

    st.divider()
    st.caption(f"Data: Yahoo Finance · FRED · Educational use only — not investment advice · {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M UTC')}")
