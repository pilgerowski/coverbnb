# PROMPT MESTRE — Especificação Completa para Recriar o Projeto CoverBNB

Copie e cole o prompt abaixo em um assistente de IA (ou utilize-o como especificação de engenharia) para recriar integralmente o projeto **CoverBNB** do zero:

---

```markdown
Você deve criar um projeto completo em Python chamado **CoverBNB**, composto por um motor matemático/CLI (`rebalanceamento_cover.py`), uma interface gráfica em PyQt5 (`rebalanceamento_cover_gui.py`), arquivos de configuração (`paresXlinks.json`, `keys.json`, `run.sh`, `.gitignore`) e documentação modular (`README.md`, `base_teorica.md`, `implementacao.md`, `instalacao.md`).

## 1. Objetivo do Sistema
Aplicar a teoria de **Portfólios Constantemente Rebalanceados (CRP)**, **Portfólios Universais (`Dirichlet 1/2`)** e **Melhor Portfólio Constante em Retrospectiva (BCRP)** de **Thomas M. Cover** (*Universal Portfolios*, 1991) para negociar criptomoedas contra **BNB** na Binance, tendo como objetivo **acumular a maior quantidade possível de BNB** ao longo do tempo e exibir o patrimônio tanto em **BNB** quanto convertido para **Reais (`BRL`)** via `BNBBRL`.

---

## 2. Restrições Técnicas e de Ambiente
1. **Zero dependências científicas externas:** Todo o motor matemático, cliente HTTP/REST, descompactação `gzip` e assinatura criptográfica `HMAC-SHA256` em `rebalanceamento_cover.py` deve usar **exclusivamente a biblioteca padrão do Python 3** (`math`, `random`, `json`, `os`, `sys`, `time`, `hmac`, `hashlib`, `gzip`, `urllib.request`, `urllib.error`, `argparse`, `datetime`). **NÃO** utilize `numpy`, `scipy`, `pandas` ou `requests`.
2. **Interface Gráfica em `PyQt5`:** A GUI (`rebalanceamento_cover_gui.py`) deve ser implementada usando `PyQt5` (`QtWidgets`, `QtCore`, `QtGui`).
3. **Moedas Operadas (6 ativos na carteira):**
   - Moeda-base (caixa de referência): `BNB` (preço em BNB = `1.0`).
   - 5 altcoins cotadas em BNB: `XRP` (`XRPBNB`), `SOL` (`SOLBNB`), `TRX` (`TRXBNB`), `DOGE` (`DOGEBNB`) e `LTC` (`LTCBNB`).
   - Par de conversão fiduciária: `BNBBRL` (para converter valores de BNB para Reais `R$`).
   - Taxa Spot padrão da Binance considerada nas simulações: `BINANCE_FEE = 0.001` (`0,10%`).

---

## 3. Arquivos de Configuração

### 3.1. `paresXlinks.json`
Lista JSON onde cada elemento possui 3 campos `[SIMBOLO, URL_CANDLES_DIARIOS, URL_PRECO_RECENTE]`:
```json
[
    [
        "XRPBNB",
        "https://www.binance.com/bapi/margin/v1/friendly/new-otc/pair-klines?interval=1d&baseCoin=XRP&quoteCoin=BNB",
        "https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin=BNB&toCoin=XRP"
    ],
    [
        "SOLBNB",
        "https://www.binance.com/bapi/margin/v1/friendly/new-otc/pair-klines?interval=1d&baseCoin=SOL&quoteCoin=BNB",
        "https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin=BNB&toCoin=SOL"
    ],
    [
        "TRXBNB",
        "https://www.binance.com/bapi/margin/v1/friendly/new-otc/pair-klines?interval=1d&baseCoin=TRX&quoteCoin=BNB",
        "https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin=BNB&toCoin=TRX"
    ],
    [
        "DOGEBNB",
        "https://www.binance.com/bapi/margin/v1/friendly/new-otc/pair-klines?interval=1d&baseCoin=DOGE&quoteCoin=BNB",
        "https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin=BNB&toCoin=DOGE"
    ],
    [
        "LTCBNB",
        "https://www.binance.com/bapi/margin/v1/friendly/new-otc/pair-klines?interval=1d&baseCoin=LTC&quoteCoin=BNB",
        "https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin=BNB&toCoin=LTC"
    ],
    [
        "BNBBRL",
        "https://www.binance.com/bapi/margin/v1/friendly/new-otc/pair-klines?interval=1d&baseCoin=BNB&quoteCoin=BRL",
        "https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin=BNB&toCoin=BRL"
    ]
]
```

### 3.2. `keys.json` (Exemplo Seguro)
Formato padrão sugerido pela Binance:
```json
{
  "apiKey": "COLOQUE_SUA_API_KEY_DA_BINANCE_AQUI",
  "secretKey": "COLOQUE_SUA_SECRET_KEY_DA_BINANCE_AQUI",
  "comment": "Arquivo de exemplo — substitua pelas suas chaves da Binance (apenas permissao de Leitura / Read-Only)"
}
```

### 3.3. `run.sh` e `.gitignore`
- `run.sh`: executa `python3 rebalanceamento_cover_gui.py`.
- `.gitignore`: ignora `__pycache__/`, `*.py[cod]`, `historico_carteira.json` e `*.har`.

---

## 4. Especificação do Módulo Principal (`rebalanceamento_cover.py`)

### 4.1. Leitura de Chaves e Saldo Spot na Binance (`load_api_keys`, `get_binance_server_time`, `fetch_spot_balances`)
1. `load_api_keys(keys_path)`:
   - Lê `"apiKey"` e `"secretKey"` (com `.strip()`) do dicionário em `keys.json` (mantendo compatibilidade com `API_KEY`/`SECRET_KEY` ou formato de lista de pares).
   - Se detectar palavras de exemplo (`"SUA_"`, `"YOUR_"`, `"EXEMPLO"`, `"EXAMPLE"`, `"AQUI"`, `"HERE"`), retorna `(None, None)` imediatamente sem tentar autenticar na rede.
2. `get_binance_server_time()`:
   - Consulta `GET /api/v3/time` nos servidores da Binance (`api.binance.com`, `api1.binance.com`, `www.binance.com`) e retorna `serverTime` em milissegundos (com fallback para `int(time.time() * 1000)`), evitando erro `-1021` de relógio local.
3. `fetch_spot_balances(coins_order)`:
   - Assina `timestamp=<ts>&recvWindow=60000` com `HMAC-SHA256` usando `secretKey` e envia header `X-MBX-APIKEY: <apiKey>`.
   - Tenta `GET /api/v3/account` e inclui fallback para `POST /sapi/v3/asset/getUserAsset` nos hosts `api.binance.com`, `api1.binance.com`, `api2.binance.com`, `api3.binance.com`.
   - Soma `free + locked` para cada moeda de `coins_order` e retorna `(dict_saldos, mensagem_status, sucesso_bool)`.

### 4.2. Coleta de Candles, Preço Recente e Atualização dos JSONs Locais (`normalize_klines_payload`, `fetch_latest_pair_price`, `save_local_klines`, `fetch_klines`)
1. `normalize_klines_payload(payload)`:
   - Aceita tanto lista direta de arrays quanto envelope BAPI `{"code": "000000", "data": [...]}` (onde os itens podem ser listas ou dicionários com `openTime`/`time`/`t` e `close`/`closePrice`/`c`/`price`).
   - Normaliza cada candle para `[open_time_ms, open_str, high_str, low_str, close_str, "0", close_time_ms]` ordenado por timestamp crescente.
2. `fetch_latest_pair_price(symbol, price_url, reference_close)`:
   - Consulta o 3º item de `paresXlinks.json` (`new-otc/pair-price-change?fromCoin=BNB&toCoin=...`, com suporte a `gzip`).
   - Extrai o preço do JSON (`data`) e orienta automaticamente entre `valor` e `1.0 / valor` comparando a distância logarítmica `abs(math.log(cand / reference_close))` com o fechamento do último candle (`reference_close`), garantindo que pares `<MOEDA>BNB` estejam sempre em **BNB por 1 unidade da moeda** e `BNBBRL` esteja em **R$ por 1 BNB**.
3. `save_local_klines(symbol, data)`:
   - Grava de forma atômica (via arquivo `.tmp` + `os.replace`) o arquivo `<SIMBOLO>.json` local (`XRPBNB.json`, `SOLBNB.json`, `TRXBNB.json`, `DOGEBNB.json`, `LTCBNB.json`, `BNBBRL.json`).
4. `fetch_klines(symbol, url, offline=False, update_local=True, price_url=None)`:
   - Se `not offline`: baixa os candles de `url` (com fallback para `/api/v3/uiKlines` e `/api/v3/klines`), consulta `fetch_latest_pair_price` para atualizar o preço de fechamento atual (`data[-1][4]`), atualiza o arquivo `<SIMBOLO>.json` no disco via `save_local_klines` e em seguida lê os dados do arquivo `.json` local atualizado.
   - Se `offline=True` ou sem internet: lê diretamente do arquivo `<SIMBOLO>.json` local.

### 4.3. Algoritmos Matemáticos de Thomas M. Cover
A partir das séries de fechamento das moedas ativas (`active_universe`), alinhe os últimos `window_len = min(all_lengths)` candles e construa a matriz de retornos relativos diários `relatives_matrix` onde, para cada período $t$, $x_{t,\text{BNB}} = 1.0$ e $x_{t,c} = \text{Close}_{t,c} / \text{Close}_{t-1,c}$:
1. **CRP (`crp`):** Pesos iguais $b_i = 1 / m_{\text{ativas}}$ para todas as moedas ativas.
2. **Portfólio Universal de Cover (`universal` — `compute_universal_weights`):**
   - Usa gerador determinístico `random.Random(1991)` para amostrar `num_experts` carteiras no simplex $\Delta_m$ segundo a priori $\text{Dirichlet}(1/2, \dots, 1/2)$ usando `rng.gammavariate(0.5, 1.0)` normalizado, adicionando também o baricentro uniforme e os vértices puros.
   - Calcula a riqueza acumulada $S_n(\mathbf{b}^{(k)}) = \prod_{t=1}^T (\mathbf{b}^{(k)} \cdot \mathbf{x}_t)$ de cada carteira e retorna a média ponderada pelo desempenho acumulado:
     $$\hat{\mathbf{b}} = \frac{\sum_k \mathbf{b}^{(k)} S_n(\mathbf{b}^{(k)})}{\sum_k S_n(\mathbf{b}^{(k)})}$$
3. **BCRP Histórico (`bcrp` — `compute_bcrp_weights`):**
   - Maximiza $\sum_{t=1}^T \ln(\mathbf{b} \cdot \mathbf{x}_t)$ no simplex $\Delta_m$ via iteração multiplicativa de ponto fixo de Cover:
     $$b_i^{(r+1)} = b_i^{(r)} \cdot \frac{1}{T} \sum_{t=1}^T \frac{x_{t,i}}{\mathbf{b}^{(r)} \cdot \mathbf{x}_t}$$
     combinada com projeção euclidiana no simplex e busca em linha armijo/backtracking para convergência rápida.

### 4.4. Argumentos de Linha de Comando (CLI) em `rebalanceamento_cover.py`
- `--gui`: Abre a interface gráfica (`rebalanceamento_cover_gui.py`).
- `--offline`: Usa apenas os arquivos `.json` locais sem consultar a internet.
- `--atualizar-json`: Apenas baixa os candles e cotações recentes da Binance, atualiza os arquivos `.json` locais e encerra.
- `--estrategia {crp,universal,bcrp}`: Escolhe o modelo de rebalanceamento.
- `--apenas-ativas`: Rebalanceia apenas entre as moedas com saldo `> 0` (mais `BNB`).
- `--saldos`: Recebe os saldos via string `"BNB=1.5,XRP=500,..."` ou JSON `'{"BNB": 1.5, ...}'`.
- `--limiar`: Desvio mínimo percentual (`float`, padrão `1.0%`) para sugerir `COMPRAR` ou `VENDER` (abaixo do limiar sugere `MANTER`).

---

## 5. Especificação da Interface Gráfica (`rebalanceamento_cover_gui.py`)

1. **Tema Visual e Geometria:**
   - Tema escuro estilo Binance (`#0B0E11` fundo principal, `#1E2329` painéis/cards, `#F0B90B` destaque amarelo BNB, `#0ECB81` verde compra, `#F6465D` vermelho venda).
   - Largura ajustada automaticamente à tela via `QApplication.primaryScreen().availableGeometry()` (máximo `90%` da largura útil, `minWidth: 720`, painel esquerdo com `setMaximumWidth(350)`).
