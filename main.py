import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import pytz
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="API Tasas Oficiales BCV", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cache = {
    "data": None,
    "last_fetched": None
}

CACHE_TTL_MINUTES = 60

def scrapear_bcv():
    url = "https://www.bcv.org.ve"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers, verify=False, timeout=15)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    dolar_box = soup.find(id="dolar")
    usd_val = 0.0
    if dolar_box:
        strong = dolar_box.find("strong")
        if strong:
            usd_str = strong.text.strip().replace(".", "").replace(",", ".")
            usd_val = float(re.findall(r"[\d\.]+", usd_str)[0])
            
    euro_box = soup.find(id="euro")
    eur_val = 0.0
    if euro_box:
        strong = euro_box.find("strong")
        if strong:
            eur_str = strong.text.strip().replace(".", "").replace(",", ".")
            eur_val = float(re.findall(r"[\d\.]+", eur_str)[0])
            
    fecha_box = soup.select_one(".date-display-single, .pull-right.dinpro span, .view-tipo-de-cambio-oficial-del-bcv .date-display-single")
    if fecha_box:
        fecha_valor = fecha_box.text.strip()
    else:
        tz_ve = pytz.timezone("America/Caracas")
        fecha_valor = datetime.now(tz_ve).strftime("%d/%m/%Y")
        
    if usd_val <= 0.0:
        raise ValueError("No se pudo obtener una tasa válida de USD desde el portal.")
        
    return {
        "usd": round(usd_val, 4),
        "eur": round(eur_val, 4),
        "fecha_valor": fecha_valor
    }

@app.get("/api/tasas")
def get_tasas():
    tz_ve = pytz.timezone("America/Caracas")
    ahora = datetime.now(tz_ve)
    
    if cache["data"] and cache["last_fetched"]:
        if ahora - cache["last_fetched"] < timedelta(minutes=CACHE_TTL_MINUTES):
            return cache["data"]
            
    try:
        resultado = scrapear_bcv()
        resultado["actualizado_en"] = ahora.strftime("%Y-%m-%d %H:%M:%S")
        cache["data"] = resultado
        cache["last_fetched"] = ahora
        return resultado
    except Exception as e:
        if cache["data"]:
            return cache["data"]
        return {
            "error": "Error al consultar el portal del BCV",
            "detalle": str(e),
            "usd": 0.0,
            "eur": 0.0,
            "fecha_valor": "N/D"
        }

@app.get("/")
def home():
    return {"status": "ok", "message": "API de tasas BCV activa. Usa el endpoint /api/tasas"}
