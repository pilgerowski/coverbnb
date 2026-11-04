# ❓ Perguntas Frequentes (FAQ) — CoverBNB

[← Voltar ao README principal](README.md) | [🌱 Guia para Iniciantes (`base_teorica_leigos.md`)](base_teorica_leigos.md) | [📘 Base Teórica Matemática (`base_teorica.md`)](base_teorica.md)

Este documento reúne e organiza todas as perguntas teóricas, operacionais, analíticas e técnicas feitas durante o desenvolvimento e operação do **CoverBNB**.

---

## 📑 Índice de Perguntas

### Parte I — Teoria e Modelos de Thomas M. Cover
1. [O que é e como funciona o rebalanceamento de portfólios de Thomas M. Cover?](#1-o-que-é-e-como-funciona-o-rebalanceamento-de-portfólios-de-thomas-m-cover)
2. [Qual é a diferença prática entre os 3 modelos (`CRP`, `Portfólio Universal Dirichlet 1/2` e `BCRP`)?](#2-qual-é-a-diferença-prática-entre-os-3-modelos-crp-portfólio-universal-dirichlet-12-e-bcrp)
3. [Na aba "Modelos Cover", por que a `TRX` aparece com `99,84%` no `BCRP Histórico`? O que isso significa?](#3-na-aba-modelos-cover-por-que-a-trx-aparece-com-9984-no-bcrp-histórico-o-que-isso-significa)
4. [Das moedas do portfólio, alguma teve queda violenta em relação ao BNB nos últimos 1.000 candles? Por que a `ZEC` foi retirada?](#4-das-moedas-do-portfólio-alguma-teve-queda-violenta-em-relação-ao-bnb-nos-últimos-1000-candles-por-que-a-zec-foi-retirada)

### Parte II — Operação Prática na Binance
5. [A que horas é mais indicado rodar o script e executar as ordens?](#5-a-que-horas-é-mais-indicado-rodar-o-script-e-executar-as-ordens)
6. [Por que o Desvio Mínimo padrão é de `1,5%` e qual o impacto das taxas da Binance?](#6-por-que-o-desvio-mínimo-padrão-é-de-15-e-qual-o-impacto-das-taxas-da-binance)
7. [Como posso obter uma imagem/retrato dos meus ativos que estão na carteira Spot da Binance?](#7-como-posso-obter-uma-imagemretrato-dos-meus-ativos-que-estão-na-carteira-spot-da-binance)
8. [Em que ordem devo executar as sugestões na Binance?](#8-em-que-ordem-devo-executar-as-sugestões-na-binance)

### Parte III — Desempenho Real, Metas e Projeções de Acumulação de BNB
9. [Analisando o `historico_carteira.json`, já há algum ganho?](#9-analisando-o-historico_carteirajson-já-há-algum-ganho)
10. [Por que a meta foi definida em `256 BNBs` ("A Escada das 10 Dobras")?](#10-por-que-a-meta-foi-definida-em-256-bnbs-a-escada-das-10-dobras)
11. [Nesse ritmo, quanto tempo se estima para chegar em `1 BNB`, `2 BNB`, `5 BNB`, `256 BNB` e `1.000 BNB`?](#11-nesse-ritmo-quanto-tempo-se-estima-para-chegar-em-1-bnb-2-bnb-5-bnb-256-bnb-e-1000-bnb)
12. [E quantos BNBs eu poderia ter em `01/01/2038`?](#12-e-quantos-bnbs-eu-poderia-ter-em-01012038)

### Parte IV — Questões Técnicas do Sistema
13. [De onde o script busca os candles diários e a cotação mais recente (`paresXlinks.json`)?](#13-de-onde-o-script-busca-os-candles-diários-e-a-cotação-mais-recente-paresxlinksjson)

---

## Parte I — Teoria e Modelos de Thomas M. Cover

### 1. O que é e como funciona o rebalanceamento de portfólios de Thomas M. Cover?
O método criado por **Thomas M. Cover** (*Universal Portfolios*, 1991) aplica a **Teoria da Informação** ao mercado financeiro. Em vez de tentar adivinhar para onde os preços vão, o investidor define fatias percentuais para uma cesta de moedas cotadas em **BNB** e restaura essas proporções periodicamente:
* Quando uma moeda **sobe** frente ao BNB, a fatia dela na carteira fica maior que o alvo $\implies$ você **vende o excesso** e guarda o lucro em **BNB**.
* Quando uma moeda **cai** frente ao BNB, a fatia dela encolhe $\implies$ você usa uma pequena fração de **BNB** para **recomprar na baixa**.
* Esse processo extrai ganho diretamente da oscilação dos preços — fenômeno chamado de **Bombeamento de Volatilidade (*Volatility Pumping*)** — permitindo aumentar a quantidade total de BNB mesmo que as altcoins andem de lado no longo prazo.

---

### 2. Qual é a diferença prática entre os 3 modelos (`CRP`, `Portfólio Universal Dirichlet 1/2` e `BCRP`)?

| Modelo | Como Funciona | Vantagem Principal | Ponto de Atenção |
| :--- | :--- | :--- | :--- |
| **`Portfólio Universal (Dirichlet 1/2)`** *(Padrão)* | Simula milhares de carteiras com pesos diferentes ao longo dos candles históricos (usando a distribuição *a priori* de Jeffreys `Dirichlet(1/2)`) e pondera cada uma pelo lucro real acumulado em BNB. | **Equilíbrio ideal:** dá fatias maiores para as moedas que mais geram BNB (como `TRX`), mas mantém reservas saudáveis nas demais para capturar altas repentinas. | Adaptação suave e progressiva (não zera completamente moedas secundárias). |
| **`CRP — Pesos Iguais (1/N)`** | Divide o patrimônio em partes exatamente iguais entre os ativos marcados (nos 6 ativos, `16,67%` para cada). | Máxima diversificação sem viés do passado; captura qualquer alta de qualquer moeda. | Não aprende com o histórico: se uma moeda entrar em queda secular sem volta, continuará mandando comprá-la. |
| **`BCRP — Ótimo Histórico`** | Calcula matematicamente qual teria sido a carteira fixa perfeita olhando para trás (nos últimos candles diários). | Corta para `0%` moedas perdedoras no período e mostra quem foi a campeã histórica contra o BNB. | Olha 100% pelo retrovisor (*overfitting*), podendo concentrar quase tudo em uma única moeda. |

---

### 3. Na aba "Modelos Cover", por que a `TRX` aparece com `99,84%` no `BCRP Histórico`? O que isso significa?
O **BCRP Histórico** (*Best Constant Rebalanced Portfolio*) responde à pergunta: *"Se eu tivesse uma máquina do tempo e conhecesse o passado de antemão, qual divisão teria gerado o máximo absoluto de BNB?"*

Na janela histórica comum dos candles diários (últimos **324 dias**), o desempenho acumulado de cada moeda cotada em **BNB** foi:
* 🥇 **`TRXBNB`:** **🟢 `+42,19%`** (`1,42x` mais BNB)
* 🥈 **`BNB` (Caixa):** **`0,00%`** (`1,00x`)
* **`SOLBNB`:** 🔴 `-10,09%`
* **`LTCBNB`:** 🔴 `-13,25%`
* **`XRPBNB`:** 🔴 `-17,02%`
* **`DOGEBNB`:** 🔴 `-29,03%`

Como a **`TRX`** foi a única que superou fortemente o próprio `BNB` nesse recorte enquanto as outras 4 recuaram frente ao BNB, o otimizador em retrospectiva (`BCRP`) atribui **`99,84%` para `TRX`** e quase `0%` para as demais.

> **Por que não seguimos o BCRP puro e usamos o Portfólio Universal (`Dirichlet 1/2`)?**
> Porque colocar `99,84%` em uma moeda só acabaria com a diversificação e mataria o *Volatility Pumping* futuro. O **Portfólio Universal (`Dirichlet 1/2`)** usa essa mesma informação com prudência: premia a **`TRX` com a maior fatia da carteira (`18,10%`)**, mas mantém entre **`15,8%` e `17,0%`** nas demais moedas (`BNB`, `XRP`, `LTC`, `SOL`, `DOGE`) para capturar a próxima pernada de alta de qualquer uma delas.

---

### 4. Das moedas do portfólio, alguma teve queda violenta em relação ao BNB nos últimos 1.000 candles? Por que a `ZEC` foi retirada?
Sim. No estudo dos 1.000 candles diários, observou-se a diferença fundamental entre **oscilação cíclica** (queda seguida de forte recuperação, ideal para o rebalanceamento) e **colapso secular** (queda contínua sem recuperação):

| Par | Maior Queda (*Max Drawdown*) | Maior Queda em 1 Dia | Diagnóstico frente ao BNB |
| :--- | :---: | :---: | :--- |
| **`ZECBNB`** *(Retirada)* | **-96,58%** | -24,63% | ❌ **Colapso secular sem recuperação (-95,1% no total):** drenava BNB ao ser recomprada na queda. Por isso foi **removida da operação**. |
| **`LTCBNB`** | **-78,67%** | -18,91% | ⚠️ Queda estrutural forte no longo prazo, porém com repiques intermediários. |
| **`DOGEBNB`** | **-78,81%** | -37,63% | ✅ Explosões episódicas gigantescas seguidas de correção (excelente para vender nos picos). |
| **`XRPBNB`** | **-74,35%** | -16,82% | ✅ Caiu forte e depois **triplicou** contra o BNB, gerando lucro positivo no rebalanceamento mesmo caindo no *Buy & Hold*. |
| **`SOLBNB`** | **-73,88%** | -14,25% | ✅ Subiu `+237%` antes de corrigir; alta volatilidade para bombeamento. |
| **`TRXBNB`** | **-59,87%** | -15,24% | ✅ Oscilação saudável com tendência de alta estrutural contra o BNB. |

---

## Parte II — Operação Prática na Binance

### 5. A que horas é mais indicado rodar o script e executar as ordens?
1. **Para atualizar os candles e calcular a carteira: entre `21:05` e `21:15` (Horário de Brasília — BRT / UTC-3):**
   * O candle diário (`1d`) da Binance fecha exatamente à **00:00 UTC** (**21:00 no horário de Brasília**). Rodar logo após as 21:05 garante que o candle do dia já fechou completo.
2. **Para executar ordens maiores com menor *spread*: entre `10:00` e `13:00` (BRT):**
   * Horário em que as bolsas da Europa e dos Estados Unidos operam juntas, oferecendo maior liquidez nos livros de ofertas.
3. **Horários a evitar:**
   * **20:55 às 21:02 (BRT):** virada do candle diário (alta volatilidade de *spread*).
   * **02:00 às 05:00 (BRT):** menor liquidez global.

---

### 6. Por que o Desvio Mínimo padrão é de `1,5%` e qual o impacto das taxas da Binance?
* A Binance cobra **0,10% de taxa Spot** por operação (ou 0,075% usando desconto em BNB).
* As simulações mostraram que rebalancear micro-oscilações diárias menores que `1%` gasta parte do ganho em taxas.
* Com o **Desvio Mínimo padrão de `1,5%`** (ou bandas maiores entre `2%` e `5%`), o sistema ignora ruídos irrelevantes (`MANTER`) e só sugere ordens quando há um movimento real de preço que compensa com folga a taxa da corretora.

---

### 7. Como posso obter uma imagem/retrato dos meus ativos que estão na carteira Spot da Binance?
Existem duas formas:
1. **Automaticamente pelo próprio CoverBNB (via `keys.json`):**
   * Basta criar uma chave de API na Binance (`Gerenciamento de API`) marcando **apenas a permissão "Habilitar Leitura" (*Enable Reading*)** e colar `apiKey` e `secretKey` no arquivo `keys.json`.
   * Ao abrir a interface gráfica (ou clicar em **`🔄 Atualizar Saldo`**), o programa consulta a sua conta Spot via `HMAC-SHA256` (`GET /api/v3/account`) e preenche todas as quantidades reais automaticamente.
2. **Manualmente no site/app da Binance:**
   * Menu `Carteira (Wallet) -> Conta Spot (Spot)`, marcando *"Ocultar pequenos saldos"*.

---

### 8. Em que ordem devo executar as sugestões na Binance?
Sempre execute:
1. **1º PASSO — ORDENS DE VENDA (`Moeda -> BNB`):** vende o excedente das moedas que subiram e transforma o lucro em **BNB livre no caixa**.
2. **2º PASSO — ORDENS DE COMPRA (`BNB -> Moeda`):** usa o BNB disponível em caixa para comprar as moedas que ficaram abaixo do peso-alvo.

---

## Parte III — Desempenho Real, Metas e Projeções de Acumulação de BNB

### 9. Analisando o `historico_carteira.json`, já há algum ganho?
Sim! Após a consolidação das 6 carteiras (`BNB`, `XRP`, `SOL`, `TRX`, `DOGE`, `LTC`, sem `ZEC`) e a adoção das cotações OTC em tempo real da Binance em `02/11/2026`:
* **Registro #7 (`02/11 às 23:11`):** `0.25084605 BNB` (`R$ 954,72`)
* **Registro #8 (`03/11 às 21:39`):** `0.25142239 BNB` (`R$ 961,94`) — ganho de `+0.00057634 BNB` (`+0,23%`)
* **Registro #9 (`03/11 às 23:03`):** **`0.25186882 BNB`** (`R$ 961,89`) — ganho adicional de `+0.00044643 BNB` (`+0,18%`), já descontando as taxas das compras de `XRP` e `DOGE`!
* **Resultado acumulado em 24 horas (`#7` $\to$ `#9`):** **`+0.00102277 BNB` (`+0,4077%` de ganho líquido em BNB em 24h)** e **`+R$ 7,17` (`+0,75%` em Reais)**.

---

### 10. Por que a meta foi definida em `256 BNBs` ("A Escada das 10 Dobras")?
Porque partindo do capital inicial de **`~0,25 BNB`** ($2^{-2}\text{ BNB}$), chegar a **`256 BNB`** ($2^8\text{ BNB}$) representa **exatamente 10 dobras sucessivas (`10 × 2x`, multiplicação por `1.024x`)**:
1. `0,25` $\to$ **`0,50 BNB`**
2. `0,50` $\to$ **`1,00 BNB`**
3. `1,00` $\to$ **`2,00 BNB`**
4. `2,00` $\to$ **`4,00 BNB`**
5. `4,00` $\to$ **`8,00 BNB`**
6. `8,00` $\to$ **`16,00 BNB`**
7. `16,00` $\to$ **`32,00 BNB`**
8. `32,00` $\to$ **`64,00 BNB`**
9. `64,00` $\to$ **`128,00 BNB`**
10. `128,00` $\to$ **`256,00 BNB`** *(~R$ 977,6 mil na cotação atual do BNB)*

Como o crescimento é composto, **cada dobra leva exatamente o mesmo tempo** se a taxa percentual média for mantida.

---

### 11. Nesse ritmo, quanto tempo se estima para chegar em `1 BNB`, `2 BNB`, `5 BNB`, `256 BNB` e `1.000 BNB`?
Partindo do saldo de **`0.25186882 BNB`**, veja o tempo estimado em 3 cenários de velocidade média de acumulação de BNB:

| Meta em BNB | Valor Hoje (`BNBBRL = R$ 3.819`) | Multiplicador | 🔥 Ritmo das Últimas 24h (`+0,41% / dia`) | ⚖️ Ritmo Moderado (`+0,20% / dia`) | 🐢 Ritmo Conservador (`+0,10% / dia`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`0,50 BNB`** *(1ª Dobra)* | R$ 1.909,50 | `1,98x` | **~5,5 meses** (`169 dias`) | **~11,3 meses** (`343 dias`) | **~1 ano e 10 meses** (`686 dias`) |
| **`1,00 BNB`** *(2ª Dobra)* | R$ 3.819,00 | `3,97x` | **~11 meses** (`339 dias`) | **~1 ano e 11 meses** (`690 dias`) | **~3 anos e 9 meses** (`1.379 dias`) |
| **`2,00 BNB`** *(3ª Dobra)* | R$ 7.638,00 | `7,94x` | **~1 ano e 5 meses** (`509 dias`) | **~2 anos e 10 meses** (`1.037 dias`) | **~5 anos e 8 meses** (`2.073 dias`) |
| **`5,00 BNB`** | R$ 19.095,00 | `19,85x` | **~2 anos** (`734 dias`) | **~4 anos e 1 mês** (`1.495 dias`) | **~8 anos e 2 meses** (`2.990 dias`) |
| **`256,00 BNB`** *(🎯 Meta 10ª Dobra)* | **R$ 977.664,00** | `1.016,40x` | **~4 anos e 8 meses** (`1.702 dias`) | **~9 anos e 6 meses** (`3.465 dias`) | **~18 anos e 11 meses** (`6.927 dias`) |
| **`1.000,00 BNB`** | R$ 3.819.000,00 | `3.970,32x` | **~5 anos e 7 meses** (`2.037 dias`) | **~11 anos e 4 meses** (`4.147 dias`) | **~22 anos e 8 meses** (`8.291 dias`) |

> **Nota sobre Liquidez Acima de `100 BNB`:** Acima de `100 BNB` rumo a `256` ou `1.000 BNB`, as ordens individuais passam a movimentar dezenas de BNBs de uma vez. Nessa faixa, recomenda-se executar ordens *Limit* (Maker) ou operar via pares de altíssima liquidez (`Moeda/USDT` $\leftrightarrow$ `BNB/USDT`) para evitar *slippage* no livro de ofertas.

---

### 12. E quantos BNBs eu poderia ter em `01/01/2038`?
Entre `04/11/2026` e `01/01/2038` existem exatamente **`4.076 dias`** (**11 anos e 2 meses**). Partindo de `0.25186882 BNB`, a projeção para `01/01/2038` conforme a taxa média diária de acumulação é:

| Cenário | Taxa Média Diária | Taxa Anual Equivalente | **Saldo Estimado em `01/01/2038`** | Valor na Cotação Atual (`R$ 3.819/BNB`) |
| :--- | :---: | :---: | :---: | :---: |
| **1. Média Histórica do Backtest** | `+0,042% / dia` | `+16,6% / ano` | **`1,40 BNB`** | R$ 5.347,00 |
| **2. Ritmo Conservador** | `+0,10% / dia` | `+44,0% / ano` | **`14,81 BNB`** | R$ 56.551,00 |
| **3. Ritmo Moderado** | `+0,15% / dia` | `+72,8% / ano` | **`113,37 BNB`** | R$ 432.948,00 |
| **4. Ritmo Meta 256 BNB** | `+0,17% / dia` | `+85,9% / ano` | **`256,00 BNB`** | **R$ 977.664,00** |
| **5. Ritmo Forte** | `+0,20% / dia` | `+107,3% / ano` | **`866,97 BNB`** | **R$ 3.310.958,00** |

---

## Parte IV — Questões Técnicas do Sistema

### 13. De onde o script busca os candles diários e a cotação mais recente (`paresXlinks.json`)?
O arquivo `paresXlinks.json` possui **3 colunas** para cada um dos 6 pares (`XRPBNB`, `SOLBNB`, `TRXBNB`, `DOGEBNB`, `LTCBNB` e `BNBBRL`):
1. **Nome do Par (`SIMBOLO`):** define o arquivo local `<SIMBOLO>.json` (todos em letras maiúsculas, incluindo `BNBBRL.json`).
2. **Endpoint de Candles Diários (`new-otc/pair-klines`):**
   * Exemplo: `https://www.binance.com/bapi/margin/v1/friendly/new-otc/pair-klines?interval=1d&baseCoin=XRP&quoteCoin=BNB`
   * Fornece a série histórica atualizada de candles diários (`1d`).
3. **Endpoint de Cotação Mais Recente em Tempo Real (`new-otc/pair-price-change`):**
   * Exemplo: `https://www.binance.com/bapi/margin/v1/public/new-otc/pair-price-change?fromCoin=BNB&toCoin=XRP`
   * Busca o preço em tempo real, alinha automaticamente a direção da cotação (`preço` vs. `1/preço`) em relação ao último fechamento dos candles, atualiza o último candle e grava atomicamente o arquivo `<SIMBOLO>.json` local antes de alimentar os cálculos.