2. **Cabeçalho Compacto (`34px` de altura):**
   - 4 cards horizontais em linha única (`setFixedHeight(34)`):
     1. `Total BNB:` (em amarelo `#F0B90B`)
     2. `Total R$:` (em verde `#0ECB81`)
     3. `BNBBRL:` (cotação atual em `R$`)
     4. `Evolução:` (variação em BNB e `%` contra o último registro salvo em `historico_carteira.json`)
3. **Inicialização Automática (`PriceFetchWorker` via `QThread`):**
   - Ao abrir o programa, dispara automaticamente a atualização online dos candles e preços recentes a partir de `paresXlinks.json` (atualizando os arquivos `.json` locais) e consulta o saldo Spot real na Binance via `keys.json`.
   - Se `keys.json` tiver chaves válidas, preenche os campos de quantidade com o saldo Spot real; caso contrário, inicia todos os campos zerados (`0`).
   - O seletor de modelo (`self.strategy_combo`) deve vir sempre com **"Portfólio Universal (Dirichlet 1/2)"** (`universal`) selecionado como `default`, e o controle de **Desvio Mínimo (`self.threshold_spin`)** deve iniciar em **`1,5%`** (`setValue(1.5)`).
   - Não deve existir botão `"JSONs Locais"`; os botões de ação no painel esquerdo são:
     - **"⚡ Simular Ordens"** (ocupa a largura das 2 colunas no topo)
     - **"🔄 Atualizar Saldo"** (à esquerda) e **"💾 Salvar Registro"** (à direita) abaixo.
   - Logo abaixo dos botões de ação no painel esquerdo, incluir o box **"3. Meta de Acumulação (256 BNB)"** exibindo o progresso atual (`total_bnb / 256 BNB`), percentual concluído, dobras restantes (`log2(256 / total_bnb)`) e o próximo marco da escada de dobras.
