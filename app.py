import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import plotly.graph_objects as go
from scipy import stats
import io

warnings.filterwarnings("ignore")

# ── Chart theme ───────────────────────────────────────────────────────────────
FONT    = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
C_BLUE  = "#2563eb"; C_INDIGO = "#4f46e5"; C_PURPLE = "#7c3aed"
C_GREEN = "#16a34a"; C_RED    = "#dc2626"; C_AMBER  = "#d97706"
C_TEAL  = "#0891b2"; C_GRAY   = "#6b7280"; C_DARK   = "#1e293b"
PALETTE = [C_BLUE,C_INDIGO,C_PURPLE,C_TEAL,C_GREEN,C_AMBER,C_RED,"#db2777","#0f766e"]

def base_layout(title="", height=400, margin=None, legend=True):
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

def apply_theme(fig, title="", height=400, margin=None, legend=True):
    fig.update_layout(**base_layout(title,height,margin,legend))
    return fig

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Valuation Platform",layout="wide",initial_sidebar_state="collapsed")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html,body,[class*="css"],.stApp,button,input,label,p,div,span{
  font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif !important;
}

/* Hide default Streamlit sidebar toggle & header */
[data-testid="collapsedControl"]{display:none !important;}
header[data-testid="stHeader"]{display:none !important;}
.block-container{padding:0 !important;max-width:100% !important;}
[data-testid="stSidebar"]{display:none !important;}

/* Run button */
div[data-testid="stButton"]>button{
  background:#2563eb !important;color:#fff !important;border:none !important;
  font-weight:600 !important;font-family:'Inter',sans-serif !important;
  width:100% !important;
}
div[data-testid="stButton"]>button:hover{background:#1d4ed8 !important;}
div[data-testid="stButton"]>button [data-testid="stIconMaterial"],
div[data-testid="stButton"]>button span[aria-hidden="true"]{display:none !important;}

/* Metric cards */
div[data-testid="stMetric"]{
  background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;
}

/* Number inputs, selects, sliders — compact */
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input{
  font-size:13px !important;
}

/* Scrollbar */
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:2px;}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# DOMAIN MAP — for Clearbit logos
# ═══════════════════════════════════════════════════════════════
DOMAINS = {
    "AAPL":"apple.com","MSFT":"microsoft.com","GOOGL":"google.com","GOOG":"google.com",
    "AMZN":"amazon.com","NVDA":"nvidia.com","META":"meta.com","TSLA":"tesla.com",
    "BRK-B":"berkshirehathaway.com","BRK-A":"berkshirehathaway.com",
    "JPM":"jpmorganchase.com","V":"visa.com","UNH":"unitedhealthgroup.com",
    "XOM":"exxonmobil.com","WMT":"walmart.com","MA":"mastercard.com",
    "PG":"pg.com","JNJ":"jnj.com","HD":"homedepot.com","AVGO":"broadcom.com",
    "CVX":"chevron.com","MRK":"merck.com","ABBV":"abbvie.com","COST":"costco.com",
    "PEP":"pepsico.com","KO":"coca-cola.com","BAC":"bankofamerica.com",
    "CRM":"salesforce.com","TMO":"thermofisher.com","ACN":"accenture.com",
    "MCD":"mcdonalds.com","NFLX":"netflix.com","AMD":"amd.com","INTC":"intel.com",
    "QCOM":"qualcomm.com","DIS":"disney.com","TXN":"ti.com","INTU":"intuit.com",
    "AMGN":"amgen.com","PM":"pmi.com","RTX":"rtx.com","HON":"honeywell.com",
    "SBUX":"starbucks.com","CAT":"caterpillar.com","GE":"ge.com","BA":"boeing.com",
    "MS":"morganstanley.com","GS":"goldmansachs.com","SPGI":"spglobal.com",
    "BLK":"blackrock.com","AXP":"americanexpress.com","ISRG":"intuitivesurgical.com",
    "NOW":"servicenow.com","LRCX":"lamresearch.com","DE":"johndeere.com",
    "PLD":"prologis.com","ADI":"analog.com","SYK":"stryker.com","GILD":"gilead.com",
    "REGN":"regeneron.com","VRTX":"vrtx.com","ZTS":"zoetis.com","BSX":"bostonscientific.com",
    "CI":"cigna.com","CB":"chubb.com","MMC":"marshmclennan.com","AON":"aon.com",
    "PNC":"pnc.com","USB":"usbank.com","TFC":"truist.com","COF":"capitalone.com",
    "MO":"altria.com","PM":"pmi.com","BTI":"bat.com",
    "SO":"southerncompany.com","NEE":"nexteraenergy.com","DUK":"duke-energy.com",
    "ARM":"arm.com","SMCI":"supermicro.com","MRNA":"modernatx.com",
    "PYPL":"paypal.com","SNAP":"snap.com","UBER":"uber.com","LYFT":"lyft.com",
    "ABNB":"airbnb.com","SHOP":"shopify.com","SQ":"squareup.com","PLTR":"palantir.com",
    "SNOW":"snowflake.com","DDOG":"datadoghq.com","NET":"cloudflare.com",
    "ZM":"zoom.us","DOCU":"docusign.com","TWLO":"twilio.com","OKTA":"okta.com",
    "CRWD":"crowdstrike.com","S":"sentinelone.com","PANW":"paloaltonetworks.com",
    "FTNT":"fortinet.com","ORCL":"oracle.com","SAP":"sap.com","IBM":"ibm.com",
    "DELL":"dell.com","HPQ":"hp.com","CSCO":"cisco.com","NOC":"northropgrumman.com",
    "LMT":"lockheedmartin.com","GD":"gd.com","PFE":"pfizer.com","LLY":"lilly.com",
    "NVO":"novonordisk.com","ROCHE":"roche.com","AZN":"astrazeneca.com",
    "UNP":"up.com","CSX":"csx.com","NSC":"nscorp.com","FDX":"fedex.com","UPS":"ups.com",
    "F":"ford.com","GM":"gm.com","RIVN":"rivian.com","LCID":"lucidmotors.com",
}

def clearbit_url(ticker):
    d = DOMAINS.get(ticker.upper())
    return f"https://logo.clearbit.com/{d}" if d else None

def logo_html(ticker, size=28, radius="50%", bg="#e2e8f0"):
    url = clearbit_url(ticker)
    initials = ticker[:2].upper()
    if url:
        return (
            f"<span style='display:inline-flex;align-items:center;justify-content:center;"
            f"width:{size}px;height:{size}px;border-radius:{radius};"
            f"overflow:hidden;background:#f1f5f9;border:0.5px solid #e2e8f0;flex-shrink:0;'>"
            f"<img src='{url}' width='{int(size*0.75)}' height='{int(size*0.75)}' "
            f"style='object-fit:contain;border-radius:2px;' "
            f"onerror=\"this.parentElement.innerHTML='<span style=&quot;font-size:{int(size*0.3)}px;"
            f"font-weight:700;color:#fff;background:{bg};width:100%;height:100%;display:flex;"
            f"align-items:center;justify-content:center;border-radius:{radius};&quot;>{initials}</span>'\">"
            f"</span>"
        )
    colors = ["#2563eb","#7c3aed","#0891b2","#059669","#d97706","#dc2626"]
    c = colors[sum(ord(x) for x in ticker) % len(colors)]
    return (
        f"<span style='display:inline-flex;align-items:center;justify-content:center;"
        f"width:{size}px;height:{size}px;border-radius:{radius};background:{c};"
        f"font-size:{int(size*0.3)}px;font-weight:700;color:#fff;flex-shrink:0;'>{initials}</span>"
    )

# ═══════════════════════════════════════════════════════════════
# DATA FUNCTIONS
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def get_rf():
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
        df  = pd.read_csv(url,parse_dates=["DATE"])
        df  = df[df["DGS10"]!="."]
        return float(df["DGS10"].iloc[-1])/100
    except:
        return 0.043

@st.cache_data(ttl=900)
def fetch_company(ticker):
    t = yf.Ticker(ticker)
    return t.info, t.history(period="5y"), t.financials, t.cashflow, t.balance_sheet

@st.cache_data(ttl=600)
def fetch_movers():
    """Fetch top gainers and losers from S&P 500 universe using yfinance."""
    universe = [
        "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","AVGO","JPM","V",
        "UNH","XOM","WMT","MA","PG","JNJ","HD","COST","PEP","KO",
        "BAC","MRK","ABBV","CVX","CRM","NFLX","AMD","INTC","DIS","BA",
        "GE","MS","GS","ORCL","IBM","CSCO","PFE","LLY","QCOM","TXN",
        "AMGN","RTX","HON","CAT","NOW","PLTR","SNOW","CRWD","PANW","NET",
        "UBER","SHOP","PYPL","SNAP","ABNB","ARM","SMCI","MRNA","INTC","F",
    ]
    rows = []
    try:
        tickers_str = " ".join(universe[:40])
        data = yf.download(tickers_str, period="2d", interval="1d",
                           group_by="ticker", auto_adjust=True, progress=False)
        for t in universe[:40]:
            try:
                if t in data.columns.get_level_values(0):
                    prices = data[t]["Close"].dropna()
                    if len(prices) >= 2:
                        prev  = float(prices.iloc[-2])
                        curr  = float(prices.iloc[-1])
                        chg   = curr - prev
                        pct   = chg / prev * 100 if prev else 0
                        rows.append({"ticker":t,"price":curr,"chg":chg,"pct":pct})
            except:
                pass
    except:
        pass
    if not rows:
        return [], []
    df = pd.DataFrame(rows).dropna()
    df = df[df["pct"].abs() > 0.01]
    df = df.sort_values("pct",ascending=False)
    gainers = df[df["pct"]>0].head(4).to_dict("records")
    losers  = df[df["pct"]<0].tail(4).to_dict("records")
    top7    = pd.concat([df.head(4), df.tail(3)]).drop_duplicates("ticker")
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
                prev = float(data["Close"].iloc[-2])
                curr = float(data["Close"].iloc[-1])
                result[name] = {"price":curr,"chg":curr-prev,"pct":(curr-prev)/prev*100}
    except:
        pass
    return result

