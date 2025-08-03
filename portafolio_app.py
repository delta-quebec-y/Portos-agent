
import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Análisis de Portafolio", layout="wide")

# Título
st.title("📊 Agente de Análisis de Portafolio de Inversión")

# Instrucciones
st.markdown("Ingresa los **tickers** de las acciones y la **proporción** que representan en tu portafolio. El agente obtendrá datos de mercado desde Alpha Vantage y calculará métricas de riesgo como Sharpe y Sortino ratios.")

# Entrada de datos
tickers_input = st.text_input("Tickers separados por coma (ej. AAPL, MSFT, GOOGL)", "AAPL, MSFT")
weights_input = st.text_input("Proporciones separadas por coma (ej. 0.5, 0.5)", "0.5, 0.5")

# API Key de Alpha Vantage
api_key = st.text_input("🔑 Ingresa tu API Key de Alpha Vantage", type="password")

# Función para obtener precios históricos
@st.cache_data
def get_prices(ticker, api_key):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={ticker}&outputsize=full&apikey={api_key}"
    r = requests.get(url)
    data = r.json()
    try:
        prices = data["Time Series (Daily)"]
        df = pd.DataFrame(prices).T
        df = df.rename(columns={"5. adjusted close": "Adj Close"})
        df["Adj Close"] = df["Adj Close"].astype(float)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        return df[["Adj Close"]]
    except:
        return pd.DataFrame()

# Procesamiento
if st.button("📈 Analizar Portafolio"):
    tickers = [t.strip().upper() for t in tickers_input.split(",")]
    weights = [float(w.strip()) for w in weights_input.split(",")]

    if len(tickers) != len(weights):
        st.error("El número de tickers debe coincidir con el número de proporciones.")
    elif abs(sum(weights) - 1.0) > 0.01:
        st.error("Las proporciones deben sumar 1.0")
    elif not api_key:
        st.error("Debes ingresar tu API Key de Alpha Vantage.")
    else:
        st.success("Datos válidos. Obteniendo precios históricos...")

        price_data = {}
        for ticker in tickers:
            df = get_prices(ticker, api_key)
            if df.empty:
                st.warning(f"No se pudo obtener datos para {ticker}")
            else:
                price_data[ticker] = df

        if len(price_data) == 0:
            st.error("No se pudo obtener datos de ningún ticker.")
        else:
            # Unir precios
            combined_df = pd.concat(price_data.values(), axis=1)
            combined_df.columns = list(price_data.keys())
            combined_df = combined_df.dropna()

            # Calcular retornos diarios
            returns = combined_df.pct_change().dropna()

            # Retorno del portafolio
            weights_array = np.array(weights)
            portfolio_returns = returns.dot(weights_array)

            # Métricas
            avg_return = np.mean(portfolio_returns) * 252
            volatility = np.std(portfolio_returns) * np.sqrt(252)
            downside_returns = portfolio_returns[portfolio_returns < 0]
            downside_std = np.std(downside_returns) * np.sqrt(252)
            risk_free_rate = 0.02

            sharpe_ratio = (avg_return - risk_free_rate) / volatility if volatility != 0 else np.nan
            sortino_ratio = (avg_return - risk_free_rate) / downside_std if downside_std != 0 else np.nan

            # Resultados
            st.subheader("📊 Métricas del Portafolio")
            st.metric("Retorno anualizado", f"{avg_return:.2%}")
            st.metric("Volatilidad anualizada", f"{volatility:.2%}")
            st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")
            st.metric("Sortino Ratio", f"{sortino_ratio:.2f}")

            # Gráfico de retornos acumulados
            cumulative_returns = (1 + portfolio_returns).cumprod()
            st.line_chart(cumulative_returns, use_container_width=True)

            # Recomendación básica
            st.subheader("🧠 Recomendación")
            if sharpe_ratio > 1 and sortino_ratio > 1:
                st.success("El portafolio muestra un buen rendimiento ajustado por riesgo. Puedes considerar mantener la composición actual.")
            elif sharpe_ratio < 0.5 or sortino_ratio < 0.5:
                st.warning("El portafolio tiene bajo rendimiento ajustado por riesgo. Considera revisar la composición y diversificar.")
            else:
                st.info("El portafolio tiene rendimiento moderado. Puedes optimizarlo según tu horizonte de inversión.")