4. **Comportamento da Tabela das 6 Carteiras e Simulação Automática + Exploratória:**
   - Na aba **"⚖️ Carteira & Ordens"**, a tabela superior (`self.table_positions`) mostra exatamente as **6 carteiras (`BNB`, `XRP`, `SOL`, `TRX`, `DOGE`, `LTC`)** com altura fixa calculada sob medida (`28 + n_rows * 26 + 4 = 188px`, sem barra de rolagem vertical), deixando todo o espaço inferior para o grupo **"Simular Ordens — Passo a Passo na Binance (Acumular BNB)"** (`self.orders_text`).
   - **Importante:** Assim que o carregamento inicial dos candles e dos saldos Spot termina (`_on_prices_loaded`), o programa já executa automaticamente a simulação das ordens (`self.recalculate_portfolio()`), aproveitando o *layer* de ampulheta. Os botões **"⚡ Simular Ordens"** e **"🔄 Atualizar Saldo"** permanecem disponíveis para que o usuário possa fazer testes exploratórios alterando quantidades/parâmetros na carteira ou recarregar os saldos reais da corretora.
   - O passo a passo das ordens lista primeiro o **1º Passo: VENDAS (`Moeda -> BNB`)** para liberar BNB em caixa, e depois o **2º Passo: COMPRAS (`BNB -> Moeda`)**, exibindo quantidades exatas, valores em BNB, valores em `R$`, reserva final de BNB e estimativa de taxa (`0,10%`).
5. **Layer de Ampulheta Animada (`LoadingOverlay` e `HourglassSpinnerWidget`):**
   - Implementar um overlay semitransparente sobre a janela principal com uma ampulheta vetorial animada (`QPainter` com arco giratório `#F0B90B` e areia fluindo entre os bulbos) que bloqueia cliques acidentais e informa o progresso detalhado em tempo real:
     - Durante o carregamento de dados da Binance (`PriceFetchWorker`: busca de candles, cotação recente de cada par e leitura do saldo Spot).
     - Durante o processamento matemático dos modelos de Tom Cover (`PortfolioCalcWorker`: simulação Monte Carlo Dirichlet 1/2 do Portfólio Universal e otimização do BCRP).
6. **Abas Adicionais:**
   - **"📊 Modelos Cover"**: Tabela comparando lado a lado o Peso Atual, `CRP (1/N)`, `Universal Cover (Dirichlet 1/2)` e `BCRP Histórico` para cada ativo.
   - **"🕒 Histórico"**: Lista todos os registros salvos em `historico_carteira.json` com botões para carregar ou excluir um registro selecionado.
```