@st.cache_data(ttl=900)
def fetch_sparkline(ticker):
    try:
        data = yf.download(ticker,period="5d",interval="1h",auto_adjust=True,progress=False)
        return data["Close"].dropna().tolist()
    except:
        return []

def extract_financials(info, fin, cf, bs, ticker_sym):
    d = {}
    for k,ik in [("revenue","totalRevenue"),("ebitda","ebitda"),
                 ("net_income","netIncomeToCommon"),("gross_profit","grossProfits"),
                 ("total_debt","totalDebt"),("cash","totalCash"),
                 ("shares","sharesOutstanding"),("mkt_cap","marketCap"),
                 ("dividend","dividendRate"),("payout_ratio","payoutRatio"),
                 ("roe","returnOnEquity"),("roic","returnOnAssets"),
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
    d["fcf_margin"] = info.get("freeCashflowYield") or 0
    d["shares"]     = d["shares"] or 1
    if not d["enterprise_value"]: d["enterprise_value"] = d["mkt_cap"]

    rev_hist = []
    if fin is not None and not fin.empty:
        for idx in fin.index:
            if "revenue" in idx.lower():
                rev_hist = list(fin.loc[idx].dropna().values[::-1]); break
    d["rev_hist"] = rev_hist

    fcf = 0
    if cf is not None and not cf.empty:
        for idx in cf.index:
            if "free cash flow" in idx.lower():
                vals = cf.loc[idx].dropna()
                if len(vals): fcf = float(vals.iloc[0])
                break
        if fcf == 0:
            ocf = capex = 0
            for idx in cf.index:
                if "operating" in idx.lower() and "cash" in idx.lower():
                    vals = cf.loc[idx].dropna()
                    if len(vals): ocf = float(vals.iloc[0])
                if "capital" in idx.lower() or "capex" in idx.lower():
                    vals = cf.loc[idx].dropna()
                    if len(vals): capex = float(vals.iloc[0])
            fcf = ocf + capex
    d["fcf"] = fcf
    return d

# ═══════════════════════════════════════════════════════════════
# VALUATION ENGINES
# ═══════════════════════════════════════════════════════════════
def compute_wacc(d, rf, tax=0.21):
    beta     = max(float(d["beta"] or 1.0), 0.3)
    cost_eq  = rf + beta*0.055
    dbt      = d["total_debt"] or 0
    mc       = d["mkt_cap"] or 1
    cost_dbt = max(rf+0.015, 0.04)
    if d["interest_expense"] and dbt>0:
        cost_dbt = max(min(abs(d["interest_expense"])/dbt,0.15),0.03)
    tc = mc+dbt
    ew = mc/tc if tc>0 else 1.0; dw = dbt/tc if tc>0 else 0.0
    return round(ew*cost_eq+dw*cost_dbt*(1-tax),4),round(cost_eq,4),round(cost_dbt,4),round(ew,4),round(dw,4)

def estimate_growth(rev_hist):
    if len(rev_hist)>=2:
        rates=[(rev_hist[i]-rev_hist[i-1])/abs(rev_hist[i-1])
               for i in range(1,len(rev_hist)) if rev_hist[i-1]]
        if rates: return float(np.median(rates))
    return 0.08

def dcf_2stage(fcf,g1,wacc,tg,years=5,debt=0,cash=0,shares=1):
    if not shares or not fcf: return 0,0,[]
    f=fcf; pvs=[]
    for i in range(1,years+1):
        f=f*(1+g1); pvs.append(f/(1+wacc)**i)
    tv = pvs[-1]*(1+wacc)**years*(1+tg)/(wacc-tg) if wacc>tg else 0
    pv_tv=tv/(1+wacc)**years
    ev=sum(pvs)+pv_tv
    return (ev-debt+cash)/shares,ev,pvs

def dcf_3stage(fcf,g1,g2,wacc,tg,y1=3,y2=4,debt=0,cash=0,shares=1):
    if not shares or not fcf: return 0,0,[]
    f=fcf; pvs=[]; fcfs=[]
    for i in range(1,y1+1):
        f=f*(1+g1); pvs.append(f/(1+wacc)**i); fcfs.append(f)
    for i,gr in enumerate(np.linspace(g1,g2,y2),start=y1+1):
        f=f*(1+gr); pvs.append(f/(1+wacc)**i); fcfs.append(f)
    tv=fcfs[-1]*(1+tg)/(wacc-tg) if wacc>tg else 0
    pv_tv=tv/(1+wacc)**(y1+y2); ev=sum(pvs)+pv_tv
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
    target=(price*shares+debt-cash)
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

SECTOR_COMPS = {
    "Technology":["AAPL","MSFT","GOOGL","META","AMZN","ORCL","CRM","NVDA"],
    "Consumer Cyclical":["AMZN","TSLA","HD","NKE","MCD","BKNG","TGT"],
    "Healthcare":["JNJ","UNH","PFE","ABBV","MRK","TMO","ABT","LLY"],
    "Financial Services":["JPM","BAC","WFC","GS","MS","BLK","SCHW"],
    "Communication Services":["GOOGL","META","NFLX","DIS","T","VZ","CMCSA"],
    "Industrials":["CAT","BA","HON","UPS","GE","RTX","LMT"],
    "Consumer Defensive":["PG","KO","PEP","WMT","COST","CL"],
    "Energy":["XOM","CVX","COP","SLB","EOG"],
    "Utilities":["NEE","DUK","SO","D","EXC"],
    "Real Estate":["AMT","PLD","CCI","EQIX","SPG"],
    "Basic Materials":["LIN","APD","ECL","NEM","FCX"],
}

@st.cache_data(ttl=3600)
def fetch_comps(tickers, exclude):
    rows=[]
    for t in tickers:
        if t==exclude.upper(): continue
        try:
            info=yf.Ticker(t).info
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

def comps_implied(d, cdf):
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

def comps_regression(d, cdf):
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

def build_excel(d,wacc,cost_eq,rf,tg,g1,fcf_base,years,all_dcf,cdf,bars):
    buf=io.BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as writer:
        pd.DataFrame({"Metric":list(d.keys()),"Value":list(d.values())}).to_excel(writer,sheet_name="Overview",index=False)
        if bars:
            pd.DataFrame([{"Method":n,"Bear":lo,"Base":mid,"Bull":hi} for n,lo,hi,mid in bars]).to_excel(writer,sheet_name="Valuation Summary",index=False)
        if cdf is not None and not cdf.empty:
            cdf.to_excel(writer,sheet_name="Comparable Companies",index=False)
        sensitivity_table(fcf_base,wacc,g1,tg,d["total_debt"],d["cash"],d["shares"],years).to_excel(writer,sheet_name="DCF Sensitivity")
    buf.seek(0); return buf.getvalue()

# ── Formatting ────────────────────────────────────────────────
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

GLOSSARY={
    "Stock Price":"The current market price per share.",
    "Market Cap":"Share price × shares outstanding — total equity market value.",
    "Enterprise Value":"Market Cap + debt − cash. The full acquisition cost of the business.",
    "Revenue":"Total sales before any costs. Also called the top line.",
    "EBITDA":"Earnings Before Interest, Tax, Depreciation & Amortisation. A cash-flow proxy.",
    "FCF":"Free Cash Flow — operating cash flow minus capex.",
    "Net Income":"Bottom-line profit after all expenses and taxes.",
    "Beta":"Sensitivity to market moves. Beta 1.5 = stock moves 1.5× the market.",
    "P/E (TTM)":"Price ÷ trailing 12-month earnings per share.",
    "Fwd P/E":"Price ÷ next year's estimated earnings per share.",
    "EV/EBITDA":"Capital-structure-neutral valuation multiple. Lower = cheaper.",
    "EV/Revenue":"EV ÷ Revenue. Used for high-growth or unprofitable companies.",
    "ROE":"Return on Equity — net income ÷ shareholders equity.",
    "WACC":"Weighted Average Cost of Capital — the DCF discount rate.",
    "Gross Margin":"Gross profit ÷ revenue. Measures pricing power.",
    "EBITDA Margin":"EBITDA ÷ revenue. Measures operating efficiency.",
    "Rev Growth":"Year-over-year revenue growth rate.",
    "Hist Rev CAGR":"Annualised historical revenue growth from financial statements.",
    "Net Debt":"Total debt minus cash. Positive = net debt; negative = net cash.",
    "ND/EBITDA":"Leverage ratio. Above 4× is considered high.",
    "Risk-Free Rate":"10-year US Treasury yield — the baseline for WACC.",
}

def tt_html(label):
    tip=GLOSSARY.get(label,"")
    if not tip: return ""
    safe=tip.replace("'","&#39;").replace('"',"&quot;")
    return (f'<span style="position:relative;display:inline-flex;align-items:center;"'
            f' onmouseenter="this.querySelector(\'span.tb\').style.display=\'block\'"'
            f' onmouseleave="this.querySelector(\'span.tb\').style.display=\'none\'">'
            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:13px;height:13px;border-radius:50%;background:#e2e8f0;color:#6b7280;'
            f'font-size:8px;font-weight:700;cursor:default;flex-shrink:0;">?</span>'
            f'<span class="tb" style="display:none;position:absolute;bottom:calc(100% + 6px);'
            f'left:50%;transform:translateX(-50%);background:#1e293b;color:#f1f5f9;'
            f'font-size:11px;line-height:1.5;padding:7px 10px;border-radius:6px;width:200px;'
            f'white-space:normal;z-index:9999;box-shadow:0 4px 16px rgba(0,0,0,.4);'
            f'font-family:Inter,sans-serif;font-weight:400;text-transform:none;letter-spacing:0;">'
            f'{safe}</span></span>')

def kpi_card(label, value):
    tip=tt_html(label)
    return (f"<div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;"
            f"padding:12px 14px;min-width:0;'>"
            f"<div style='display:flex;align-items:center;gap:4px;margin-bottom:5px;'>"
            f"<span style='font-size:10px;color:#6b7280;text-transform:uppercase;"
            f"letter-spacing:0.05em;font-weight:500;'>{label}</span>{tip}</div>"
            f"<div style='font-size:17px;font-weight:700;color:#1a1a2e;"
            f"word-break:break-word;line-height:1.3;'>{value}</div></div>")

def kpi_row(items):
    cards="".join(kpi_card(l,v) for l,v in items)
    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat({len(items)},1fr);'
        f'gap:8px;margin-bottom:10px;">{cards}</div>',
        unsafe_allow_html=True)

