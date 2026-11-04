#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebalanceamento de Portfólio de Tom Cover (Acumulação de BNB)
-------------------------------------------------------------
- Lê os pares e links de `paresXlinks.json`
- Busca a cotação mais recente na API da Binance (com fallback para os arquivos .json locais)
- Pergunta a quantidade atual de cada moeda na carteira (incluindo BNB)
- Armazena o registro com data, hora, saldos, cotações e valor em BNB e BRL (`historico_carteira.json`)
- Calcula o valor total da carteira em BNB e em Reais (BRL)
- Calcula os pesos do Portfólio Constantemente Rebalanceado (CRP), Portfólio Universal de Cover
  e BCRP (Melhor Portfólio Rebalanceado em Retrospectiva)
- Apresenta sugestões detalhadas de COMPRA e VENDA (em quantidade da moeda, em BNB e em R$)
"""

import argparse
import gzip
import hashlib
import hmac
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LINKS_FILE = os.path.join(BASE_DIR, "paresXlinks.json")
KEYS_FILE = os.path.join(BASE_DIR, "keys.json")
HISTORY_FILE = os.path.join(BASE_DIR, "historico_carteira.json")
BINANCE_FEE = 0.001  # 0.10% taxa spot padrão
META_BNB = 256.0  # Meta de acumulação: 256 BNBs (2^8 BNB)


def compute_goal_progress(total_bnb: float, bnb_brl_price: float = 0.0) -> dict:
    """Calcula o progresso atual rumo à meta de 256 BNBs (em %, dobras restantes, próximo degrau e data provável)."""
    if total_bnb <= 0:
        return {
            "meta_bnb": META_BNB,
            "pct": 0.0,
            "dobras_restantes": 10.0,
            "proximo_marco": 0.5,
            "falta_proximo_marco": 0.5,
            "meta_brl": META_BNB * bnb_brl_price,
            "eta_proximo_str": "📅 Data provável (0.5 BNB): aguardando simulação",
            "eta_meta_str": "—",
            "taxa_diaria_pct": 0.0,
        }
    pct = (total_bnb / META_BNB) * 100.0
    dobras_restantes = (
        math.log2(META_BNB / total_bnb) if total_bnb < META_BNB else 0.0
    )
    marcos = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0]
    proximo_marco = META_BNB
    for m in marcos:
        if m > total_bnb * 1.01:
            proximo_marco = m
            break

    # Estima a taxa diária composta a partir do histórico real da carteira de 6 moedas
    history = load_history()
    valid_hist = [
        h
        for h in history
        if isinstance(h, dict)
        and "ZEC" not in h.get("quantidades", {})
        and float(h.get("total_bnb", 0.0)) > 0
        and int(h.get("timestamp", 0)) >= 1793670000
    ]
    if not valid_hist:
        valid_hist = [
            h
            for h in history
            if isinstance(h, dict) and float(h.get("total_bnb", 0.0)) > 0
        ]

    log_r_day = None
    if valid_hist:
        bnb_0 = float(valid_hist[0].get("total_bnb", 0.0))
        ts_0 = int(valid_hist[0].get("timestamp", 0))
        now_ts = int(time.time())
        bnb_end, ts_end = total_bnb, now_ts
        if (ts_end - ts_0 < 3600 or bnb_end <= bnb_0) and len(valid_hist) >= 2:
            last_bnb = float(valid_hist[-1].get("total_bnb", 0.0))
            last_ts = int(valid_hist[-1].get("timestamp", 0))
            if last_bnb > bnb_0 and last_ts > ts_0:
                bnb_end, ts_end = last_bnb, last_ts
        days_elapsed = (ts_end - ts_0) / 86400.0
        if days_elapsed >= 0.05 and bnb_end > bnb_0 > 0:
            log_r_day = math.log(bnb_end / bnb_0) / days_elapsed
            log_r_day = max(0.0002, min(0.02, log_r_day))

    if log_r_day is None:
        log_r_day = math.log(1.0 + 0.0020)  # Ritmo moderado padrão (+0,20%/dia)

    taxa_diaria_pct = (math.exp(log_r_day) - 1.0) * 100.0
    now_dt = datetime.now()
    if proximo_marco > total_bnb:
        dias_prox = math.log(proximo_marco / total_bnb) / log_r_day
        dt_prox = now_dt + timedelta(days=dias_prox)
        eta_proximo_str = (
            f"📅 Data provável ({proximo_marco:g} BNB): "
            f"{dt_prox.strftime('%d/%m/%Y')} (~{int(round(dias_prox))} dias a +{taxa_diaria_pct:.2f}%/d)"
        )
    else:
        eta_proximo_str = "🎉 Meta de 256 BNB alcançada!"

    if META_BNB > total_bnb:
        dias_meta = math.log(META_BNB / total_bnb) / log_r_day
        dt_meta = now_dt + timedelta(days=dias_meta)
        eta_meta_str = f"{dt_meta.strftime('%d/%m/%Y')} (~{int(round(dias_meta))} dias)"
    else:
        eta_meta_str = "Alcançada!"

    return {
        "meta_bnb": META_BNB,
        "pct": pct,
        "dobras_restantes": max(0.0, dobras_restantes),
        "proximo_marco": proximo_marco,
        "falta_proximo_marco": max(0.0, proximo_marco - total_bnb),
        "meta_brl": META_BNB * bnb_brl_price,
        "eta_proximo_str": eta_proximo_str,
        "eta_meta_str": eta_meta_str,
        "taxa_diaria_pct": taxa_diaria_pct,
    }


def load_api_keys(keys_path: str = KEYS_FILE):
    """
    Lê apiKey e secretKey do arquivo keys.json no padrão sugerido pela Binance:
        {
          "apiKey": "...",
          "secretKey": "...",
          "comment": "..."
        }
    (Mantém compatibilidade com variantes de nomes de chave ou lista).
    """
    if not os.path.exists(keys_path):
        return None, None
    try:
        with open(keys_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        if isinstance(data, dict):
            api_key = (
                data.get("apiKey")
                or data.get("API_KEY")
                or data.get("api_key")
                or ""
            ).strip()
            secret_key = (
                data.get("secretKey")
                or data.get("SECRET_KEY")
                or data.get("secret_key")
                or ""
            ).strip()
            if any(
                tok in api_key.upper() or tok in secret_key.upper()
                for tok in ("SUA_", "YOUR_", "EXEMPLO", "EXAMPLE", "AQUI", "HERE")
            ):
                return None, None
            return (api_key or None), (secret_key or None)
        elif isinstance(data, list):
            kv = {}
            for item in data:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    kv[str(item[0]).strip()] = str(item[1]).strip()
            api_key = kv.get("apiKey") or kv.get("API_KEY") or kv.get("api_key")
            secret_key = (
                kv.get("secretKey") or kv.get("SECRET_KEY") or kv.get("secret_key")
            )
            return api_key, secret_key
    except Exception:
        pass
    return None, None


def get_binance_server_time() -> int:
    """Obtém o timestamp oficial do servidor da Binance em ms (evita erro -1021 de relógio local)."""
    for base_url in (
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://www.binance.com",
    ):
        try:
            req = urllib.request.Request(
                f"{base_url}/api/v3/time",
                headers={"User-Agent": "Mozilla/5.0 (CoverPortfolioRebalancer/1.0)"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                if "serverTime" in payload:
                    return int(payload["serverTime"])
        except Exception:
            continue
    return int(time.time() * 1000)


def fetch_spot_balances(coins_order: list, keys_path: str = KEYS_FILE):
    """
    Consulta o saldo real da carteira Spot na Binance usando as chaves (apiKey / secretKey)
    em keys.json via GET /api/v3/account (com fallback para POST /sapi/v3/asset/getUserAsset).
    Retorna (dict_saldos, status_msg, ok_bool).
    """
    api_key, secret_key = load_api_keys(keys_path)
    if not api_key or not secret_key:
        return {}, "Chaves apiKey/secretKey não encontradas em keys.json", False

    ts = get_binance_server_time()
    query_string = f"timestamp={ts}&recvWindow=60000"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "X-MBX-APIKEY": api_key,
        "User-Agent": "Mozilla/5.0 (CoverPortfolioRebalancer/1.0)",
    }

    last_err = ""
    for base_url in (
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ):
        # 1) Endpoint Spot padrão: GET /api/v3/account
        url_acc = f"{base_url}/api/v3/account?{query_string}&signature={signature}"
        try:
            req = urllib.request.Request(url_acc, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                balances_raw = data.get("balances", [])
                spot_map = {}
                for b in balances_raw:
                    asset = str(b.get("asset", "")).upper()
                    free_val = float(b.get("free", 0.0))
                    locked_val = float(b.get("locked", 0.0))
                    spot_map[asset] = free_val + locked_val

                result = {
                    c.upper(): spot_map.get(c.upper(), 0.0) for c in coins_order
                }
                return result, "Saldos Spot carregados via API Binance (keys.json)", True
        except urllib.error.HTTPError as he:
            try:
                err_body = he.read().decode("utf-8", errors="ignore")
                last_err = f"HTTP {he.code}: {err_body}"
            except Exception:
                last_err = f"HTTP {he.code}"
        except Exception as exc:
            last_err = str(exc)

        # 2) Fallback Endpoint Wallet Spot da Binance: POST /sapi/v3/asset/getUserAsset
        url_sapi = (
            f"{base_url}/sapi/v3/asset/getUserAsset?{query_string}&signature={signature}"
        )
        try:
            req_sapi = urllib.request.Request(
                url_sapi, data=b"", headers=headers, method="POST"
            )
            with urllib.request.urlopen(req_sapi, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    spot_map = {}
                    for b in data:
                        asset = str(b.get("asset", "")).upper()
                        free_val = float(b.get("free", 0.0))
                        locked_val = float(b.get("locked", 0.0))
                        spot_map[asset] = free_val + locked_val
                    result = {
                        c.upper(): spot_map.get(c.upper(), 0.0)
                        for c in coins_order
                    }
                    return (
                        result,
                        "Saldos Spot carregados via API Binance (keys.json)",
                        True,
                    )
        except Exception:
            continue

    return {}, f"Não foi possível consultar saldo Spot ({last_err})", False


def find_local_json(symbol: str) -> str:
    """Encontra o arquivo JSON local correspondente ao símbolo (padronizado em MAIÚSCULAS: <SYMBOL>.json)."""
    exact = os.path.join(BASE_DIR, f"{symbol.upper()}.json")
    if os.path.exists(exact):
        return exact
    for fname in os.listdir(BASE_DIR):
        if fname.lower() == f"{symbol.lower()}.json":
            return os.path.join(BASE_DIR, fname)
    return exact


def save_local_klines(symbol: str, data: list) -> str:
    """Grava os candles atualizados no arquivo JSON local (e sincroniza em coverbnb/ se existir)."""
    local_path = find_local_json(symbol)
    tmp_path = f"{local_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fp:
        json.dump(data, fp)
        fp.flush()
        os.fsync(fp.fileno())
    os.replace(tmp_path, local_path)

    # Se existir a subpasta coverbnb/, mantém o JSON lá sincronizado também
    coverbnb_dir = os.path.join(BASE_DIR, "coverbnb")
    if os.path.isdir(coverbnb_dir):
        bname = os.path.basename(local_path)
        cb_path = os.path.join(coverbnb_dir, bname)
        try:
            with open(cb_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp)
        except OSError:
            pass
    return local_path


def normalize_klines_payload(payload) -> list:
    """
    Normaliza a resposta tanto do endpoint OTC/Convert:
      https://www.binance.com/bapi/margin/v1/friendly/new-otc/pair-klines?interval=1d&baseCoin=...&quoteCoin=...
    quanto do endpoint Spot (/api/v3/uiKlines ou /api/v3/klines) para o formato padrão de lista de candles:
      [[open_time_ms, open, high, low, close, volume, close_time_ms, ...], ...]
    """
    raw_list = None
    if isinstance(payload, list):
        raw_list = payload
    elif isinstance(payload, dict):
        data_field = payload.get("data")
        if isinstance(data_field, list):
            raw_list = data_field
        elif isinstance(data_field, dict):
            for key in ("klines", "list", "rows", "candles", "items", "data"):
                if isinstance(data_field.get(key), list):
                    raw_list = data_field[key]
                    break
            if raw_list is None:
                for val in data_field.values():
                    if isinstance(val, list) and len(val) > 0:
                        raw_list = val
                        break
        else:
            for key in ("klines", "list", "rows", "candles"):
                if isinstance(payload.get(key), list):
                    raw_list = payload[key]
                    break

    if not isinstance(raw_list, list) or len(raw_list) == 0:
        return []

    normalized = []
    for row in raw_list:
        try:
            if isinstance(row, (list, tuple)):
                if len(row) >= 5:
                    t = int(float(row[0]))
                    if t < 10**11:
                        t *= 1000
                    c_val = str(row[4])
                    o_val = str(row[1]) if row[1] is not None else c_val
                    h_val = str(row[2]) if row[2] is not None else c_val
                    l_val = str(row[3]) if row[3] is not None else c_val
                    ct = int(float(row[6])) if len(row) > 6 and row[6] is not None else t
                    if ct < 10**11:
                        ct *= 1000
                    normalized.append([t, o_val, h_val, l_val, c_val, "0", ct])
                elif len(row) >= 2:
                    t = int(float(row[0]))
                    if t < 10**11:
                        t *= 1000
                    c_val = str(row[-1])
                    normalized.append([t, c_val, c_val, c_val, c_val, "0", t])
            elif isinstance(row, dict):
                t_raw = (
                    row.get("openTime")
                    or row.get("startTime")
                    or row.get("time")
                    or row.get("timestamp")
                    or row.get("t")
                    or row.get("date")
                    or row.get("closeTime")
                    or row.get("endTime")
                    or row.get("T")
                )
                c_raw = (
                    row.get("close")
                    or row.get("closePrice")
                    or row.get("c")
                    or row.get("price")
                    or row.get("rate")
                    or row.get("value")
                )
                if t_raw is None or c_raw is None:
                    continue
                t = int(float(t_raw))
                if t < 10**11:
                    t *= 1000
                c_val = str(c_raw)
                o_val = str(row.get("open") or row.get("openPrice") or row.get("o") or c_val)
                h_val = str(row.get("high") or row.get("highPrice") or row.get("h") or c_val)
                l_val = str(row.get("low") or row.get("lowPrice") or row.get("l") or c_val)
                ct_raw = row.get("closeTime") or row.get("endTime") or row.get("T") or t
                ct = int(float(ct_raw))
                if ct < 10**11:
                    ct *= 1000
                normalized.append([t, o_val, h_val, l_val, c_val, "0", ct])
        except Exception:
            continue

    normalized.sort(key=lambda item: item[0])
    return normalized


def fetch_latest_pair_price(
    symbol: str, price_url: str = None, reference_close: float = None
):
    """
    Busca o valor mais recente do par a partir do link configurado em paresXlinks.json:
      https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin=BNB&toCoin=XRP
    Alinha automaticamente a orientação (direta vs. inversa 1/x) com base no último fechamento
    dos candles (reference_close), garantindo que <MOEDA>BNB esteja sempre em BNB por 1 MOEDA
    e BNBBRL esteja em BRL por 1 BNB.
    """
    sym_up = symbol.upper()
    urls = []
    if price_url:
        urls.append(price_url)

    if sym_up.endswith("BNB") and len(sym_up) > 3:
        coin = sym_up[:-3]
        u1 = f"https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin=BNB&toCoin={coin}"
        u2 = f"https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin={coin}&toCoin=BNB"
        for u in (u1, u2):
            if u not in urls:
                urls.append(u)
    elif sym_up.endswith("BRL") and len(sym_up) > 3:
        coin = sym_up[:-3]
        u1 = f"https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin={coin}&toCoin=BRL"
        u2 = f"https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin=BRL&toCoin={coin}"
        for u in (u1, u2):
            if u not in urls:
                urls.append(u)

    urls.append(f"https://api.binance.com/api/v3/ticker/price?symbol={sym_up}")

    def _orient_price(candidates: list, url_used: str):
        valid = [c for c in candidates if c is not None and c > 0]
        if not valid:
            return None
        if reference_close and reference_close > 0:
            best_val = None
            best_dist = float("inf")
            for c in valid:
                for cand in (c, 1.0 / c):
                    dist = abs(math.log(cand / reference_close))
                    if dist < best_dist:
                        best_dist = dist
                        best_val = cand
            if best_val is not None and best_dist < math.log(5.0):
                return best_val
        # Caso não haja reference_close, orienta pelos parâmetros fromCoin/toCoin
        raw = valid[0]
        if sym_up.endswith("BNB") and "fromCoin=BNB" in url_used and raw > 0:
            return 1.0 / raw
        return raw

    priority_keys = (
        "inversePrice",
        "price",
        "lastPrice",
        "closePrice",
        "close",
        "exchangeRate",
        "rate",
        "toCoinAmount",
        "quotation",
        "value",
    )
    skip_tokens = ("change", "percent", "pct", "time", "date", "code", "24h", "vol", "high", "low", "open")

    for candidate_url in urls:
        try:
            req = urllib.request.Request(
                candidate_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                },
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                raw_bytes = resp.read()
                if raw_bytes[:2] == b"\x1f\x8b":
                    raw_bytes = gzip.decompress(raw_bytes)
                payload = json.loads(raw_bytes.decode("utf-8"))

                data = payload.get("data", payload) if isinstance(payload, dict) else payload
                candidates = []
                if isinstance(data, (int, float, str)):
                    try:
                        candidates.append(float(data))
                    except ValueError:
                        pass
                elif isinstance(data, dict):
                    for k in priority_keys:
                        if k in data and data[k] is not None:
                            try:
                                candidates.append(float(data[k]))
                            except (ValueError, TypeError):
                                pass
                    for k, v in data.items():
                        kl = str(k).lower()
                        if any(tok in kl for tok in skip_tokens):
                            continue
                        if isinstance(v, (int, float, str)):
                            try:
                                candidates.append(float(v))
                            except (ValueError, TypeError):
                                pass

                oriented = _orient_price(candidates, candidate_url)
                if oriented is not None and oriented > 0:
                    return oriented
        except Exception:
            continue
    return None


def fetch_klines(
    symbol: str,
    url: str,
    offline: bool = False,
    update_local: bool = True,
    price_url: str = None,
):
    """
    1) Busca os candles mais recentes na Binance a partir do link de paresXlinks.json
       (suportando tanto o endpoint OTC /bapi/margin/v1/friendly/new-otc/pair-klines quanto /api/v3/uiKlines).
    2) Busca o preço mais recente do par via new-otc/pair-price-change (price_url) e atualiza o fechamento atual.
    3) Atualiza o arquivo .json local correspondente no disco.
    4) Lê e retorna os candles a partir do arquivo .json local atualizado.
    """
    local_path = find_local_json(symbol)
    urls_to_try = [url]

    # Caso symbol seja de 6+ letras terminando em BNB ou BRL, garante também o link new-otc/pair-klines
    sym_up = symbol.upper()
    if sym_up.endswith("BNB") and len(sym_up) > 3:
        base_c, quote_c = sym_up[:-3], "BNB"
        otc_url = f"https://www.binance.com/bapi/margin/v1/friendly/new-otc/pair-klines?interval=1d&baseCoin={base_c}&quoteCoin={quote_c}"
        if otc_url not in urls_to_try:
            urls_to_try.insert(0, otc_url)
    elif sym_up.endswith("BRL") and len(sym_up) > 3:
        base_c, quote_c = sym_up[:-3], "BRL"
        otc_url = f"https://www.binance.com/bapi/margin/v1/friendly/new-otc/pair-klines?interval=1d&baseCoin={base_c}&quoteCoin={quote_c}"
        if otc_url not in urls_to_try:
            urls_to_try.insert(0, otc_url)

    # Fallbacks Spot públicos da Binance (caso o par seja fiduciário como BNBBRL e não exista no OTC)
    for host in (
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://www.binance.com",
    ):
        for ep in ("/api/v3/uiKlines", "/api/v3/klines"):
            candidate = f"{host}{ep}?symbol={sym_up}&interval=1d&limit=1000"
            if candidate not in urls_to_try:
                urls_to_try.append(candidate)

    updated_online = False
    price_updated_online = False
    if not offline:
        for candidate_url in urls_to_try:
            try:
                req = urllib.request.Request(
                    candidate_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
                        "Accept": "application/json, text/plain, */*",
                    },
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    raw_bytes = resp.read()
                    if raw_bytes[:2] == b"\x1f\x8b":
                        raw_bytes = gzip.decompress(raw_bytes)
                    payload = json.loads(raw_bytes.decode("utf-8"))
                    data = normalize_klines_payload(payload)
                    if len(data) > 0:
                        ref_close = float(data[-1][4])
                        latest_p = fetch_latest_pair_price(
                            symbol, price_url=price_url, reference_close=ref_close
                        )
                        if latest_p is not None and latest_p > 0:
                            data[-1][4] = f"{latest_p:.8f}" if latest_p < 100 else f"{latest_p:.2f}"
                            data[-1][6] = int(time.time() * 1000)
                            price_updated_online = True
                        if update_local:
                            try:
                                local_path = save_local_klines(symbol, data)
                                updated_online = True
                            except OSError:
                                pass
                        if not os.path.exists(local_path):
                            return data, "ONLINE (Binance API)"
                        break
            except Exception:
                continue

    # Lê sempre a partir do arquivo JSON local (já atualizado quando online)
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as fp:
            raw_local = json.load(fp)
        data = normalize_klines_payload(raw_local)
        if not offline and not price_updated_online and len(data) > 0:
            ref_close = float(data[-1][4])
            latest_p = fetch_latest_pair_price(
                symbol, price_url=price_url, reference_close=ref_close
            )
            if latest_p is not None and latest_p > 0:
                data[-1][4] = f"{latest_p:.8f}" if latest_p < 100 else f"{latest_p:.2f}"
                data[-1][6] = int(time.time() * 1000)
                price_updated_online = True
                if update_local:
                    try:
                        save_local_klines(symbol, data)
                    except OSError:
                        pass
        bname = os.path.basename(local_path)
        if updated_online and price_updated_online:
            return data, f"ONLINE -> {bname} + cotação atualizada"
        if updated_online:
            return data, f"ONLINE -> {bname} atualizado"
        if price_updated_online:
            return data, f"LOCAL ({bname}) + cotação ONLINE"
        return data, f"LOCAL ({bname})"

    raise RuntimeError(f"Não foi possível obter dados para {symbol} (nem online, nem em {local_path}).")


def parse_close_series(klines: list) -> dict:
    """Retorna dicionário {timestamp_ms: close_price} e o último preço de fechamento."""
    norm = normalize_klines_payload(klines) if not isinstance(klines, list) or (klines and isinstance(klines[0], dict)) else klines
    series = {}
    for row in norm:
        t = int(row[0])
        c = float(row[4])
        series[t] = c
    last_close = float(norm[-1][4])
    last_time_ms = int(norm[-1][6]) if len(norm[-1]) > 6 else int(norm[-1][0])
    return series, last_close, last_time_ms


def dot(a: list, b: list) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_bcrp_weights(relatives: list, iters: int = 400) -> list:
    """
    Calcula o BCRP (Best Constant Rebalanced Portfolio) de Tom Cover
    usando Exponentiated Gradient / Ponto Fixo acelerado no simplex:
        b_j^{(k+1)} proportional to b_j^{(k)} * (grad_j)^eta
    """
    m = len(relatives[0])
    T = len(relatives)
    if T == 0:
        return [1.0 / m] * m
    b = [1.0 / m] * m
    eta = 25.0
    for _ in range(iters):
        grad = [0.0] * m
        for x in relatives:
            bx = dot(b, x)
            if bx > 0:
                for j in range(m):
                    grad[j] += x[j] / (bx * T)
        b_next = [b[j] * (max(grad[j], 1e-12) ** eta) for j in range(m)]
        s = sum(b_next)
        if s <= 0:
            break
        diff = sum(abs(b_next[j] / s - b[j]) for j in range(m))
        b = [v / s for v in b_next]
        if diff < 1e-9:
            break
    return b


def compute_universal_weights(relatives: list, num_experts: int = 4000) -> list:
    """
    Calcula os pesos atuais do Portfólio Universal de Tom Cover (prior Dirichlet(1/2)).
    Usa gerador determinístico para reprodutibilidade exata.
    """
    import random

    rng = random.Random(1991)  # 1991 = ano do artigo Universal Portfolios de Tom Cover
    m = len(relatives[0])
    if len(relatives) == 0:
        return [1.0 / m] * m

    experts = []
    for _ in range(num_experts):
        raw = [rng.gammavariate(0.5, 1.0) for _ in range(m)]
        s = sum(raw)
        experts.append([v / s for v in raw])

    # Inclui também os vértices e o centro (CRP pesos iguais)
    experts.append([1.0 / m] * m)
    for j in range(m):
        e = [0.0] * m
        e[j] = 1.0
        experts.append(e)

    wealths = [1.0] * len(experts)
    for x in relatives:
        for k, b in enumerate(experts):
            wealths[k] *= dot(b, x)

    total_w = sum(wealths)
    if total_w <= 0:
        return [1.0 / m] * m
    b_univ = [
        sum(wealths[k] * experts[k][j] for k in range(len(experts))) / total_w
        for j in range(m)
    ]
    return b_univ


def load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def save_history_entry(entry: dict):
    history = load_history()
    history.append(entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as fp:
        json.dump(history, fp, indent=2, ensure_ascii=False)


def prompt_float(prompt_text: str, default_val: float) -> float:
    while True:
        try:
            raw = input(f"{prompt_text} [{default_val:g}]: ").strip()
        except EOFError:
            return default_val
        if raw == "":
            return default_val
        raw_clean = raw.replace(",", ".")
        try:
            val = float(raw_clean)
            if val < 0:
                print("  [!] Digite um valor maior ou igual a zero.")
                continue
            return val
        except ValueError:
            print("  [!] Valor inválido. Digite um número (ex: 12.5 ou 0).")


def format_brl(val: float) -> str:
    """Formata float no padrão R$ 1.234,56."""
    s = f"{val:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def main():
    parser = argparse.ArgumentParser(
        description="Rebalanceador de Carteira Tom Cover (Foco em Acumular BNB)"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Abre a interface gráfica (PyQt5)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Usa apenas os arquivos .json locais sem consultar a internet",
    )
    parser.add_argument(
        "--atualizar-json",
        action="store_true",
        help="Apenas busca os candles da Binance, atualiza os arquivos .json locais e encerra",
    )
    parser.add_argument(
        "--estrategia",
        choices=["crp", "universal", "bcrp"],
        default=None,
        help="Estratégia alvo para sugestões: 'crp' (Pesos Iguais), 'universal' (Cover Universal) ou 'bcrp' (Ótimo Histórico)",
    )
    parser.add_argument(
        "--apenas-ativas",
        action="store_true",
        help="Rebalanceia apenas entre as moedas que possuem saldo > 0 (mais BNB)",
    )
    parser.add_argument(
        "--saldos",
        type=str,
        default=None,
        help="Passa saldos via linha de comando em formato JSON ou 'BNB=1,XRP=100,TRX=500'",
    )
    parser.add_argument(
        "--limiar",
        type=float,
        default=1.0,
        help="Desvio mínimo (em %% do portfólio) para sugerir ordem de compra/venda (padrão: 1.0%%)",
    )
    args = parser.parse_args()
    if args.gui:
        import rebalanceamento_cover_gui
        rebalanceamento_cover_gui.main()
        return

    if not os.path.exists(LINKS_FILE):
        print(f"Erro: Arquivo {LINKS_FILE} não encontrado.", file=sys.stderr)
        sys.exit(1)

    with open(LINKS_FILE, "r", encoding="utf-8") as fp:
        pairs_links = json.load(fp)

    print("=" * 78)
    print("  REBALANCEADOR DE PORTFÓLIO DE TOM COVER — OBJETIVO: ACUMULAR BNB")
    print("=" * 78)
    print(
        "\n[1/4] Buscando candles (paresXlinks.json) e atualizando arquivos JSON locais..."
        if not args.offline
        else "\n[1/4] Carregando candles dos arquivos JSON locais (modo offline)..."
    )

    coin_Data = {}
    bnb_brl_price = None
    bnb_brl_source = ""

    for item in pairs_links:
        symbol, url = item[0].strip().upper(), item[1].strip()
        price_url = item[2].strip() if len(item) > 2 else None
        klines, source = fetch_klines(
            symbol, url, offline=args.offline, price_url=price_url
        )
        series, last_close, last_time_ms = parse_close_series(klines)
        dt_str = datetime.fromtimestamp(last_time_ms / 1000.0).strftime("%Y-%m-%d %H:%M")

        if symbol == "BNBBRL":
            bnb_brl_price = last_close
            bnb_brl_source = source
            print(f"  • {symbol:8s}: {format_brl(last_close):>14s} | Candle: {dt_str} | Fonte: {source}")
        elif symbol.endswith("BNB"):
            coin = symbol[:-3]
            coin_Data[coin] = {
                "symbol": symbol,
                "price_bnb": last_close,
                "series": series,
                "last_time": dt_str,
                "source": source,
            }
            print(f"  • {symbol:8s}: {last_close:14.8f} BNB | Candle: {dt_str} | Fonte: {source}")

    if args.atualizar_json:
        print("\n✓ Todos os arquivos JSON locais de candles foram atualizados com sucesso!")
        return

    if bnb_brl_price is None:
        raise RuntimeError("Par BNBBRL não encontrado em paresXlinks.json.")

    coins_order = ["BNB"] + [
        item[0].strip().upper()[:-3]
        for item in pairs_links
        if item[0].strip().upper().endswith("BNB")
    ]

    # Tenta buscar o saldo real na carteira Spot da Binance via keys.json
    spot_holdings, spot_msg, spot_ok = ({}, "", False)
    if not args.offline:
        spot_holdings, spot_msg, spot_ok = fetch_spot_balances(coins_order)
        if spot_ok:
            print(f"\n  ✓ {spot_msg}")

    # Carrega último saldo salvo para usar como sugestão padrão caso a API não esteja disponível
    history = load_history()
    last_holdings = {}
    if history:
        last_holdings = history[-1].get("quantidades", {})
        last_dt = history[-1].get("data_hora", "desconhecida")
        print(f"\n  (Último registro encontrado em {last_dt})")
    if spot_ok:
        last_holdings = spot_holdings

    # Obter quantidades atuais
    holdings = {}
    if args.saldos:
        raw_s = args.saldos.strip()
        if raw_s.startswith("{"):
            parsed = json.loads(raw_s)
            for c in coins_order:
                holdings[c] = float(parsed.get(c, 0.0))
        else:
            parsed = {}
            for kv in raw_s.split(","):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    parsed[k.strip().upper()] = float(v.strip())
            for c in coins_order:
                holdings[c] = float(parsed.get(c, 0.0))
    else:
        print("\n[2/4] Informe a quantidade atual de cada moeda na sua carteira")
        print("      (Pressione ENTER para manter o valor entre colchetes):")
        for c in coins_order:
            default_q = float(last_holdings.get(c, 0.0))
            if c == "BNB":
                holdings[c] = prompt_float(f"  Quantidade de {c:4s} (Moeda base)", default_q)
            else:
                p_bnb = coin_Data[c]["price_bnb"]
                p_brl = p_bnb * bnb_brl_price
                holdings[c] = prompt_float(
                    f"  Quantidade de {c:4s} (1 {c} = {p_bnb:.6f} BNB / {format_brl(p_brl)})",
                    default_q,
                )

    # Pergunta modo de universo e estratégia se interativo e não especificado via flag
    only_active = args.apenas_ativas
    strategy_choice = args.estrategia
    if not args.saldos and strategy_choice is None:
        print("\n[3/4] Configuração do Rebalanceamento de Tom Cover:")
        print("  Qual variante de pesos de Tom Cover deseja usar para as sugestões?")
        print("    [1] CRP Pesos Iguais (1/N em cada ativo — clássico contra volatilidade)")
        print("    [2] Portfólio Universal de Cover (pesos adaptativos via histórico)")
        print("    [3] BCRP Histórico (pesos que maximizaram o crescimento passado em BNB)")
        try:
            opt = input("  Escolha [1/2/3] (Padrão = 1): ").strip()
        except EOFError:
            opt = "1"
        if opt == "2":
            strategy_choice = "universal"
        elif opt == "3":
            strategy_choice = "bcrp"
        else:
            strategy_choice = "crp"

        inactive_coins = [c for c in coins_order if c != "BNB" and holdings.get(c, 0.0) <= 0]
        if inactive_coins and len(inactive_coins) < len(coins_order) - 1:
            try:
                ans = input(
                    f"  Incluir também moedas atualmente zeradas ({', '.join(inactive_coins)}) no rebalanceamento? [S/n]: "
                ).strip().lower()
            except EOFError:
                ans = "s"
            if ans in ("n", "nao", "não", "no"):
                only_active = True
    elif strategy_choice is None:
        strategy_choice = "crp"

    # Calcula valor atual de cada posição em BNB e BRL
    now_dt = datetime.now().astimezone()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S %z")

    positions = {}
    total_bnb = 0.0
    for c in coins_order:
        qty = holdings.get(c, 0.0)
        price_bnb = 1.0 if c == "BNB" else coin_Data[c]["price_bnb"]
        val_bnb = qty * price_bnb
        val_brl = val_bnb * bnb_brl_price
        total_bnb += val_bnb
        positions[c] = {
            "quantidade": qty,
            "preco_bnb": price_bnb,
            "preco_brl": price_bnb * bnb_brl_price,
            "valor_bnb": val_bnb,
            "valor_brl": val_brl,
        }

    total_brl = total_bnb * bnb_brl_price
    for c in coins_order:
        positions[c]["peso_atual"] = (
            positions[c]["valor_bnb"] / total_bnb if total_bnb > 0 else 0.0
        )

    # Determina subconjunto de moedas participantes do rebalanceamento
    if only_active:
        active_universe = [
            c for c in coins_order if c == "BNB" or holdings.get(c, 0.0) > 0
        ]
        if len(active_universe) < 2:
            active_universe = list(coins_order)
    else:
        active_universe = list(coins_order)

    # Calcula retornos relativos históricos para os ativos que possuem série temporal comum recente
    # (Para moedas com janela mais antiga como DOGEBNB/ZECBNB, usa estatística marginal ou série comum disponível)
    non_bnb_active = [c for c in active_universe if c != "BNB"]
    # Seleciona os pares que têm dados recentes sobrepostos (ou o maior subconjunto com >= 100 dias em comum)
    common_timestamps = None
    modern_coins = []
    for c in non_bnb_active:
        ts_set = set(coin_Data[c]["series"].keys())
        # Verifica se compartilha datas com o último candle
        if common_timestamps is None:
            common_timestamps = ts_set
            modern_coins.append(c)
        else:
            inter = common_timestamps.intersection(ts_set)
            if len(inter) >= 100:
                common_timestamps = inter
                modern_coins.append(c)

    # Monta matriz de preços relativos para o universo ativo
    # Para ativos fora da janela comum (ex: DOGE/ZEC de anos anteriores), alinha pelo índice final dos últimos N candles
    all_lengths = [len(coin_Data[c]["series"]) for c in non_bnb_active]
    window_len = min(all_lengths) if all_lengths else 0
    relatives_matrix = []
    if window_len >= 2:
        sorted_prices = {}
        for c in non_bnb_active:
            s_dict = coin_Data[c]["series"]
            times_sorted = sorted(s_dict.keys())[-window_len:]
            sorted_prices[c] = [s_dict[t] for t in times_sorted]
        for t in range(1, window_len):
            row = []
            for c in active_universe:
                if c == "BNB":
                    row.append(1.0)
                else:
                    row.append(sorted_prices[c][t] / sorted_prices[c][t - 1])
            relatives_matrix.append(row)

    m_active = len(active_universe)
    weights_crp_active = [1.0 / m_active] * m_active
    weights_univ_active = compute_universal_weights(relatives_matrix)
    weights_bcrp_active = compute_bcrp_weights(relatives_matrix)

    # Mapeia para todas as moedas em coins_order
    def expand_weights(w_sub: list) -> dict:
        out = {c: 0.0 for c in coins_order}
        for c, w in zip(active_universe, w_sub):
            out[c] = w
        return out

    w_crp = expand_weights(weights_crp_active)
    w_univ = expand_weights(weights_univ_active)
    w_bcrp = expand_weights(weights_bcrp_active)

    if strategy_choice == "universal":
        target_weights = w_univ
        strategy_label = "Portfólio Universal de Cover (Dirichlet 1/2)"
    elif strategy_choice == "bcrp":
        target_weights = w_bcrp
        strategy_label = "BCRP (Melhor Portfólio Rebalanceado Histórico)"
    else:
        target_weights = w_crp
        strategy_label = f"CRP Pesos Iguais (1/{m_active} = {100.0/m_active:.2f}% por ativo)"

    # Gera sugestões de COMPRA e VENDA
    suggestions = []
    min_drift_frac = args.limiar / 100.0
    for c in coins_order:
        w_cur = positions[c]["peso_atual"]
        w_tgt = target_weights[c]
        target_bnb = total_bnb * w_tgt
        diff_bnb = target_bnb - positions[c]["valor_bnb"]
        diff_brl = diff_bnb * bnb_brl_price
        price_bnb = positions[c]["preco_bnb"]
        diff_qty = diff_bnb / price_bnb if price_bnb > 0 else 0.0

        if total_bnb <= 0 or abs(w_tgt - w_cur) < min_drift_frac:
            acao = "MANTER"
        elif diff_bnb > 0:
            acao = "COMPRAR" if c != "BNB" else "ACUMULAR (Caixa BNB)"
        else:
            acao = "VENDER" if c != "BNB" else "USAR BNB P/ COMPRAS"

        suggestions.append(
            {
                "moeda": c,
                "acao": acao,
                "peso_atual_pct": round(w_cur * 100, 2),
                "peso_alvo_pct": round(w_tgt * 100, 2),
                "desvio_pct": round((w_cur - w_tgt) * 100, 2),
                "qtd_atual": positions[c]["quantidade"],
                "qtd_alvo": target_bnb / price_bnb if price_bnb > 0 else 0.0,
                "delta_qtd": diff_qty,
                "delta_bnb": diff_bnb,
                "delta_brl": diff_brl,
            }
        )

    # Apresentação do Relatório
    print("\n" + "=" * 78)
    print(f"  RELATÓRIO DA CARTEIRA — {now_str}")
    print("=" * 78)
    print(f"  Cotação BNBBRL de referência : {format_brl(bnb_brl_price)} ({bnb_brl_source})")
    print(f"  VALOR TOTAL EM BNB           : {total_bnb:.8f} BNB")
    print(f"  VALOR TOTAL EM REAIS (BRL)   : {format_brl(total_brl)}")
    goal_info = compute_goal_progress(total_bnb, bnb_brl_price)
    print(
        f"  META DE ACUMULAÇÃO (256 BNB) : {goal_info['pct']:.4f}% concluído "
        f"| Faltam {goal_info['dobras_restantes']:.2f} dobras "
        f"| Próx. marco: {goal_info['proximo_marco']:g} BNB (faltam +{goal_info['falta_proximo_marco']:.6f} BNB)"
    )

    if history:
        first_entry = history[0]
        prev_entry = history[-1]
        prev_bnb = float(prev_entry.get("total_bnb", 0.0))
        first_bnb = float(first_entry.get("total_bnb", 0.0))
        if prev_bnb > 0:
            diff_last = total_bnb - prev_bnb
            pct_last = (total_bnb / prev_bnb - 1.0) * 100.0
            print(
                f"  Evolução vs. último registro : {diff_last:+.8f} BNB ({pct_last:+.2f}%) desde {prev_entry.get('data_hora')}"
            )
        if len(history) > 1 and first_bnb > 0:
            diff_first = total_bnb - first_bnb
            pct_first = (total_bnb / first_bnb - 1.0) * 100.0
            print(
                f"  Evolução desde 1º registro   : {diff_first:+.8f} BNB ({pct_first:+.2f}%) desde {first_entry.get('data_hora')}"
            )

    print("\n--- POSIÇÃO ATUAL DETALHADA ---")
    print(
        f"{'Ativo':6s} | {'Quantidade':>14s} | {'Preço (BNB)':>14s} | {'Valor (BNB)':>14s} | {'Valor (R$)':>15s} | {'Peso Atual':>10s}"
    )
    print("-" * 88)
    for c in coins_order:
        p = positions[c]
        print(
            f"{c:6s} | {p['quantidade']:14.6f} | {p['preco_bnb']:14.8f} | {p['valor_bnb']:14.8f} | {format_brl(p['valor_brl']):>15s} | {p['peso_atual']*100:9.2f}%"
        )
    print("-" * 88)
    print(
        f"{'TOTAL':6s} | {'':>14s} | {'':>14s} | {total_bnb:14.8f} | {format_brl(total_brl):>15s} | {'100.00%':>10s}"
    )

    print("\n--- COMPARATIVO DE PESOS ALVO DE TOM COVER ---")
    print(
        f"{'Ativo':6s} | {'Peso Atual':>10s} | {'CRP (Iguais)':>13s} | {'Universal (Cover)':>17s} | {'BCRP (Ótimo Hist.)':>18s}"
    )
    print("-" * 76)
    for c in coins_order:
        print(
            f"{c:6s} | {positions[c]['peso_atual']*100:9.2f}% | {w_crp[c]*100:12.2f}% | {w_univ[c]*100:16.2f}% | {w_bcrp[c]*100:17.2f}%"
        )

    print(f"\n--- SUGESTÕES DE REBALANCEAMENTO ({strategy_label}) ---")
    if total_bnb <= 0:
        print("  [!] Carteira com saldo total zero. Adicione quantidades para gerar ordens de compra e venda.")
    else:
        print(
            f"{'Ativo':6s} | {'Ação Sugerida':20s} | {'Atual -> Alvo':15s} | {'Qtd a Negociar':>16s} | {'Valor (BNB)':>14s} | {'Valor (R$)':>14s}"
        )
        print("-" * 98)
        sells = [s for s in suggestions if s["delta_bnb"] < 0 and s["acao"] != "MANTER"]
        buys = [s for s in suggestions if s["delta_bnb"] > 0 and s["acao"] != "MANTER"]
        holds = [s for s in suggestions if s["acao"] == "MANTER"]

        for s in sells + buys + holds:
            c = s["moeda"]
            weights_str = f"{s['peso_atual_pct']:5.1f}% -> {s['peso_alvo_pct']:5.1f}%"
            print(
                f"{c:6s} | {s['acao']:20s} | {weights_str:15s} | {s['delta_qtd']:+16.6f} | {s['delta_bnb']:+14.8f} | {format_brl(abs(s['delta_brl'])):>14s}"
            )

        # Resumo prático de execução de ordens nos pares <MOEDA>BNB
        coin_sells = [s for s in sells if s["moeda"] != "BNB"]
        coin_buys = [s for s in buys if s["moeda"] != "BNB"]
        turnover_bnb = sum(abs(s["delta_bnb"]) for s in coin_sells + coin_buys) / 2.0
        est_fee_bnb = sum(abs(s["delta_bnb"]) for s in coin_sells + coin_buys) * BINANCE_FEE

        print("\n--- PASSO A PASSO DE ORDENS NA BINANCE (PARES CONTRA BNB) ---")
        if not coin_sells and not coin_buys:
            print(
                f"  ✓ Sua carteira já está equilibrada dentro do limiar de {args.limiar:.1f}%. Nenhuma ordem necessária hoje!"
            )
        else:
            step_n = 1
            if coin_sells:
                print("  1º) Execute as VENDAS (realizando lucro das moedas que subiram para BNB):")
                for s in coin_sells:
                    c = s["moeda"]
                    print(
                        f"      {step_n}. VENDER {abs(s['delta_qtd']):.6f} {c} no par {c}BNB  -->  Recebe +{abs(s['delta_bnb']):.8f} BNB ({format_brl(abs(s['delta_brl']))})"
                    )
                    step_n += 1
            if coin_buys:
                print("  2º) Execute as COMPRAS (comprando na baixa com BNB):")
                for s in coin_buys:
                    c = s["moeda"]
                    print(
                        f"      {step_n}. COMPRAR {abs(s['delta_qtd']):.6f} {c} no par {c}BNB  -->  Usa {abs(s['delta_bnb']):.8f} BNB ({format_brl(abs(s['delta_brl']))})"
                    )
                    step_n += 1
            bnb_sug = next(s for s in suggestions if s["moeda"] == "BNB")
            print(
                f"\n  • Saldo de BNB reserva após rebalancear : {bnb_sug['qtd_alvo']:.8f} BNB ({format_brl(bnb_sug['qtd_alvo'] * bnb_brl_price)})"
            )
            print(
                f"  • Taxa estimada da Binance (0,10%)      : ~{est_fee_bnb:.8f} BNB ({format_brl(est_fee_bnb * bnb_brl_price)})"
            )

    # Salva registro no histórico com dia e hora
    entry = {
        "data_hora": now_str,
        "timestamp": int(now_dt.timestamp()),
        "estrategia": strategy_choice,
        "cotacao_bnb_brl": bnb_brl_price,
        "total_bnb": round(total_bnb, 8),
        "total_brl": round(total_brl, 2),
        "quantidades": {c: positions[c]["quantidade"] for c in coins_order},
        "precos_bnb": {c: positions[c]["preco_bnb"] for c in coins_order},
        "valores_bnb": {c: round(positions[c]["valor_bnb"], 8) for c in coins_order},
        "valores_brl": {c: round(positions[c]["valor_brl"], 2) for c in coins_order},
        "pesos_atuais": {c: round(positions[c]["peso_atual"], 6) for c in coins_order},
        "pesos_alvo": {c: round(target_weights[c], 6) for c in coins_order},
        "sugestoes": suggestions,
    }
    save_history_entry(entry)
    print(f"\n[4/4] Registro salvo com data e hora em: {HISTORY_FILE}")
    print("=" * 78)


if __name__ == "__main__":
    main()
