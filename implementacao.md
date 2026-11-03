# Detalhes Técnicos e Arquitetura de Implementação

[← Voltar ao README principal](README.md)

---

## 1. Visão Geral da Arquitetura

O sistema é dividido em dois módulos principais sem dependências externas de bibliotecas científicas (`numpy`/`scipy`), garantindo portabilidade imediata em qualquer instalação padrão de **Python 3**:

1. **`rebalanceamento_cover.py` (Motor Matemático, Cliente API Binance e CLI):**
   * Implementa os três algoritmos de alocação de Thomas M. Cover (`CRP`, `Universal Portfolio Dirichlet 1/2` e `BCRP`) em Python puro (`math`, `random`).
   * Realiza a coleta dos últimos 1.000 candles diários (`1d`) da API pública da Binance a partir de `paresXlinks.json`, atualizando os arquivos `.json` locais e usando-os automaticamente como *fallback* quando sem internet.
   * Realiza a leitura autenticada (`HMAC-SHA256`) dos saldos reais da carteira **Spot** na Binance via `keys.json`.
   * Mantém a persistência histórica de todas as leituras e simulações em `historico_carteira.json`.
2. **`rebalanceamento_cover_gui.py` (Interface Gráfica em PyQt5):**
   * Interface desktop responsiva com tema escuro (inspirado no layout da Binance).
   * Executa a atualização de candles, cotações recentes e leitura da conta Spot em *thread* separada (`PriceFetchWorker` via `QThread`) na inicialização do programa.
   * Calcula a carteira e o passo a passo de ordens sob demanda ao clicar em **"⚡ Simular Ordens"** utilizando uma *thread* dedicada (`PortfolioCalcWorker`).
   * Exibe um *layer* modal semitransparente com ampulheta vetorial animada (`LoadingOverlay` e `HourglassSpinnerWidget`) tanto durante a busca de dados da Binance quanto durante o processamento matemático dos modelos de Tom Cover.

---

## 2. Implementação dos Algoritmos Matemáticos (`rebalanceamento_cover.py`)

### 2.1. Matriz de Retornos Relativos (`relatives_matrix`)
Para cada moeda ativa $c \neq \text{BNB}$, o preço de fechamento no instante $t$ (cotado em BNB) produz o retorno relativo diário:

$$
x_{t,c} = \frac{\text{Close}_{t,c}}{\text{Close}_{t-1,c}}, \quad x_{t,\text{BNB}} = 1
$$

O sistema alinha automaticamente o comprimento comum dos últimos $N$ candles disponíveis entre os ativos selecionados (`window_len = min(all_lengths)`), permitindo combinar qualquer subconjunto de moedas ativas.

### 2.2. Portfólio Universal de Cover (`compute_universal_weights`)
* Amostra um conjunto determinístico (`random.Random(42)`) de vetores de pesos $\mathbf{b}^{(k)} \in \Delta_m$ distribuídos segundo a priori de Jeffreys $\text{Dirichlet}(1/2, \dots, 1/2)$ (gerados via variáveis $\text{Gamma}(0.5, 1.0)$ normalizadas, mais os vértices puros e o baricentro uniforme).
* Acumula o log-retorno de cada carteira amostrada ao longo da janela histórica:

$$
\ell_k = \sum_{t=1}^{T} \ln\left( \mathbf{b}^{(k)} \cdot \mathbf{x}_t \right)
$$

* Aplica estabilização numérica (*log-sum-exp* subtraindo $\max_k \ell_k$) para calcular os pesos finais sem *underflow* ou *overflow*:

$$
\hat{\mathbf{b}} = \frac{\sum_k \mathbf{b}^{(k)} \exp(\ell_k - \ell_{\max})}{\sum_k \exp(\ell_k - \ell_{\max})}
$$

