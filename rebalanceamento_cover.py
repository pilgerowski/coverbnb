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
import hashlib
import hmac
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LINKS_FILE = os.path.join(BASE_DIR, "paresXlinks.json")
KEYS_FILE = os.path.join(BASE_DIR, "keys.json")
HISTORY_FILE = os.path.join(BASE_DIR, "historico_carteira.json")
BINANCE_FEE = 0.001  # 0.10% taxa spot padrão


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
    """Encontra o arquivo JSON local correspondente ao símbolo (case-insensitive)."""
    exact = os.path.join(BASE_DIR, f"{symbol}.json")
    if os.path.exists(exact):
        return exact
    lower = os.path.join(BASE_DIR, f"{symbol.lower()}.json")
    if os.path.exists(lower):
        return lower
    for fname in os.listdir(BASE_DIR):
        if fname.lower() == f"{symbol.lower()}.json":
            return os.path.join(BASE_DIR, fname)
    return exact


def fetch_klines(symbol: str, url: str, offline: bool = False, update_local: bool = True):
    """
    Busca os candles mais recentes a partir do link de paresXlinks.json.
    Se a URL falhar (ex: sem internet ou erro no endpoint), faz fallback para o arquivo JSON local.
    """
    local_path = find_local_json(symbol)
    urls_to_try = [url]
    # Caso a URL tenha '/api/v3/aor/uiKlines', tenta também '/api/v3/uiKlines'
    if "/api/v3/aor/uiKlines" in url:
        urls_to_try.append(url.replace("/api/v3/aor/uiKlines", "/api/v3/uiKlines"))

    if not offline:
        for candidate_url in urls_to_try:
            try:
                req = urllib.request.Request(
                    candidate_url,
                    headers={"User-Agent": "Mozilla/5.0 (CoverPortfolioRebalancer/1.0)"},
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    raw_bytes = resp.read()
                    data = json.loads(raw_bytes.decode("utf-8"))
                    if isinstance(data, list) and len(data) > 0:
                        if update_local:
                            try:
                                with open(local_path, "w", encoding="utf-8") as fp:
                                    json.dump(data, fp)
                            except OSError:
                                pass
                        return data, "ONLINE (Binance API)"
            except Exception:
                continue

    # Fallback para o arquivo local
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        return data, f"LOCAL ({os.path.basename(local_path)})"

    raise RuntimeError(f"Não foi possível obter dados para {symbol} (nem online, nem em {local_path}).")


def parse_close_series(klines: list) -> dict:
    """Retorna dicionário {timestamp_ms: close_price} e o último preço de fechamento."""
    series = {}
    for row in klines:
        t = int(row[0])
        c = float(row[4])
        series[t] = c
    last_close = float(klines[-1][4])
    last_time_ms = int(klines[-1][6]) if len(klines[-1]) > 6 else int(klines[-1][0])
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
    print("\n[1/4] Carregando cotações a partir de paresXlinks.json...")

    coin_Data = {}
    bnb_brl_price = None
    bnb_brl_source = ""

    for item in pairs_links:
        symbol, url = item[0].strip().upper(), item[1].strip()
        klines, source = fetch_klines(symbol, url, offline=args.offline)
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