def section_hdr(text):
    st.markdown(
        f"<p style='font-size:1rem;font-weight:600;color:#1a1a2e;"
        f"border-left:3px solid #2563eb;padding-left:0.7rem;"
        f"margin:1.2rem 0 0.6rem;font-family:Inter,sans-serif;'>{text}</p>",
        unsafe_allow_html=True)

def render_tags(*tags):
    html="".join(f"<span style='display:inline-block;background:#eff6ff;color:#1d4ed8;"
                 f"border-radius:4px;padding:2px 8px;font-size:0.75rem;font-weight:500;"
                 f"margin:2px;font-family:Inter,sans-serif;'>{t}</span>" for t in tags if t)
    st.markdown(html,unsafe_allow_html=True)

def mini_sparkline(prices, color="#2563eb", width=80, height=30):
    if not prices or len(prices)<2: return ""
    mn,mx=min(prices),max(prices)
    rng=mx-mn or 1
    pts=[(int(i/(len(prices)-1)*(width-2)+1), int(height-2-(p-mn)/rng*(height-4)+1))
         for i,p in enumerate(prices)]
    poly=" ".join(f"{x},{y}" for x,y in pts)
    fill_pts=poly+f" {width-1},{height-1} 1,{height-1}"
    uid=f"sp{abs(hash(str(prices[:3])))%99999}"
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<defs><linearGradient id="{uid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity="0.2"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
            f'</linearGradient></defs>'
            f'<polygon points="{fill_pts}" fill="url(#{uid})"/>'
            f'<polyline points="{poly}" fill="none" stroke="{color}" '
            f'stroke-width="1.8" stroke-linejoin="round"/></svg>')

# ═══════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════
if "page" not in st.session_state:       st.session_state.page="home"
if "ticker" not in st.session_state:     st.session_state.ticker=""
if "val_data" not in st.session_state:   st.session_state.val_data=None
if "val_loaded" not in st.session_state: st.session_state.val_loaded=False

# ═══════════════════════════════════════════════════════════════
# LAYOUT — custom sidebar + main
# ═══════════════════════════════════════════════════════════════
col_sb, col_main = st.columns([1, 5], gap="small")