### 2.3. Melhor Portfólio Constantemente Rebalanceado (`compute_bcrp_weights`)
* Resolve o problema de otimização côncava $\max_{\mathbf{b} \in \Delta_m} \sum_{t=1}^T \ln(\mathbf{b} \cdot \mathbf{x}_t)$ pelo algoritmo multiplicativo de **ponto fixo de Cover** (*Cover's iterative algorithm*):

$$
b_i^{(r+1)} = b_i^{(r)} \cdot \frac{1}{T} \sum_{t=1}^{T} \frac{x_{t,i}}{\mathbf{b}^{(r)} \cdot \mathbf{x}_t}
$$

* A convergência é garantida no simplex $\Delta_m$ até que $\max_i |b_i^{(r+1)} - b_i^{(r)}| < 10^{-9}$, zerando automaticamente ativos cujo retorno marginal reduz o crescimento em BNB.

---

## 3. Integração com a API da Binance

### 3.1. Atualização de Candles e Cotação Mais Recente (`fetch_klines`, `normalize_klines_payload`, `fetch_latest_pair_price`)
* Lê cada entrada `[SIMBOLO, URL_CANDLES, URL_PRECO_RECENTE]` definida em `paresXlinks.json`:
  1. **Série Histórica de Candles (`new-otc/pair-klines`):** Consulta `https://www.binance.com/bapi/margin/v1/friendly/new-otc/pair-klines?interval=1d&baseCoin=<MOEDA>&quoteCoin=BNB` (com suporte a descompactação `gzip` e *fallback* para `/api/v3/uiKlines`). A função `normalize_klines_payload` converte qualquer envelope BAPI (`{"code": "000000", "data": [...]}`) para a matriz padronizada de candles.
  2. **Cotação Mais Recente em Tempo Real (`new-otc/pair-price-change`):** Consulta `https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin=BNB&toCoin=<MOEDA>` via `fetch_latest_pair_price`, alinhando automaticamente a direção da cotação (`preço` vs. `1 / preço`) em relação ao último fechamento dos candles para garantir que `<MOEDA>BNB` esteja sempre em **BNB por 1 unidade da moeda** e `BNBBRL` esteja sempre em **R$ por 1 BNB**.
  3. **Atualização dos Arquivos JSON Locais (`save_local_klines`):** Atualiza o preço de fechamento do último candle com a cotação mais recente, grava atomicamente o arquivo `<SIMBOLO>.json` local no disco e lê a série diretamente do arquivo `.json` atualizado (que também passa a servir como cache para o modo `--offline`).

### 3.2. Leitura Autenticada do Saldo Spot (`fetch_spot_balances`)
* Lê `apiKey` e `secretKey` de `keys.json` (`load_api_keys`). Valores de exemplo são detectados automaticamente e ignorados sem gerar erros de rede.
* Sincroniza o timestamp diretamente com o servidor oficial da Binance (`GET /api/v3/time` via `get_binance_server_time`) para evitar erros de defasagem de relógio local (`HTTP 400 / -1021`).
* Assina a query `timestamp=<ts>&recvWindow=60000` com `HMAC-SHA256` e consulta `GET /api/v3/account` (com *fallback* para `POST /sapi/v3/asset/getUserAsset`) através dos servidores `api.binance.com`, `api1.binance.com`, `api2.binance.com` e `api3.binance.com`.
* Soma `free + locked` para cada um dos 6 ativos da carteira (`BNB`, `XRP`, `SOL`, `TRX`, `DOGE`, `LTC`).

---

## 4. Interface Gráfica (`rebalanceamento_cover_gui.py`)

* **Cabeçalho Compacto (`34px`):** Exibe em linha única o Patrimônio Total em BNB, Patrimônio Total em Reais (`R$`), Cotação `BNBBRL` e Resumo de Ordens.
* **Geometria Adaptativa:** Consulta `QApplication.primaryScreen().availableGeometry()` para iniciar ajustada à largura do monitor (`minWidth: 720px`).
* **Painel Esquerdo de Configuração e Saldos:**
  * Modelo **Portfólio Universal (Dirichlet 1/2)** selecionado como padrão (`default`).
  * Controle de **Limiar Mínimo de Desvio (`%`)** para filtrar micro-ordens e economizar taxas.
  * 6 linhas de ativos com *checkbox* individual (para incluir/excluir a moeda do rebalanceamento) e campo de quantidade (iniciado em `0` para preenchimento manual ou populado automaticamente via API Spot).
* **Painel Direito de Carteiras e Simulação:**
  * Tabela superior com altura ajustada para as **6 carteiras (`188px`)**, exibindo Saldo Atual, Preço em BNB, Valor em BNB, Valor em R$, Peso Atual, Peso Alvo, Diferença e Ação.
  * Painel inferior amplo para **"Simular Ordens — Passo a Passo na Binance"**, ordenando primeiro todas as **VENDAS** (para gerar caixa em BNB) e depois todas as **COMPRAS** (descontando a taxa spot de `0,10%`).
  * Tanto a tabela das carteiras quanto o passo a passo das ordens só são atualizados após clicar no botão **"⚡ Simular Ordens"**.
* **Layer de Ampulheta Animada (`LoadingOverlay` & `HourglassSpinnerWidget`):**
  * **`HourglassSpinnerWidget`:** Desenha em tempo real (`QPainter` a `25 FPS`) uma ampulheta vetorial com anel giratório dourado (`#F0B90B`) e fluxo contínuo de areia escorrendo do bulbo superior para o inferior.
  * **`LoadingOverlay`:** Camada modal semitransparente (`rgba(18, 20, 26, 190)`) que cobre toda a janela principal, altera o cursor para `WaitCursor` e impede cliques acidentais enquanto operações estão em andamento:
    1. **Carregamento de Dados (`PriceFetchWorker`):** Emite `progress_signal` a cada par consultado em `paresXlinks.json` e durante a leitura do saldo Spot (`keys.json`), atualizando o subtítulo do *overlay* em tempo real.
    2. **Processamento dos Modelos (`PortfolioCalcWorker`):** Executa `compute_universal_weights` (Monte Carlo Dirichlet 1/2) e `compute_bcrp_weights` em segundo plano sincronizado com `QEventLoop`, mantendo a animação da ampulheta fluida durante os cálculos.

---

## 5. Recomendações Operacionais e Horários de Execução

1. **Melhor Horário para Atualização dos Candles (21:05 às 21:15 BRT / UTC-3):**
   * O candle diário (`1d`) da Binance fecha exatamente à **00:00 UTC** (**21:00 no horário de Brasília**).
   * Executar o script entre **21:05 e 21:15 (BRT)** garante que o candle diário recém-fechado já foi consolidado, alimentando o modelo Universal (`Dirichlet 1/2`) e o BCRP com 1000 dias completos.
2. **Melhor Janela de Liquidez para Execução de Ordens (10:00 às 13:00 BRT):**
   * Caso execute ordens de volume maior, o horário entre **10:00 e 13:00 (BRT)** concentra a sobreposição dos mercados europeu e norte-americano, oferecendo menor *spread* nos livros de ofertas dos pares cotados em BNB.
3. **Ordem de Execução na Binance:**
   * Execute sempre as ordens de **VENDA (`Par -> BNB`) primeiro** para liberar saldo livre em BNB, e em seguida execute as ordens de **COMPRA (`BNB -> Par`)**.

---

## 6. Estrutura de Arquivos do Projeto

| Arquivo | Descrição |
| :--- | :--- |
| `rebalanceamento_cover.py` | Motor matemático (`CRP`, `Universal Dirichlet 1/2`, `BCRP`), cliente HTTP/HMAC da API da Binance, persistência de histórico e interface de linha de comando (CLI). |
| `rebalanceamento_cover_gui.py` | Interface gráfica em `PyQt5` para visualização da carteira em BNB e BRL, seleção de modelos e simulação passo a passo das ordens. |
| `paresXlinks.json` | Configuração dos pares negociados contra `BNB` (+ `BNBBRL`) e URLs da API de candles da Binance. |
| `keys.json` | Arquivo de configuração das chaves de leitura da API da Binance (`apiKey` e `secretKey`). |
| `run.sh` | Script auxiliar para execução rápida. |
| `DOGEBNB.json`, `LTCBNB.json`, `SOLBNB.json`, `TRXBNB.json`, `XRPBNB.json`, `BNBBRL.json` | Séries históricas locais de 1000 candles diários (atualizadas automaticamente quando online e utilizadas como fallback quando offline). |
| `historico_carteira.json` | Gerado automaticamente ao salvar leituras da carteira (ignorado pelo Git via `.gitignore`). |