with col_sb:
    # Brand
    st.markdown("""
    <div style='padding:14px 4px 10px;border-bottom:0.5px solid #e2e8f0;margin-bottom:6px;'>
      <div style='font-size:12px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#1a1a2e;'>Valuation</div>
      <div style='font-size:10px;color:#9ca3af;margin-top:2px;'>Research platform</div>
    </div>
    """, unsafe_allow_html=True)

    # Nav — Home always visible
    def nav_btn(label, page_key, icon=""):
        is_active = st.session_state.page == page_key
        bg = "#eff6ff" if is_active else "transparent"
        color = "#2563eb" if is_active else "#6b7280"
        border = "2px solid #2563eb" if is_active else "2px solid transparent"
        if st.button(f"{icon}  {label}", key=f"nav_{page_key}",
                     use_container_width=True):
            st.session_state.page = page_key
            st.rerun()

    # Override button style for nav — only in the sidebar column
    st.markdown("""
    <style>
    div[data-testid="stButton"]>button{
      background:transparent !important;color:#6b7280 !important;
      border:none !important;font-weight:400 !important;
      text-align:left !important;justify-content:flex-start !important;
      padding:6px 8px !important;border-radius:6px !important;
      font-size:13px !important;
    }
    div[data-testid="stButton"]>button:hover{
      background:#f1f5f9 !important;color:#1a1a2e !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.button("  Home", key="nav_home", use_container_width=True):
        st.session_state.page = "home"; st.rerun()

    # Company pill — visible when valuation loaded
    if st.session_state.val_loaded and st.session_state.val_data:
        d   = st.session_state.val_data
        tok = st.session_state.ticker
        url = clearbit_url(tok)
        img_tag = f'<img src="{url}" width="20" height="20" style="object-fit:contain;border-radius:2px;" onerror="this.style.display=\'none\'">' if url else ""
        st.markdown(f"""
        <div style='margin:6px 0;padding:8px 6px;background:#f8fafc;
                    border:0.5px solid #e2e8f0;border-radius:8px;
                    display:flex;align-items:center;gap:8px;'>
          <span style='display:inline-flex;align-items:center;justify-content:center;
                       width:26px;height:26px;border-radius:6px;overflow:hidden;
                       background:#f1f5f9;border:0.5px solid #e2e8f0;flex-shrink:0;'>{img_tag}</span>
          <div>
            <div style='font-size:12px;font-weight:600;color:#1a1a2e;'>{tok}</div>
            <div style='font-size:10px;color:#16a34a;'>${d["price"]:,.2f}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Valuation nav items — only shown after loading
        pages = [
            ("DCF Analysis","dcf"),("Scenarios","scenarios"),
            ("Reverse DCF","rdcf"),("Comps","comps"),
            ("DDM","ddm"),("Football Field","ff"),("Sensitivity","sens"),
        ]
        for label, key in pages:
            active = st.session_state.page == key
            btn_style = "background:#eff6ff !important;color:#2563eb !important;font-weight:500 !important;" if active else ""
            st.markdown(f"<style>[data-testid='stButton']:has(button[kind='secondary']{{key:'{key}'}}){{border-left:2px solid #2563eb;}}</style>",unsafe_allow_html=True)
            if st.button(f"  {label}", key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key; st.rerun()

    st.markdown("<div style='flex:1'></div>",unsafe_allow_html=True)
    st.divider()

    # Ticker input always at bottom
    st.markdown("<div style='font-size:10px;color:#9ca3af;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;'>Value a company</div>",unsafe_allow_html=True)
    ticker_input = st.text_input("Ticker", value=st.session_state.ticker,
                                  placeholder="AAPL, MSFT…",
                                  label_visibility="collapsed").upper().strip()
    run_pressed = st.button("Run Valuation", key="run_val", use_container_width=True)

    if run_pressed and ticker_input:
        st.session_state.ticker      = ticker_input
        st.session_state.val_loaded  = False
        st.session_state.val_data    = None
        st.session_state.page        = "dcf"
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# FETCH VALUATION DATA
# ═══════════════════════════════════════════════════════════════
if st.session_state.ticker and not st.session_state.val_loaded:
    with col_main:
        with st.spinner(f"Loading {st.session_state.ticker}..."):
            try:
                rf = get_rf()
                info,hist,fin,cf,bs = fetch_company(st.session_state.ticker)
                d = extract_financials(info,fin,cf,bs,st.session_state.ticker)
                if d["price"] and d["price"]>0:
                    st.session_state.val_data   = d
                    st.session_state.val_rf      = rf
                    st.session_state.val_loaded  = True
                    st.rerun()
                else:
                    st.error(f"No price data for {st.session_state.ticker}.")
            except Exception as e:
                st.error(f"Could not load {st.session_state.ticker}: {e}")

# ═══════════════════════════════════════════════════════════════
# MAIN CONTENT
# ═══════════════════════════════════════════════════════════════
with col_main:
    page = st.session_state.page

    # ──────────────────────────────────────────────────────────
    # HOME
    # ──────────────────────────────────────────────────────────
    if page == "home":
        # Index bar
        indices = fetch_indices()
        if indices:
            idx_parts=[]
            for name,v in indices.items():
                col=C_GREEN if v["pct"]>=0 else C_RED
                sgn="+" if v["pct"]>=0 else ""
                idx_parts.append(
                    f"<span style='margin-right:20px;'>"
                    f"<span style='font-size:11px;color:#6b7280;'>{name}</span>&nbsp;"
                    f"<span style='font-size:11px;font-weight:500;color:#1a1a2e;'>{v['price']:,.0f}</span>&nbsp;"
                    f"<span style='font-size:11px;color:{col};'>{sgn}{v['pct']:.2f}%</span>"
                    f"</span>")
            rfr = get_rf()
            idx_parts.append(
                f"<span><span style='font-size:11px;color:#6b7280;'>10Y UST</span>&nbsp;"
                f"<span style='font-size:11px;font-weight:500;color:#1a1a2e;'>{rfr*100:.2f}%</span></span>")
            st.markdown(
                f"<div style='padding:8px 4px 12px;border-bottom:0.5px solid #e2e8f0;"
                f"margin-bottom:16px;display:flex;flex-wrap:wrap;align-items:center;'>"
                f"{''.join(idx_parts)}</div>",
                unsafe_allow_html=True)

        st.markdown("<h2 style='font-size:18px;font-weight:500;color:#1a1a2e;margin-bottom:3px;'>Today's biggest movers</h2>",unsafe_allow_html=True)
        st.markdown("<p style='font-size:12px;color:#6b7280;margin-bottom:12px;'>Top US equities by absolute % price change — live via Yahoo Finance</p>",unsafe_allow_html=True)

        with st.spinner("Fetching market movers..."):
            result = fetch_movers()
            if len(result)==3:
                movers,gainers,losers = result
            else:
                movers,gainers,losers=[],[],[]

        if movers:
            # Table header
            st.markdown("""
            <div style='display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:0;
                        border-bottom:0.5px solid #e2e8f0;padding:5px 8px;
                        font-size:10px;text-transform:uppercase;letter-spacing:0.06em;color:#9ca3af;'>
              <span>Company</span><span>Trend</span>
              <span style='text-align:right'>Price</span>
              <span style='text-align:right'>Change</span>
            </div>
            """,unsafe_allow_html=True)

            for m in movers:
                t = m["ticker"]
                is_pos = m["pct"] >= 0
                col_c  = C_GREEN if is_pos else C_RED
                bg_pill= "#dcfce7" if is_pos else "#fee2e2"
                sgn    = "+" if is_pos else ""
                spark_data = fetch_sparkline(t)
                spark  = mini_sparkline(spark_data, col_c, 80, 30)
                logo   = logo_html(t, size=30, radius="50%")

                row_html = f"""
                <div style='display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:0;
                             align-items:center;padding:8px 8px;
                             border-bottom:0.5px solid #f1f5f9;cursor:pointer;'
                     onmouseover="this.style.background='#f8fafc'"
                     onmouseout="this.style.background='transparent'">
                  <div style='display:flex;align-items:center;gap:10px;'>
                    {logo}
                    <div>
                      <div style='font-size:13px;font-weight:600;color:#1a1a2e;'>{t}</div>
                      <div style='font-size:10px;color:#9ca3af;'>{m.get('name','')[:22] if 'name' in m else ''}</div>
                    </div>
                  </div>
                  <div>{spark}</div>
                  <div style='text-align:right;'>
                    <div style='font-size:12px;font-weight:500;color:#1a1a2e;'>${m["price"]:,.2f}</div>
                    <div style='font-size:10px;color:{col_c};'>{sgn}${abs(m["chg"]):.2f}</div>
                  </div>
                  <div style='text-align:right;'>
                    <span style='display:inline-flex;align-items:center;gap:2px;font-size:11px;
                                 font-weight:600;padding:3px 8px;border-radius:20px;
                                 background:{bg_pill};color:{col_c};'>
                      {sgn}{abs(m["pct"]):.2f}%
                    </span>
                  </div>
                </div>"""
                st.markdown(row_html, unsafe_allow_html=True)

            # Gainers / Losers cards
            st.markdown("<div style='height:16px;'></div>",unsafe_allow_html=True)
            gc, lc = st.columns(2)
            with gc:
                rows_html="".join(
                    f"<div style='display:flex;justify-content:space-between;padding:4px 0;"
                    f"border-bottom:0.5px solid #f1f5f9;font-size:11px;'>"
                    f"<span style='color:#2563eb;font-weight:500;'>{g['ticker']}</span>"
                    f"<span style='color:{C_GREEN};'>+{g['pct']:.2f}%</span></div>"
                    for g in gainers)
                st.markdown(f"""
                <div style='background:#f8fafc;border:0.5px solid #e2e8f0;
                            border-radius:10px;padding:12px 14px;'>
                  <div style='font-size:11px;font-weight:500;color:#6b7280;
                              margin-bottom:8px;'>Top gainers</div>
                  {rows_html}
                </div>""",unsafe_allow_html=True)
            with lc:
                rows_html="".join(
                    f"<div style='display:flex;justify-content:space-between;padding:4px 0;"
                    f"border-bottom:0.5px solid #f1f5f9;font-size:11px;'>"
                    f"<span style='color:#2563eb;font-weight:500;'>{l['ticker']}</span>"
                    f"<span style='color:{C_RED};'>{l['pct']:.2f}%</span></div>"
                    for l in losers)
                st.markdown(f"""
                <div style='background:#f8fafc;border:0.5px solid #e2e8f0;
                            border-radius:10px;padding:12px 14px;'>
                  <div style='font-size:11px;font-weight:500;color:#6b7280;
                              margin-bottom:8px;'>Top losers</div>
                  {rows_html}
                </div>""",unsafe_allow_html=True)
        else:
            st.info("Market data unavailable. Enter a ticker below to begin a valuation.")

    # ──────────────────────────────────────────────────────────
    # VALUATION PAGES — require data
    # ──────────────────────────────────────────────────────────
    elif st.session_state.val_loaded and st.session_state.val_data:
        d   = st.session_state.val_data
        rf  = st.session_state.val_rf
        tok = st.session_state.ticker

        # ── Assumptions collapsible ───────────────────────────
        with st.expander("Assumptions", expanded=False):
            ac1,ac2,ac3 = st.columns(3)
            with ac1:
                st.markdown("**DCF**")
                dcf_scenario  = st.selectbox("Model",["2-Stage","3-Stage","Monte Carlo","All Three"],key="dcf_type")
                g1_pct        = st.number_input("Growth Yr 1 (%)",value=10.0,step=0.5,format="%.1f",key="g1")
                tg_pct        = st.number_input("Terminal Growth (%)",value=2.5,step=0.1,format="%.1f",key="tg")
                g2_pct        = st.number_input("Fade Growth (%)",value=5.0,step=0.5,format="%.1f",key="g2") if "3-Stage" in dcf_scenario or dcf_scenario=="All Three" else 5.0
                wacc_override = st.number_input("WACC Override (0=auto)",value=0.0,step=0.1,format="%.1f",key="wacc_ov")
                proj_years    = st.slider("Projection Years",5,10,5,key="pyears")
                tax_pct       = st.slider("Tax Rate (%)",10,35,21,key="tax")
            with ac2:
                st.markdown("**Margin-Based FCF**")
                use_margin    = st.checkbox("Enable margin-based FCF",value=False,key="use_margin")
                ebitda_m      = st.slider("EBITDA Margin (%)",5,60,20,key="emarg")/100 if use_margin else 0.20
                fcf_conv      = st.slider("FCF/EBITDA Conv (%)",30,90,60,key="fconv")/100 if use_margin else 0.60
                st.markdown("**Monte Carlo**")
                mc_gs = st.slider("Growth Std Dev (%)",1.0,15.0,5.0,key="mc_gs")/100
                mc_ws = st.slider("WACC Std Dev (%)",0.5,5.0,1.5,key="mc_ws")/100
                n_sims= st.select_slider("Simulations",[1000,5000,10000,25000],value=10000,key="nsims")
            with ac3:
                st.markdown("**Scenarios**")
                bull_g1  = st.number_input("Bull Growth (%)",value=g1_pct+5,step=0.5,format="%.1f",key="bull_g")
                bull_tg  = st.number_input("Bull Terminal (%)",value=tg_pct+0.5,step=0.1,format="%.1f",key="bull_tg")
                bull_wa  = st.number_input("Bull WACC adj (pp)",value=-0.5,step=0.1,format="%.1f",key="bull_wa")
                bear_g1  = st.number_input("Bear Growth (%)",value=max(g1_pct-5,0),step=0.5,format="%.1f",key="bear_g")
                bear_tg  = st.number_input("Bear Terminal (%)",value=max(tg_pct-0.5,0.5),step=0.1,format="%.1f",key="bear_tg")
                bear_wa  = st.number_input("Bear WACC adj (pp)",value=1.0,step=0.1,format="%.1f",key="bear_wa")
                st.markdown("**Comps**")
                manual_comps = st.text_input("Custom comp tickers",placeholder="MSFT,GOOGL",key="mcomps")
                show_bridge  = st.checkbox("Show EV bridge",value=True,key="bridge")

        # ── Derived values ────────────────────────────────────
        tax_rate   = tax_pct/100
        wacc,cost_eq,cost_dbt,e_wt,d_wt = compute_wacc(d,rf,tax_rate)
        if wacc_override>0: wacc=wacc_override/100
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

        # ── Company header ────────────────────────────────────
        logo_h=logo_html(tok,size=40,radius="10px")
        upside=""
        if d["analyst_target"]:
            up=(d["analyst_target"]-current_price)/current_price*100
            upside=f" &nbsp;<span style='font-size:11px;color:{'#16a34a' if up>0 else '#dc2626'};background:{'#dcfce7' if up>0 else '#fee2e2'};padding:2px 8px;border-radius:20px;'>Analyst target ${d['analyst_target']:.2f} ({up:+.1f}%)</span>"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;padding-top:4px;'>"
            f"{logo_h}"
            f"<div><div style='font-size:20px;font-weight:500;color:#1a1a2e;'>{d['name']} "
            f"<span style='font-size:14px;color:#9ca3af;'>({tok})</span>{upside}</div>"
            f"<div style='font-size:11px;color:#9ca3af;margin-top:2px;'>{d['sector']} · {d['industry']} · {d['country']}</div>"
            f"</div></div>",
            unsafe_allow_html=True)

        if fcf_note: st.warning(fcf_note)
        flag=None
        if d["ebitda"]>0 and debt>0:
            lev=debt/d["ebitda"]
            if lev>6: flag=("error",f"High leverage: ND/EBITDA = {lev:.1f}x")
            elif lev>4: flag=("warning",f"Elevated leverage: ND/EBITDA = {lev:.1f}x")
        if flag:
            if flag[0]=="error": st.error(flag[1])
            else: st.warning(flag[1])

        # KPI rows
        section_hdr("Key Financials")
        kpi_row([("Stock Price",f"${current_price:,.2f}"),("Market Cap",fB(d["mkt_cap"])),
                 ("Enterprise Value",fB(d["enterprise_value"])),("Revenue",fB(d["revenue"])),
                 ("EBITDA",fB(d["ebitda"])),("FCF",fB(d["fcf"]) if d["fcf"] else "N/A"),
                 ("Net Income",fB(d["net_income"]))])
        kpi_row([("Beta",f"{float(d['beta']):.2f}"),("P/E (TTM)",fx(d["pe"])),
                 ("Fwd P/E",fx(d["fwd_pe"])),("EV/EBITDA",fx(d["ev_ebitda"])),
                 ("EV/Revenue",fx(d["ev_revenue"])),("ROE",fp(d["roe"])),("WACC",fp(wacc))])
        kpi_row([("Gross Margin",fp(d["gross_margin"])),("EBITDA Margin",fp(d["ebitda_margin"])),
                 ("Rev Growth",fp(d["rev_growth"])),("Hist Rev CAGR",fp(hist_growth)),
                 ("Net Debt",fB(debt-cash)),
                 ("ND/EBITDA",fx((debt-cash)/d["ebitda"]) if d["ebitda"]>0 else "N/A"),
                 ("Risk-Free Rate",fp(rf))])

        # EV Bridge
        if show_bridge:
            section_hdr("Enterprise Value to Equity Bridge")
            bridge_items=[("Enterprise Value",d["enterprise_value"],"absolute"),
                          ("(−) Total Debt",-debt,"relative"),
                          ("(+) Cash",cash,"relative"),
                          ("(−) Minority",-d["minority_interest"],"relative"),
                          ("(−) Preferred",-d["preferred_stock"],"relative"),
                          ("= Equity Value",d["mkt_cap"],"total")]
            fig_b=go.Figure(go.Waterfall(
                orientation="v",
                measure=[b[2] for b in bridge_items],
                x=[b[0] for b in bridge_items],
                y=[b[1] for b in bridge_items],
                connector=dict(line=dict(color="#cbd5e1",width=1,dash="dot")),
                increasing=dict(marker_color=C_GREEN,marker_line_width=0),
                decreasing=dict(marker_color=C_RED,marker_line_width=0),
                totals=dict(marker_color=C_BLUE,marker_line_width=0),
                text=[fB(b[1]) for b in bridge_items],
                textposition="outside",textfont=dict(size=10,family=FONT),
            ))
            apply_theme(fig_b,height=320,legend=False)
            fig_b.update_layout(yaxis=dict(title="Value ($)",tickprefix="$",tickformat=",.0f"),
                                 margin=dict(l=60,r=30,t=20,b=40))
            st.plotly_chart(fig_b,use_container_width=True)

        # Description
        if d["description"]:
            if st.toggle("Show business description",value=False,key="desc_tog"):
                st.write(d["description"][:900]+"...")

        # ── PAGE: DCF ─────────────────────────────────────────
        if page == "dcf":
            section_hdr("DCF Analysis")
            st.caption(f"FCF Base: {fB(active_fcf)} · WACC: {fp(wacc)} · Stage 1 Growth: {fp(g1)} · Terminal: {fp(terminal_g)} · Beta: {float(d['beta']):.2f}")

            all_dcf={}; mc_results=None; mc_p10=mc_p50=mc_p90=0.0

            if dcf_scenario in ["2-Stage","All Three"]:
                ps2,ev2,pvs2=dcf_2stage(active_fcf,g1,wacc,terminal_g,proj_years,debt,cash,shares)
                all_dcf["2-Stage DCF"]=ps2
                if dcf_scenario=="2-Stage":
                    up=(ps2-current_price)/current_price*100 if current_price else 0
                    ca,cb,cc=st.columns(3)
                    ca.metric("Implied Price",f"${ps2:,.2f}")
                    cb.metric("Current Price",f"${current_price:,.2f}")
                    cc.metric("Upside/Downside",f"{up:+.1f}%",delta_color="normal" if up>0 else "inverse")
                    yr_labels=[f"Yr {i+1}" for i in range(proj_years)]
                    tv_pv=max((ps2*shares)-sum(pvs2)+debt-cash,0)
                    fig=go.Figure()
                    fig.add_trace(go.Bar(name="PV of FCF",x=yr_labels,y=pvs2,
                                         marker=dict(color=C_BLUE,opacity=0.85,line=dict(width=0)),
                                         text=[fB(v) for v in pvs2],textposition="outside",textfont=dict(size=10,color=C_GRAY)))
                    fig.add_trace(go.Bar(name="PV of Terminal Value",x=["Terminal"],y=[tv_pv],
                                         marker=dict(color=C_PURPLE,opacity=0.85,line=dict(width=0)),
                                         text=[fB(tv_pv)],textposition="outside",textfont=dict(size=10,color=C_GRAY)))
                    apply_theme(fig,"DCF Value Build — Present Value of Cash Flows",height=340)
                    fig.update_layout(barmode="group",yaxis=dict(title="PV ($)",tickprefix="$",tickformat=",.0f"),bargap=0.3)
                    st.plotly_chart(fig,use_container_width=True)

            if dcf_scenario in ["3-Stage","All Three"]:
                ps3,ev3,pvs3=dcf_3stage(active_fcf,g1,g2,wacc,terminal_g,3,max(proj_years-3,1),debt,cash,shares)
                all_dcf["3-Stage DCF"]=ps3
                if dcf_scenario=="3-Stage":
                    up=(ps3-current_price)/current_price*100 if current_price else 0
                    ca,cb,cc=st.columns(3)
                    ca.metric("Implied Price",f"${ps3:,.2f}")
                    cb.metric("Current Price",f"${current_price:,.2f}")
                    cc.metric("Upside/Downside",f"{up:+.1f}%",delta_color="normal" if up>0 else "inverse")

            if dcf_scenario in ["Monte Carlo","All Three"]:
                raw=dcf_mc(active_fcf,g1,mc_gs,wacc,mc_ws,terminal_g,n_sims,proj_years,debt,cash,shares)
                mc_results=raw[np.isfinite(raw)]
                mc_p10=float(np.percentile(mc_results,10))
                mc_p50=float(np.percentile(mc_results,50))
                mc_p90=float(np.percentile(mc_results,90))
                all_dcf.update({"Monte Carlo (P10)":mc_p10,"Monte Carlo (P50)":mc_p50,"Monte Carlo (P90)":mc_p90})
                if dcf_scenario=="Monte Carlo":
                    ca,cb,cc,cd=st.columns(4)
                    ca.metric("P10 — Bear",f"${mc_p10:,.2f}")
                    cb.metric("P50 — Base",f"${mc_p50:,.2f}")
                    cc.metric("P90 — Bull",f"${mc_p90:,.2f}")
                    cd.metric("Prob > Current",f"{(mc_results>current_price).mean()*100:.0f}%")
                p1,p99=np.percentile(mc_results,1),np.percentile(mc_results,99)
                mc_cl=mc_results[(mc_results>=p1)&(mc_results<=p99)]
                fig_mc=go.Figure()
                fig_mc.add_trace(go.Histogram(x=mc_cl,nbinsx=60,name="Simulations",
                                               marker=dict(color=C_BLUE,opacity=0.75,line=dict(width=0))))
                fig_mc.add_vline(x=current_price,line_width=2,line_dash="dash",line_color=C_RED,
                                  annotation_text=f"Current ${current_price:.2f}",annotation_position="top right",
                                  annotation=dict(font=dict(size=11,color=C_RED,family=FONT)))
                fig_mc.add_vline(x=mc_p50,line_width=1.5,line_dash="dot",line_color=C_GREEN,
                                  annotation_text=f"P50 ${mc_p50:.2f}",annotation_position="top left",
                                  annotation=dict(font=dict(size=11,color=C_GREEN,family=FONT)))
                fig_mc.add_vrect(x0=mc_p10,x1=mc_p90,fillcolor=C_BLUE,opacity=0.06,layer="below",line_width=0)
                apply_theme(fig_mc,f"Monte Carlo DCF — {n_sims:,} Simulations",height=360,legend=False)
                fig_mc.update_layout(xaxis=dict(title="Implied Price ($)",tickprefix="$"),yaxis=dict(title="Frequency"))
                st.plotly_chart(fig_mc,use_container_width=True)

            if dcf_scenario=="All Three":
                section_hdr("Model Comparison")
                rows_cmp=[]
                for model,price in [("2-Stage DCF",all_dcf.get("2-Stage DCF")),
                                     ("3-Stage DCF",all_dcf.get("3-Stage DCF")),
                                     ("Monte Carlo P10",mc_p10),("Monte Carlo P50",mc_p50),("Monte Carlo P90",mc_p90)]:
                    up_s=(f"{(price-current_price)/current_price*100:+.1f}%" if price and current_price else "N/A")
                    rows_cmp.append({"Model":model,"Implied Price":f"${price:,.2f}" if price else "N/A","Upside (%)":up_s})
                st.dataframe(pd.DataFrame(rows_cmp),use_container_width=True,hide_index=True)

            if st.toggle("Show WACC Decomposition",value=False,key="wacc_tog"):
                wd=pd.DataFrame({"Component":["Cost of Equity","After-tax Cost of Debt","WACC"],
                                  "Rate":[fp(cost_eq),fp(cost_dbt*(1-tax_rate)),fp(wacc)],
                                  "Weight":[fp(e_wt),fp(d_wt),"100%"],
                                  "Contribution":[fp(cost_eq*e_wt),fp(cost_dbt*(1-tax_rate)*d_wt),fp(wacc)]})
                st.dataframe(wd,hide_index=True,use_container_width=True)
                st.caption(f"CAPM: Rf {fp(rf)} + Beta {float(d['beta']):.2f} × ERP 5.5% = {fp(cost_eq)}")

        # ── PAGE: SCENARIOS ───────────────────────────────────
        elif page == "scenarios":
            section_hdr("Bull / Base / Bear Scenarios")
            scenarios={"Bear":(bear_g1/100,bear_tg_v,bear_wacc),"Base":(g1,terminal_g,wacc),"Bull":(bull_g1/100,bull_tg_v,bull_wacc)}
            colors_sc={"Bear":C_RED,"Base":C_BLUE,"Bull":C_GREEN}
            sc_res={}
            for sn,(sg,stg,sw) in scenarios.items():
                ps,ev,_=dcf_2stage(active_fcf,sg,sw,stg,proj_years,debt,cash,shares)
                sc_res[sn]={"price":ps,"ev":ev,"g":sg,"tg":stg,"wacc":sw}
            ca,cb,cc=st.columns(3)
            for col,(sn,res) in zip([ca,cb,cc],sc_res.items()):
                up=(res["price"]-current_price)/current_price*100
                col.metric(f"{sn} Case",f"${res['price']:,.2f}",f"{up:+.1f}%",delta_color="normal" if up>0 else "inverse")
            sc_tbl=[{"Scenario":sn,"Growth Yr 1":fp(r["g"]),"Terminal":fp(r["tg"]),"WACC":fp(r["wacc"]),
                     "Implied Price":f"${r['price']:,.2f}","Upside":f"{(r['price']-current_price)/current_price*100:+.1f}%"}
                    for sn,r in sc_res.items()]
            st.dataframe(pd.DataFrame(sc_tbl),use_container_width=True,hide_index=True)
            sc_prices=[r["price"] for r in sc_res.values()]
            fig_sc=go.Figure()
            for sn,res in sc_res.items():
                fig_sc.add_trace(go.Bar(name=sn,x=[sn],y=[res["price"]],
                                         marker=dict(color=colors_sc[sn],opacity=0.82,line=dict(width=0)),
                                         text=f"${res['price']:,.2f}",textposition="outside",
                                         textfont=dict(size=12,color=colors_sc[sn],family=FONT),width=0.45))
            fig_sc.add_hline(y=current_price,line_width=1.5,line_dash="dash",line_color=C_GRAY,
                              annotation_text=f"Current ${current_price:.2f}",annotation_position="top right",
                              annotation=dict(font=dict(size=11,color=C_GRAY,family=FONT)))
            apply_theme(fig_sc,"Scenario Implied Share Price",height=360,legend=False)
            fig_sc.update_layout(yaxis=dict(title="Implied Price ($)",tickprefix="$",
                                             range=[max(0,min(sc_prices)*0.75),max(sc_prices)*1.28]),
                                  xaxis=dict(showgrid=False),bargap=0.45)
            st.plotly_chart(fig_sc,use_container_width=True)

            # Tornado
            section_hdr("Sensitivity Tornado")
            base_price=sc_res["Base"]["price"]
            tornado=[]
            for label,dw,dg in [("WACC +/-2pp",0.02,0),("FCF Growth +/-5pp",0,0.05),
                                  ("Terminal Growth +/-1pp",0,0),("FCF Base +/-20%",0,0)]:
                if "WACC" in label:
                    lo,_,_=dcf_2stage(active_fcf,g1,wacc+dw,terminal_g,proj_years,debt,cash,shares)
                    hi,_,_=dcf_2stage(active_fcf,g1,wacc-dw,terminal_g,proj_years,debt,cash,shares)
                elif "Growth" in label and "Terminal" not in label:
                    lo,_,_=dcf_2stage(active_fcf,max(g1-dg,0),wacc,terminal_g,proj_years,debt,cash,shares)
                    hi,_,_=dcf_2stage(active_fcf,g1+dg,wacc,terminal_g,proj_years,debt,cash,shares)
                elif "Terminal" in label:
                    lo,_,_=dcf_2stage(active_fcf,g1,wacc,max(terminal_g-0.01,0.005),proj_years,debt,cash,shares)
                    hi,_,_=dcf_2stage(active_fcf,g1,wacc,min(terminal_g+0.01,wacc-0.005),proj_years,debt,cash,shares)
                else:
                    lo,_,_=dcf_2stage(active_fcf*0.8,g1,wacc,terminal_g,proj_years,debt,cash,shares)
                    hi,_,_=dcf_2stage(active_fcf*1.2,g1,wacc,terminal_g,proj_years,debt,cash,shares)
                tornado.append((label,lo-base_price,hi-base_price))
            tornado.sort(key=lambda x:abs(x[2]-x[1]),reverse=True)
            tor_x=max(abs(d) for _,lo,hi in tornado for d in [lo,hi])*1.2
            fig_tor=go.Figure()
            for label,lo_d,hi_d in tornado:
                fig_tor.add_trace(go.Bar(x=[lo_d],y=[label],orientation="h",
                                          marker=dict(color=C_RED,opacity=0.78,line=dict(width=0)),
                                          showlegend=False,text=f"${lo_d:+,.1f}",textposition="outside",
                                          textfont=dict(size=10,color=C_RED,family=FONT)))
                fig_tor.add_trace(go.Bar(x=[hi_d],y=[label],orientation="h",
                                          marker=dict(color=C_GREEN,opacity=0.78,line=dict(width=0)),
                                          showlegend=False,text=f"${hi_d:+,.1f}",textposition="outside",
                                          textfont=dict(size=10,color=C_GREEN,family=FONT)))
            fig_tor.add_vline(x=0,line_color=C_DARK,line_width=1.5)
            apply_theme(fig_tor,f"Assumption Impact on Base Price ${base_price:,.2f}",height=320,legend=False)
            fig_tor.update_layout(xaxis=dict(title="Change in Implied Price ($)",tickprefix="$",range=[-tor_x,tor_x]),
                                   yaxis=dict(autorange="reversed"),barmode="overlay",margin=dict(l=200,r=80,t=50,b=50))
            st.plotly_chart(fig_tor,use_container_width=True)

        # ── PAGE: REVERSE DCF ─────────────────────────────────
        elif page == "rdcf":
            section_hdr("Reverse DCF — Market-Implied Growth Rate")
            implied_g=reverse_dcf(current_price,shares,debt,cash,active_fcf,wacc,terminal_g,proj_years)
            ca,cb,cc,cd=st.columns(4)
            ca.metric("Market-Implied Growth",fp(implied_g))
            cb.metric("Your Base Case",fp(g1))
            cc.metric("Historical CAGR",fp(hist_growth))
            cd.metric("Analyst Est. Growth",fp(d["earnings_growth"]))
            gap=implied_g-g1
            if gap>0.05: msg=f"Market pricing {fp(implied_g)} growth — {fp(gap)} above your base. Stock may be expensive."; mc="#991b1b"
            elif gap<-0.05: msg=f"Market pricing only {fp(implied_g)} growth — {fp(abs(gap))} below your base. Potential value opportunity."; mc="#14532d"
            else: msg=f"Market-implied {fp(implied_g)} broadly in line with your base case {fp(g1)}. Appears fairly valued."; mc="#1e3a5f"
            st.markdown(f"<div style='background:#f8fafc;border-left:4px solid {mc};padding:10px 14px;border-radius:4px;margin:10px 0;color:{mc};font-size:0.88rem;'>{msg}</div>",unsafe_allow_html=True)
            price_range=np.linspace(current_price*0.5,current_price*2.0,60)
            ig_arr=np.array([reverse_dcf(p,shares,debt,cash,active_fcf,wacc,terminal_g,proj_years) for p in price_range])
            mask=np.isfinite(ig_arr)&(ig_arr>-0.5)&(ig_arr<1.0)
            fig_r=go.Figure()
            fig_r.add_trace(go.Scatter(x=ig_arr[mask]*100,y=price_range[mask],mode="lines",
                                        line=dict(color=C_BLUE,width=2.5),fill="tozeroy",
                                        fillcolor=f"rgba(37,99,235,0.06)"))
            fig_r.add_hline(y=current_price,line_width=1.5,line_dash="dash",line_color=C_RED,
                             annotation_text=f"Current ${current_price:.2f}",annotation_position="top right",
                             annotation=dict(font=dict(size=11,color=C_RED,family=FONT)))
            fig_r.add_vline(x=g1*100,line_width=1.5,line_dash="dot",line_color=C_GREEN,
                             annotation_text=f"Base {g1*100:.1f}%",annotation_position="top left",
                             annotation=dict(font=dict(size=11,color=C_GREEN,family=FONT)))
            apply_theme(fig_r,"Stock Price vs Market-Implied FCF Growth Rate",height=400,legend=False)
            fig_r.update_layout(xaxis=dict(title="Market-Implied Growth Rate (%)",ticksuffix="%"),
                                  yaxis=dict(title="Stock Price ($)",tickprefix="$"))
            st.plotly_chart(fig_r,use_container_width=True)

        # ── PAGE: COMPS ───────────────────────────────────────
        elif page == "comps":
            section_hdr("Comparable Company Analysis")
            base_comps=SECTOR_COMPS.get(d["sector"],["AAPL","MSFT","GOOGL","AMZN","META"])
            if manual_comps:
                extra=[t.strip().upper() for t in manual_comps.split(",") if t.strip()]
                base_comps=list(dict.fromkeys(extra+base_comps))
            with st.spinner("Fetching comps..."):
                cdf=fetch_comps(tuple(base_comps[:8]),tok)
            if not cdf.empty:
                st.caption(f"Sector: {d['sector']} · Comps: {', '.join(cdf['Ticker'].tolist())}")
                disp=cdf[["Ticker","Name","Mkt Cap ($B)","EV/EBITDA","EV/Revenue","P/E (TTM)","Fwd P/E","EBITDA Margin","Rev Growth","ROE"]].copy()
                for col in ["EV/EBITDA","EV/Revenue","P/E (TTM)","Fwd P/E"]:
                    disp[col]=disp[col].apply(lambda x:f"{x:.1f}x" if pd.notna(x) else "N/A")
                for col in ["EBITDA Margin","Rev Growth","ROE"]:
                    disp[col]=disp[col].apply(lambda x:f"{x*100:.1f}%" if pd.notna(x) else "N/A")
                em=fp(d["ebitda"]/d["revenue"]) if d["revenue"] else "N/A"
                subj=pd.DataFrame([{"Ticker":f"[{tok}]","Name":d["name"][:22],
                                     "Mkt Cap ($B)":round((d["mkt_cap"] or 0)/1e9,1),
                                     "EV/EBITDA":fx(d["ev_ebitda"]),"EV/Revenue":fx(d["ev_revenue"]),
                                     "P/E (TTM)":fx(d["pe"]),"Fwd P/E":fx(d["fwd_pe"]),
                                     "EBITDA Margin":em,"Rev Growth":fp(d["rev_growth"]),"ROE":fp(d["roe"])}])
                st.dataframe(pd.concat([disp,subj],ignore_index=True),use_container_width=True,hide_index=True)
                cp=comps_implied(d,cdf)
                if cp:
                    section_hdr("Median-Multiple Implied Price")
                    cp_cols=st.columns(len(cp))
                    for col,(method,price) in zip(cp_cols,cp.items()):
                        up=(price-current_price)/current_price*100
                        col.metric(method,f"${price:,.2f}",f"{up:+.1f}%",delta_color="normal" if up>0 else "inverse")
                reg_price,reg_mult,r2=comps_regression(d,cdf)
                if reg_price:
                    section_hdr("Regression-Implied Price")
                    ra,rb,rc=st.columns(3)
                    up=(reg_price-current_price)/current_price*100
                    ra.metric("Regression Implied",f"${reg_price:,.2f}",f"{up:+.1f}%",delta_color="normal" if up>0 else "inverse")
                    rb.metric("Implied Multiple",fx(reg_mult))
                    rc.metric("R-squared",f"{r2:.2f}")
                sub_sc=cdf[["EV/EBITDA","Rev Growth","Ticker","Mkt Cap ($B)"]].dropna()
                if len(sub_sc)>=3:
                    x_sc=sub_sc["Rev Growth"].values; y_sc=sub_sc["EV/EBITDA"].values
                    x_p5,x_p95=np.percentile(x_sc,5),np.percentile(x_sc,95)
                    y_p5,y_p95=np.percentile(y_sc,5),np.percentile(y_sc,95)
                    x_pad=(x_p95-x_p5)*0.3 or 0.05; y_pad=(y_p95-y_p5)*0.3 or 2
                    sl,ic,_,_,_=stats.linregress(x_sc,y_sc)
                    x_fit=np.linspace(x_sc.min(),x_sc.max(),60)
                    fig_sc2=go.Figure()
                    fig_sc2.add_trace(go.Scatter(x=x_fit*100,y=ic+sl*x_fit,mode="lines",
                                                  line=dict(color=C_GRAY,dash="dot",width=1.5),name="Regression"))
                    for _,row in sub_sc.iterrows():
                        sz=max(8,min(28,row["Mkt Cap ($B)"]**0.38*3.5)) if row["Mkt Cap ($B)"] else 10
                        fig_sc2.add_trace(go.Scatter(x=[row["Rev Growth"]*100],y=[row["EV/EBITDA"]],
                                                      mode="markers+text",text=[row["Ticker"]],textposition="top center",
                                                      textfont=dict(size=10,color=C_BLUE,family=FONT),
                                                      marker=dict(size=sz,color=C_BLUE,opacity=0.75,line=dict(color="white",width=1.5)),showlegend=False))
                    if d["ev_ebitda"] and d["rev_growth"]:
                        fig_sc2.add_trace(go.Scatter(x=[d["rev_growth"]*100],y=[d["ev_ebitda"]],
                                                      mode="markers+text",text=[f"[{tok}]"],textposition="top center",
                                                      textfont=dict(size=11,color=C_RED,family=FONT),
                                                      marker=dict(size=16,color=C_RED,symbol="diamond",line=dict(color="white",width=2)),showlegend=False))
                    apply_theme(fig_sc2,"EV/EBITDA vs Revenue Growth — Comps + Regression",height=420)
                    fig_sc2.update_layout(xaxis=dict(title="Revenue Growth (%)",ticksuffix="%",range=[x_p5*100-x_pad*100,x_p95*100+x_pad*100]),
                                           yaxis=dict(title="EV/EBITDA (x)",ticksuffix="x",range=[max(0,y_p5-y_pad),y_p95+y_pad]))
                    st.plotly_chart(fig_sc2,use_container_width=True)
            else:
                st.warning("No comp data available.")

        # ── PAGE: DDM ─────────────────────────────────────────
        elif page == "ddm":
            section_hdr("Dividend Discount Model")
            div=d["dividend"] or 0
            if div==0:
                st.warning(f"{tok} does not pay a dividend. DDM not applicable.")
                implied_div=current_price*(cost_eq-terminal_g)/(1+terminal_g)
                st.metric("Implied Dividend for Fair Value at Current Price",f"${implied_div:.2f}/share")
            else:
                st.markdown(f"**Annual Dividend:** ${div:.2f} · **Payout Ratio:** {fp(d['payout_ratio'])} · **Cost of Equity:** {fp(cost_eq)}")
                gv=ddm_gordon(div,terminal_g,cost_eq)
                ms=ddm_multistage(div,g1,terminal_g,cost_eq,5)
                ca,cb,cc=st.columns(3)
                if gv:
                    up=(gv-current_price)/current_price*100
                    ca.metric("Gordon Growth",f"${gv:,.2f}",f"{up:+.1f}%",delta_color="normal" if up>0 else "inverse")
                if ms:
                    up2=(ms-current_price)/current_price*100
                    cb.metric("Multi-Stage DDM",f"${ms:,.2f}",f"{up2:+.1f}%",delta_color="normal" if up2>0 else "inverse")
                cc.metric("Current Price",f"${current_price:,.2f}")
                ke_range=np.arange(cost_eq-0.03,cost_eq+0.035,0.005)
                ddm_curve=[ddm_gordon(div,terminal_g,ke) or 0 for ke in ke_range]
                ddm_arr=np.array(ddm_curve); ddm_valid=ddm_arr[ddm_arr>0]
                fig_ddm=go.Figure()
                fig_ddm.add_trace(go.Scatter(x=ke_range*100,y=ddm_curve,mode="lines+markers",
                                              line=dict(color=C_BLUE,width=2.5),
                                              marker=dict(size=6,color=C_BLUE,line=dict(color="white",width=1.5)),
                                              fill="tozeroy",fillcolor=f"rgba(37,99,235,0.06)"))
                fig_ddm.add_hline(y=current_price,line_width=1.5,line_dash="dash",line_color=C_RED,
                                   annotation_text=f"Current ${current_price:.2f}",annotation_position="top right",
                                   annotation=dict(font=dict(size=11,color=C_RED,family=FONT)))
                apply_theme(fig_ddm,"DDM Implied Value vs Cost of Equity",height=360,legend=False)
                fig_ddm.update_layout(xaxis=dict(title="Cost of Equity (%)",ticksuffix="%"),
                                       yaxis=dict(title="Implied Price ($)",tickprefix="$",
                                                  range=[0,min(ddm_valid.max()*1.2,current_price*4) if len(ddm_valid) else current_price*3]))
                st.plotly_chart(fig_ddm,use_container_width=True)

        # ── PAGE: FOOTBALL FIELD ──────────────────────────────
        elif page == "ff":
            section_hdr("Valuation Football Field")
            bars=[]
            ps2,_,_=dcf_2stage(active_fcf,g1,wacc,terminal_g,proj_years,debt,cash,shares)
            if ps2: bars.append(("2-Stage DCF",ps2*0.80,ps2*1.20,ps2))
            ps3,_,_=dcf_3stage(active_fcf,g1,g2,wacc,terminal_g,3,max(proj_years-3,1),debt,cash,shares)
            if ps3: bars.append(("3-Stage DCF",ps3*0.80,ps3*1.20,ps3))
            raw=dcf_mc(active_fcf,g1,mc_gs,wacc,mc_ws,terminal_g,n_sims,proj_years,debt,cash,shares)
            mc_r=raw[np.isfinite(raw)]
            if len(mc_r): bars.append(("Monte Carlo",float(np.percentile(mc_r,10)),float(np.percentile(mc_r,90)),float(np.percentile(mc_r,50))))
            bs_r,_,_=dcf_2stage(active_fcf,bear_g1/100,bear_wacc,bear_tg_v,proj_years,debt,cash,shares)
            bu_r,_,_=dcf_2stage(active_fcf,bull_g1/100,bull_wacc,bull_tg_v,proj_years,debt,cash,shares)
            ba_r,_,_=dcf_2stage(active_fcf,g1,wacc,terminal_g,proj_years,debt,cash,shares)
            if bs_r and bu_r: bars.append(("Scenario Range",bs_r,bu_r,ba_r))
            try:
                base_comps=SECTOR_COMPS.get(d["sector"],["AAPL","MSFT","GOOGL"])
                cdf2=fetch_comps(tuple(base_comps[:8]),tok)
                if not cdf2.empty:
                    ev2eq=lambda ev:(ev-debt+cash)/shares if shares else 0
                    ev_eb=cdf2["EV/EBITDA"].dropna()
                    if len(ev_eb)>=2 and d["ebitda"]>0:
                        bars.append(("EV/EBITDA Comps",ev2eq(d["ebitda"]*ev_eb.quantile(0.25)),ev2eq(d["ebitda"]*ev_eb.quantile(0.75)),ev2eq(d["ebitda"]*ev_eb.median())))
                    ev_rv=cdf2["EV/Revenue"].dropna()
                    if len(ev_rv)>=2 and d["revenue"]>0:
                        bars.append(("EV/Revenue Comps",ev2eq(d["revenue"]*ev_rv.quantile(0.25)),ev2eq(d["revenue"]*ev_rv.quantile(0.75)),ev2eq(d["revenue"]*ev_rv.median())))
                    pe_v=cdf2["P/E (TTM)"].dropna()
                    if len(pe_v)>=2 and d["net_income"]>0:
                        bars.append(("P/E Comps",(d["net_income"]*pe_v.quantile(0.25))/shares,(d["net_income"]*pe_v.quantile(0.75))/shares,(d["net_income"]*pe_v.median())/shares))
            except: pass
            if d["analyst_target"]:
                at=d["analyst_target"]; bars.append(("Analyst Consensus",at*0.85,at*1.15,at))
            bars=[(n,lo,hi,mid) for n,lo,hi,mid in bars if lo>0 and hi>0 and hi<current_price*15 and lo<current_price*15]
            if bars:
                all_lo=[b[1] for b in bars]; all_hi=[b[2] for b in bars]
                x_min=max(0,min(all_lo)*0.80); x_max=max(all_hi)*1.20
                fig_ff=go.Figure()
                for i,(name,lo,hi,mid) in enumerate(bars):
                    c=PALETTE[i%len(PALETTE)]
                    fig_ff.add_trace(go.Bar(name=name,x=[hi-lo],y=[name],base=[lo],orientation="h",
                                             marker=dict(color=c,opacity=0.78,line=dict(width=0)),
                                             hovertemplate=f"<b>{name}</b><br>Bear: ${lo:,.2f}<br>Base: ${mid:,.2f}<br>Bull: ${hi:,.2f}<extra></extra>",showlegend=False))
                    fig_ff.add_trace(go.Scatter(x=[mid],y=[name],mode="markers",
                                                 marker=dict(size=11,color="white",line=dict(color=c,width=2.5)),showlegend=False,hoverinfo="skip"))
                    fig_ff.add_annotation(x=lo,y=name,text=f"${lo:,.0f}",showarrow=False,xanchor="right",font=dict(size=9,color=c,family=FONT),xshift=-6)
                    fig_ff.add_annotation(x=hi,y=name,text=f"${hi:,.0f}",showarrow=False,xanchor="left",font=dict(size=9,color=c,family=FONT),xshift=6)
                fig_ff.add_vline(x=current_price,line_width=2,line_dash="solid",line_color=C_RED,
                                  annotation_text=f"Current ${current_price:.2f}",annotation_position="top right",
                                  annotation=dict(font=dict(size=12,color=C_RED,family=FONT)))
                apply_theme(fig_ff,f"{d['name']} ({tok}) — Valuation Football Field",
                             height=max(400,80+len(bars)*65),legend=False)
                fig_ff.update_layout(xaxis=dict(title="Implied Share Price ($)",tickprefix="$",range=[x_min,x_max],zeroline=False),
                                      yaxis=dict(autorange="reversed"),barmode="overlay",margin=dict(l=190,r=80,t=60,b=55))
                st.plotly_chart(fig_ff,use_container_width=True)
                section_hdr("Implied Price Summary")
                summ=[{"Method":n,"Bear Case":f"${lo:,.2f}","Base Case":f"${mid:,.2f}","Bull Case":f"${hi:,.2f}",
                        "Upside to Base":f"{(mid-current_price)/current_price*100:+.1f}%"} for n,lo,hi,mid in bars]
                st.dataframe(pd.DataFrame(summ),use_container_width=True,hide_index=True)
                st.divider()
                try:
                    xl=build_excel(d,wacc,cost_eq,rf,terminal_g,g1,active_fcf,proj_years,{},None,bars)
                    st.download_button("Download Full Model as Excel",xl,f"{tok}_valuation.xlsx",
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                except Exception as ex:
                    st.caption(f"Excel export unavailable: {ex}")

        # ── PAGE: SENSITIVITY ─────────────────────────────────
        elif page == "sens":
            section_hdr("DCF Sensitivity Analysis")
            st.caption("Green = above current price · Red = below current price")
            sens=sensitivity_table(active_fcf,wacc,g1,terminal_g,debt,cash,shares,proj_years)
            z=sens.values.astype(float)
            z_finite=z[np.isfinite(z)]
            z_lo=np.percentile(z_finite,5) if len(z_finite) else 0
            z_hi=np.percentile(z_finite,95) if len(z_finite) else 1
            z_cl=np.clip(z,z_lo,z_hi)
            fig_h=go.Figure(data=go.Heatmap(
                z=z_cl,x=[f"{v*100:.1f}%" for v in sens.columns],y=[f"{v*100:.1f}%" for v in sens.index],
                colorscale=[[0.0,"#ef4444"],[0.35,"#fca5a5"],[0.5,"#fef9c3"],[0.65,"#86efac"],[1.0,"#16a34a"]],
                zmid=current_price,zmin=z_lo,zmax=z_hi,
                text=[[f"${v:.0f}" if np.isfinite(v) else "N/A" for v in row] for row in z],
                texttemplate="%{text}",textfont=dict(size=10,family=FONT,color="#1e293b"),
                hovertemplate="Growth: %{y}<br>WACC: %{x}<br>Price: %{text}<extra></extra>",
                colorbar=dict(title="Price ($)",tickprefix="$",tickfont=dict(size=10,family=FONT))))
            apply_theme(fig_h,height=440,legend=False)
            fig_h.update_layout(xaxis=dict(title="WACC"),yaxis=dict(title="FCF Growth Rate"),margin=dict(l=90,r=20,t=20,b=60))
            st.plotly_chart(fig_h,use_container_width=True)

            section_hdr("Terminal Growth Rate Sensitivity")
            tg_range=np.arange(0.01,0.04,0.005)
            line_colors=[C_INDIGO,C_BLUE,C_TEAL]
            fig_tg=go.Figure()
            all_tg_pts=[]
            for w,lc in zip([wacc-0.01,wacc,wacc+0.01],line_colors):
                pts=[]
                for tg in tg_range:
                    if w<=tg: pts.append(np.nan); continue
                    p,_,_=dcf_2stage(active_fcf,g1,w,tg,proj_years,debt,cash,shares)
                    pts.append(p)
                all_tg_pts.extend([p for p in pts if p and np.isfinite(p)])
                fig_tg.add_trace(go.Scatter(x=tg_range*100,y=pts,mode="lines+markers",
                                             name=f"WACC={w*100:.1f}%",line=dict(color=lc,width=2.5),
                                             marker=dict(size=6,color=lc,line=dict(color="white",width=1.5))))
            fig_tg.add_hline(y=current_price,line_width=1.5,line_dash="dash",line_color=C_RED,
                              annotation_text=f"Current ${current_price:.2f}",annotation_position="top right",
                              annotation=dict(font=dict(size=11,color=C_RED,family=FONT)))
            apply_theme(fig_tg,"Terminal Growth Rate Sensitivity",height=360)
            fig_tg.update_layout(xaxis=dict(title="Terminal Growth Rate (%)",ticksuffix="%"),
                                   yaxis=dict(title="Implied Price ($)",tickprefix="$",
                                              range=[0,min(max(all_tg_pts)*1.15,current_price*5) if all_tg_pts else current_price*3]),
                                   legend=dict(x=0.02,y=0.98))
            st.plotly_chart(fig_tg,use_container_width=True)

            if st.toggle("Show raw sensitivity table",value=False,key="raw_sens"):
                raw_df=sens.copy()
                raw_df.columns=[f"WACC {v*100:.1f}%" for v in raw_df.columns]
                raw_df.index=[f"Growth {v*100:.1f}%" for v in raw_df.index]
                st.dataframe(raw_df.style.format("${:.2f}"),use_container_width=True)

    elif page!="home":
        with col_main:
            st.info("Enter a ticker in the bottom left and click Run Valuation to begin.")

# Footer
with col_main:
    st.divider()
    st.caption(f"Data: Yahoo Finance · FRED · For educational purposes only — not investment advice · {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M UTC')}")
