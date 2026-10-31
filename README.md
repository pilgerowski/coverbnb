# CoverBNB — Rebalanceamento Universal de Portfólios para Acumulação de BNB

Aplicação prática da teoria de **Portfólios Constantemente Rebalanceados (CRP)** e **Portfólios Universais** de **Thomas M. Cover** (*Universal Portfolios*, *Mathematical Finance*, 1991) para negociação e acumulação de **BNB** frente a criptomoedas na **Binance**, com motor matemático em Python puro (sem dependências numéricas externas) e interface gráfica em **PyQt5**.

---

## Sumário

1. [Fundamentação Teórica — A Teoria de Portfólios de Thomas M. Cover](#1-fundamentação-teórica--a-teoria-de-portfólios-de-thomas-m-cover)
   - [1.1. O Modelo de Mercado](#11-o-modelo-de-mercado)
   - [1.2. Portfólios Constantemente Rebalanceados (CRP)](#12-portfólios-constantemente-rebalanceados-crp)
   - [1.3. O Fenômeno de Volatility Pumping (Bombeamento de Volatilidade)](#13-o-fenômeno-de-volatility-pumping-bombeamento-de-volatilidade)
   - [1.4. Melhor Portfólio Constantemente Rebalanceado (BCRP)](#14-melhor-portfólio-constantemente-rebalanceado-bcrp)
   - [1.5. O Algoritmo do Portfólio Universal de Cover](#15-o-algoritmo-do-portfólio-universal-de-cover)
   - [1.6. Diferença Prática entre os 3 Modelos no Sistema](#16-diferença-prática-entre-os-3-modelos-no-sistema)
2. [Estudo Empírico e Backtest nos Pares de BNB (1000 Candles Diários)](#2-estudo-empírico-e-backtest-nos-pares-de-bnb-1000-candles-diários)
   - [2.1. Desempenho Individual dos Pares contra o BNB](#21-desempenho-individual-dos-pares-contra-o-bnb)
   - [2.2. Análise de Quedas Violentas (Maximum Drawdown)](#22-análise-de-quedas-violentas-maximum-drawdown)
   - [2.3. Resultados de Rebalanceamento Par a Par (Moeda + BNB)](#23-resultados-de-rebalanceamento-par-a-par-moeda--bnb)
   - [2.4. Resultados em Portfólios Multimoedas](#24-resultados-em-portfólios-multimoedas)
   - [2.5. Impacto das Taxas de Corretagem e Limiar de Desvio](#25-impacto-das-taxas-de-corretagem-e-limiar-de-desvio)
3. [Funcionalidades do Sistema](#3-funcionalidades-do-sistema)
   - [3.1. Interface Gráfica (PyQt5)](#31-interface-gráfica-pyqt5)
   - [3.2. Modo Linha de Comando (CLI)](#32-modo-linha-de-comando-cli)
4. [Instalação e Configuração](#4-instalação-e-configuração)
   - [4.1. Requisitos](#41-requisitos)
   - [4.2. Configuração da Chave de API da Binance (keys.json)](#42-configuração-da-chave-de-api-da-binance-keysjson)
   - [4.3. Configuração dos Pares e Links (paresXlinks.json)](#43-configuração-dos-pares-e-links-paresxlinksjson)
5. [Como Executar](#5-como-executar)
6. [Recomendações Operacionais e Melhores Horários](#6-recomendações-operacionais-e-melhores-horários)
7. [Estrutura de Arquivos do Projeto](#7-estrutura-de-arquivos-do-projeto)

---

## 1. Fundamentação Teórica — A Teoria de Portfólios de Thomas M. Cover

**Thomas M. Cover (1938–2012)**, professor de Engenharia Elétrica e Estatística na Universidade de Stanford e autor do clássico *Elements of Information Theory*, desenvolveu uma abordagem revolucionária para alocação de capital baseada em **Teoria da Informação**: em vez de tentar prever preços futuros ou assumir distribuições estatísticas para o mercado, o investidor extrai crescimento exponencial diretamente da **volatilidade relativa** entre os ativos por meio do rebalanceamento sistemático.

### 1.1. O Modelo de Mercado
Considere um mercado com $m$ ativos (onde o ativo de referência/caixa é o próprio **BNB**, cujo retorno em relação a si mesmo é $1{,}0$, e os demais ativos são altcoins cotadas em BNB).
Em cada período (candle diário) $t = 1, 2, \dots, n$, o comportamento do mercado é descrito por um vetor de retornos relativos:

$$\mathbf{x}_t = (x_{t,1}, x_{t,2}, \dots, x_{t,m}), \quad x_{t,i} = \frac{\text{Fechamento}_{t,i}}{\text{Fechamento}_{t-1,i}}$$

Um portfólio no período $t$ é definido por um vetor de pesos $\mathbf{b}_t = (b_{t,1}, \dots, b_{t,m})$ pertencente ao simplex unitário:

$$\Delta_m = \left\{ \mathbf{b} \in \mathbb{R}^m : b_i \ge 0, \sum_{i=1}^{m} b_i = 1 \right\}$$

Após $n$ períodos, a riqueza acumulada (em unidades de **BNB**) por uma estratégia $\{\mathbf{b}_t\}$ é o produto dos retornos diários da carteira:

$$S_n = \prod_{t=1}^{n} \mathbf{b}_t^\top \mathbf{x}_t = \prod_{t=1}^{n} \left( \sum_{i=1}^{m} b_{t,i} x_{t,i} \right)$$

---

### 1.2. Portfólios Constantemente Rebalanceados (CRP)
Uma estratégia **CRP** (*Constant Rebalanced Portfolio*) mantém a mesma proporção fixa $\mathbf{b}$ em todos os períodos ($\mathbf{b}_t = \mathbf{b}$).
* Na prática, a cada período o investidor **vende parcialmente os ativos que subiram acima do peso-alvo** e **compra os ativos que caíram abaixo do peso-alvo**, restaurando exatamente as frações $b_1, \dots, b_m$.
* A riqueza acumulada após $n$ períodos é:

$$S_n(\mathbf{b}) = \prod_{t=1}^{n} \mathbf{b}^\top \mathbf{x}_t = \exp\left( n \cdot W_n(\mathbf{b}) \right)$$

onde $W_n(\mathbf{b}) = \frac{1}{n} \sum_{t=1}^{n} \ln(\mathbf{b}^\top \mathbf{x}_t)$ é a taxa média de crescimento exponencial da carteira.

---

### 1.3. O Fenômeno de *Volatility Pumping* (Bombeamento de Volatilidade)
A propriedade mais surpreendente demonstrada por Cover (e relacionada ao critério de Kelly / *Shannon's Demon*) é que **um portfólio constantemente rebalanceado pode crescer exponencialmente mesmo quando nenhum dos ativos individuais cresce no longo prazo**.

**Exemplo clássico:**
Suponha que tenhamos **BNB** (retorno fixo $1{,}0$) e uma altcoin que, a cada período, dobra de preço em BNB ($\times 2$) ou cai pela metade ($\times 0{,}5$) em ciclos alternados:
* **Buy & Hold da Altcoin:** $\times 2 \to \times 0{,}5 \to \times 2 \to \times 0{,}5 \implies$ ganho líquido de **$0\%$** ($1{,}00\text{x}$).
* **Buy & Hold de BNB:** ganho líquido de **$0\%$** ($1{,}00\text{x}$).
* **CRP $50\% / 50\%$:**
  * Nos dias de alta: $0{,}5(1) + 0{,}5(2) = 1{,}50$
  * Nos dias de queda: $0{,}5(1) + 0{,}5(0{,}5) = 0{,}75$
  * Em cada par de dias, o patrimônio em BNB é multiplicado por $1{,}50 \times 0{,}75 = \mathbf{1{,}125}$ (**$+12{,}5\%$ de lucro em BNB a cada ciclo completo**), puramente vendendo caro na alta e recomprando barato na baixa.

Matematicamente, pela concavidade estrita da função logaritmo (Desigualdade de Jensen), a taxa de crescimento do portfólio rebalanceado supera a média ponderada das taxas de crescimento dos ativos individuais pelo termo de **excesso de crescimento (ganho de rebalanceamento)**:

$$\ln(\mathbf{b}^\top \mathbf{x}) > \sum_{i=1}^{m} b_i \ln(x_i)$$

---

### 1.4. Melhor Portfólio Constantemente Rebalanceado (BCRP)
O **BCRP** (*Best Constant Rebalanced Portfolio*) é a carteira de pesos fixos $\mathbf{b}^*$ que teria maximizado a riqueza final caso o investidor conhecesse toda a sequência de preços $\mathbf{x}_1, \dots, \mathbf{x}_n$ em retrospectiva:

$$\mathbf{b}^* = \arg\max_{\mathbf{b} \in \Delta_m} S_n(\mathbf{b}) = \arg\max_{\mathbf{b} \in \Delta_m} \sum_{t=1}^{n} \ln(\mathbf{b}^\top \mathbf{x}_t)$$

O BCRP possui propriedades notáveis sobre **qualquer** sequência de preços:
1. Supera o melhor ativo individual do mercado: $S_n(\mathbf{b}^*) \ge \max_i S_n(\mathbf{e}_i)$.
2. Supera a média aritmética (Buy & Hold uniforme): $S_n(\mathbf{b}^*) \ge \sum b_i S_n(\mathbf{e}_i)$.
3. Supera a média geométrica dos ativos: $S_n(\mathbf{b}^*) \ge \prod S_n(\mathbf{e}_i)^{b_i}$.

---

### 1.5. O Algoritmo do Portfólio Universal de Cover
Como $\mathbf{b}^*$ depende do conhecimento prévio dos preços futuros, Cover propôs o **Portfólio Universal**: em vez de escolher um único vetor $\mathbf{b}$ a priori, divide-se o capital inicial entre **todos os portfólios $\mathbf{b} \in \Delta_m$ possíveis** segundo uma distribuição a priori $\mu(\mathbf{b})$ (tipicamente a distribuição uniforme ou a distribuição de Jeffreys $\text{Dirichlet}(1/2, \dots, 1/2)$) e deixa-se cada subcarteira crescer com sua própria riqueza $S_{t-1}(\mathbf{b})$.

No início do período $t$, o peso efetivo atribuído a cada ativo é a **média ponderada pelo desempenho acumulado** de todas as carteiras possíveis até $t-1$:

$$\hat{\mathbf{b}}_t = \frac{\int_{\Delta_m} \mathbf{b} \, S_{t-1}(\mathbf{b}) \, d\mu(\mathbf{b})}{\int_{\Delta_m} S_{t-1}(\mathbf{b}) \, d\mu(\mathbf{b})}$$

**Teorema Principal de Cover (1991):** Sem fazer **nenhuma suposição estatística** sobre os preços (mesmo sob sequências escolhidas de forma adversária), o Portfólio Universal atinge assintoticamente a **mesma taxa de crescimento exponencial de primeira ordem** do melhor portfólio em retrospectiva ($S_n^* = S_n(\mathbf{b}^*)$):

$$\lim_{n \to \infty} \frac{1}{n} \ln \frac{S_n(\mathbf{b}^*)}{\hat{S}_n} = 0$$

Com a priori $\text{Dirichlet}(1/2, \dots, 1/2)$ (Cover & Ordentlich, 1996), o arrependimento logarítmico é limitado por $\frac{m-1}{2}\ln n + O(1)$.

---

### 1.6. Diferença Prática entre os 3 Modelos no Sistema

| Modelo | Como Calcula os Pesos-Alvo | Ponto Forte | Ponto de Atenção |
| :--- | :--- | :--- | :--- |
| **`CRP` — Pesos Iguais ($1/N$)** | Divide o patrimônio igualmente entre todas as moedas marcadas como ativas (ex.: 7 moedas $\implies 14{,}29\%$ em cada). | Máxima diversificação e captura toda oscilação entre os pares sem viés do passado. | Se uma moeda estiver em tendência secular de queda sem recuperação, continuará comprando-a até que seja desmarcada. |
| **`Universal` ($\text{Dirichlet}(1/2)$)** *(Padrão)* | Simula milhares de carteiras no simplex $\Delta_m$ usando $\text{Dirichlet}(1/2)$ ao longo dos 1000 candles e pondera cada uma pelo lucro real acumulado. | Equilíbrio ótimo entre diversificação e adaptação: sobrepondera as moedas que mais geram BNB, mantendo reserva tática nas demais para capturar reversões. | Reage de forma suave e progressiva (não zera completamente ativos secundários). |
| **`BCRP` — Ótimo Histórico** | Otimização por ponto fixo / gradiente exponenciado para encontrar os pesos exatos que maximizaram o estoque de BNB nos últimos 1000 candles. | Descarta automaticamente ($0{,}0\%$) moedas que perderam valor estruturalmente contra o BNB e foca apenas nas vencedoras. | Pode concentrar excessivamente em poucos ativos caso o ciclo futuro seja diferente do ciclo passado (*overfitting*). |

---

## 2. Estudo Empírico e Backtest nos Pares de BNB (1000 Candles Diários)

O repositório acompanha séries históricas de **1.000 candles diários (`1d`)** da Binance cotadas diretamente em **BNB** (`DOGEBNB`, `LTCBNB`, `SOLBNB`, `TRXBNB`, `XRPBNB`, `ZECBNB`) e o par de conversão para Reais (`BNBBRL`). Como todas as altcoins estão cotadas em BNB, **qualquer ganho percentual acima de $1{,}00\text{x}$ significa aumento real na quantidade de moedas BNB na carteira**.

### 2.1. Desempenho Individual dos Pares contra o BNB (Buy & Hold)

| Par | Período dos 1000 Candles | Preço Inicial (BNB) | Preço Final (BNB) | Retorno Buy & Hold (em BNB) |
| :--- | :---: | :---: | :---: | :---: |
| **`TRXBNB`** | Jul/2023 – Mar/2026 | $0{,}00033490$ | $0{,}00038890$ | **$+16{,}12\%$ ($1{,}1612\text{x}$)** |
| **`DOGEBNB`** | Abr/2019 – Jan/2022 | $0{,}00014780$ | $0{,}00012940$ | **$-12{,}45\%$ ($0{,}8755\text{x}$)** |
| **`XRPBNB`** | Jul/2023 – Mar/2026 | $0{,}00192200$ | $0{,}00153200$ | **$-20{,}29\%$ ($0{,}7971\text{x}$)** |
| **`SOLBNB`** | Jul/2023 – Mar/2026 | $0{,}07809000$ | $0{,}03348000$ | **$-57{,}13\%$ ($0{,}4287\text{x}$)** |
| **`LTCBNB`** | Jul/2023 – Mar/2026 | $0{,}39220000$ | $0{,}09570000$ | **$-75{,}60\%$ ($0{,}2440\text{x}$)** |
| **`ZECBNB`** | Nov/2020 – Ago/2023 | $2{,}04300000$ | $0{,}10010000$ | **$-95{,}10\%$ ($0{,}0490\text{x}$)** |

---

### 2.2. Análise de Quedas Violentas (*Maximum Drawdown*)
A eficácia do rebalanceamento depende crucialmente de distinguir entre **volatilidade cíclica** (queda seguida de recuperação) e **deterioração secular** (queda contínua sem retorno):

| Par | Maior Queda do Topo ao Fundo (*Max Drawdown*) | Maior Queda em 1 Único Dia | Comportamento Frente ao BNB |
| :--- | :---: | :---: | :--- |
| **`ZECBNB`** | **$-96{,}58\%$** | $-24{,}63\%$ | **Colapso secular sem recuperação:** perdeu $95\%$ do valor em BNB de ponta a ponta. |
| **`LTCBNB`** | **$-78{,}67\%$** | $-18{,}91\%$ | **Tendência de baixa contínua:** perda estrutural de $3/4$ do valor em BNB. |
| **`DOGEBNB`** | **$-78{,}81\%$** | $-37{,}63\%$ | **Explosão episódica seguida de forte correção:** subiu $+1.100\%$ até Mai/2021 e recuou $-78{,}8\%$ depois. |
| **`XRPBNB`** | **$-74{,}35\%$** | $-16{,}82\%$ | **Queda forte seguida de recuperação explosiva:** caiu até Jun/2024 e depois **triplicou** frente ao BNB. |
| **`SOLBNB`** | **$-73{,}88\%$** | $-14{,}25\%$ | **Ciclo de alta seguido de correção severa:** subiu $+237\%$ até Ago/2024 e depois recuou $-73{,}9\%$. |
| **`TRXBNB`** | **$-59{,}87\%$** | $-15{,}24\%$ | **Oscilação saudável com tendência de alta:** bateu topo em Dez/2024, corrigiu e voltou a subir, encerrando no positivo ($+16{,}12\%$). |

---

### 2.3. Resultados de Rebalanceamento Par a Par (Moeda + BNB)
Comparação de $1{,}00\text{ BNB}$ inicial investido em cada par isolado contra o BNB (sem taxas):

| Par | Buy & Hold Moeda | Buy & Hold BNB | **CRP 50%/50%** | **Portfólio Universal** | **BCRP (Peso Ótimo Moeda / BNB)** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`TRX + BNB`** | $1{,}1612\text{x}$ | $1{,}0000\text{x}$ | **$1{,}1877\text{x}$ ($+18{,}77\%$)** | $1{,}1556\text{x}$ ($+15{,}56\%$) | **$1{,}2072\text{x}$** ($73\%$ TRX / $27\%$ BNB) |
| **`XRP + BNB`** | $0{,}7971\text{x}$ | $1{,}0000\text{x}$ | **$1{,}0467\text{x}$ ($+4{,}67\%$)** | **$1{,}0247\text{x}$ ($+2{,}47\%$)** | **$1{,}0475\text{x}$** ($46\%$ XRP / $54\%$ BNB) |
| **`DOGE + BNB`**| $0{,}8755\text{x}$ | $1{,}0000\text{x}$ | **$1{,}4649\text{x}$ ($+46{,}49\%$)** | **$1{,}3630\text{x}$ ($+36{,}30\%$)** | **$1{,}4658\text{x}$** ($48\%$ DOGE / $52\%$ BNB) |
| **`SOL + BNB`** | $0{,}4287\text{x}$ | $1{,}0000\text{x}$ | $0{,}7802\text{x}$ ($-21{,}98\%$) | $0{,}8226\text{x}$ ($-17{,}74\%$) | $1{,}0000\text{x}$ ($0\%$ SOL / $100\%$ BNB) |
| **`LTC + BNB`** | $0{,}2440\text{x}$ | $1{,}0000\text{x}$ | $0{,}5619\text{x}$ ($-43{,}81\%$) | $0{,}6620\text{x}$ ($-33{,}80\%$) | $1{,}0000\text{x}$ ($0\%$ LTC / $100\%$ BNB) |
| **`ZEC + BNB`** | $0{,}0490\text{x}$ | $1{,}0000\text{x}$ | $0{,}2855\text{x}$ ($-71{,}45\%$) | $0{,}4668\text{x}$ ($-53{,}32\%$) | $1{,}0000\text{x}$ ($0\%$ ZEC / $100\%$ BNB) |

> **Destaque Empírico do *Volatility Pumping*:** Nos pares **`XRPBNB`** ($-20{,}29\%$) e **`DOGEBNB`** ($-12{,}45\%$), o ativo caiu em relação ao BNB no período total, mas o portfólio rebalanceado **gerou lucro positivo em BNB** ($+4{,}67\%$ em XRP e $+46{,}49\%$ em DOGE), superando simultaneamente o Buy & Hold de ambos os ativos.

---

### 2.4. Resultados em Portfólios Multimoedas (Janela Comum 2023–2026)

1. **Carteira com todas as 5 moedas contemporâneas (`BNB + LTC + SOL + TRX + XRP`):**
   * Média Buy & Hold (pesos iguais sem rebalancear): **$0{,}7988\text{x}$ ($-20{,}12\%$)**
   * **CRP Uniforme ($20\%$ cada):** **$0{,}9736\text{x}$ ($-2{,}64\%$)** — ganho de rebalanceamento de $+17{,}48$ pontos percentuais sobre o Buy & Hold.
   * **Portfólio Universal ($\text{Dirichlet}(1/2)$):** **$0{,}9939\text{x}$ ($-0{,}61\%$)** — aprendeu a reduzir exposição a `LTC` e `SOL` e aumentou o peso em `TRX`, `BNB` e `XRP`.
   * **BCRP (Ótimo em Retrospectiva):** **$1{,}6425\text{x}$ ($+64{,}25\%$ em BNB)** — pesos ótimos: **$85{,}3\%$ `TRX` + $14{,}7\%$ `XRP`** (e $0\%$ em `LTC` e `SOL`).

2. **Carteira Focada (`BNB + TRX + XRP`):**
   * **CRP Uniforme ($1/3$ cada):** **$1{,}3635\text{x}$ ($+36{,}35\%$ em BNB)**
   * **Portfólio Universal:** **$1{,}3592\text{x}$ ($+35{,}92\%$ em BNB)**
   * **BCRP:** **$1{,}6425\text{x}$ ($+64{,}25\%$ em BNB)**

---

### 2.5. Impacto das Taxas de Corretagem e Limiar de Desvio
Na Binance Spot, a taxa padrão é de **$0{,}10\%$ por ordem** ($0{,}075\%$ pagando taxas em BNB). Rebalancear cegamente todos os dias para corrigir micro-oscilações consome parte do ganho de *volatility pumping*.
* **Solução implementada no sistema:** uso de um **Limiar de Desvio ($\tau$, padrão $1{,}0\%$ a $2{,}0\%$)** ou execução semanal. Na cesta `BNB + TRX + XRP` com taxa de $0{,}10\%$ por operação, o rebalanceamento acionado apenas quando o desvio supera o limiar gera **$+52{,}35\%$ de lucro líquido em BNB** ($1{,}5235\text{x}$, já descontadas todas as taxas).

---

## 3. Funcionalidades do Sistema

### 3.1. Interface Gráfica (`rebalanceamento_cover_gui.py`)
Interface desenvolvida em **PyQt5** com tema escuro (padrão visual Binance):
* **Inicialização Inteligente em Segundo Plano (`PriceFetchWorker`):**
  * Atualiza automaticamente os candles diários a partir das URLs em `paresXlinks.json` (atualizando os arquivos `.json` locais e utilizando-os automaticamente como *fallback* caso não haja conexão).
  * Carrega automaticamente os saldos reais da carteira **Spot** na Binance caso o arquivo `keys.json` esteja configurado com chaves válidas de leitura; caso contrário, inicia com os campos zerados (`0`) para preenchimento manual.
* **Layout Compacto e Adaptável:**
  * Cabeçalho enxuto (`34px` de altura) exibindo **Patrimônio Total em BNB**, **Patrimônio em Reais (R$)**, **Cotação `BNBBRL`** e **Resumo de Ordens**.
  * Largura ajustada automaticamente à geometria útil do monitor (`availableGeometry()`).
* **Painel de Carteiras e Simulação sob Demanda:**
  * Modelo **Portfólio Universal (Dirichlet 1/2)** pré-selecionado por padrão (com opção de alternar para `CRP` ou `BCRP`).
  * Checkboxes individuais para ativar/desativar qualquer moeda do cálculo de pesos-alvo (ex.: desmarcar moedas em queda secular mantendo apenas as desejadas).
  * Tabela superior dimensionada sob medida para as **7 carteiras (`BNB`, `XRP`, `SOL`, `TRX`, `ZEC`, `DOGE`, `LTC`)**, exibindo Saldo Atual, Cotação em BNB, Valor em BNB e R$, Peso Atual vs. Peso Alvo, Diferença e Ação Recomendada (`VENDA`, `COMPRA` ou `MANTER`).
  * Painel inferior amplo dedicado ao **Passo a Passo de Execução na Binance**, listando primeiro todas as **VENDAS** (para liberar BNB em caixa) e depois todas as **COMPRAS** (já descontando a taxa spot de $0{,}10\%$).
  * Cálculo acionado sob demanda ao clicar em **"⚡ Simular Ordens"**.
* **Registro de Histórico (`historico_carteira.json`):**
  * Botão **"💾 Salvar Histórico"** que grava data/hora, quantidades, cotações, patrimônio total em BNB e R$, pesos-alvo e ordens sugeridas, além de janela modal (**"📜 Ver Histórico"**) para consulta de registros anteriores.

### 3.2. Modo Linha de Comando (`rebalanceamento_cover.py`)
Pode ser executado diretamente no terminal de forma interativa ou automatizada via argumentos de linha de comando (`--estrategia`, `--limiar`, `--saldos`, `--offline`, `--ativos`, `--sem-historico`, `--gui`).

---

## 4. Instalação e Configuração

### 4.1. Requisitos
* **Python 3.8+** (utiliza apenas a biblioteca padrão do Python para toda a matemática de otimização, amostragem de Dirichlet e requisições HTTPS/HMAC — **não** requer `numpy` ou `pandas`).
* **PyQt5** (apenas para a interface gráfica):
  ```bash
  sudo apt install python3-pyqt5
  # ou via pip:
  pip install PyQt5
  ```

### 4.2. Configuração da Chave de API da Binance (`keys.json`)
Para que a interface carregue automaticamente os saldos da sua conta Spot ao iniciar, edite o arquivo `keys.json` na raiz do projeto seguindo o formato padrão da Binance:

```json
{
  "apiKey": "SUA_API_KEY_AQUI",
  "secretKey": "SUA_SECRET_KEY_AQUI",
  "comment": "Chave de API da Binance (apenas permissao de Leitura / Read-Only)"
}
```

> **Segurança:** Ao criar sua chave em *Gerenciamento de API* na Binance, mantenha marcada **apenas** a opção **"Habilitar Leitura" (*Enable Reading*)**. O sistema utiliza os endpoints de leitura (`GET /api/v3/account` e `POST /sapi/v3/asset/getUserAsset`) assinados com `HMAC-SHA256` e sincronizados com o `serverTime` oficial da Binance (`/api/v3/time`). Caso `keys.json` contenha os valores de exemplo, o programa inicia normalmente com os saldos zerados para preenchimento manual.

### 4.3. Configuração dos Pares e Links (`paresXlinks.json`)
O arquivo `paresXlinks.json` define os pares monitorados e suas respectivas URLs de candles diários (`interval=1d&limit=1000`):

```json
[
  ["XRPBNB", "https://api.binance.com/api/v3/uiKlines?symbol=XRPBNB&interval=1d&limit=1000"],
  ["SOLBNB", "https://api.binance.com/api/v3/uiKlines?symbol=SOLBNB&interval=1d&limit=1000"],
  ["TRXBNB", "https://api.binance.com/api/v3/uiKlines?symbol=TRXBNB&interval=1d&limit=1000"],
  ["ZECBNB", "https://api.binance.com/api/v3/uiKlines?symbol=ZECBNB&interval=1d&limit=1000"],
  ["DOGEBNB", "https://api.binance.com/api/v3/uiKlines?symbol=DOGEBNB&interval=1d&limit=1000"],
  ["LTCBNB", "https://api.binance.com/api/v3/uiKlines?symbol=LTCBNB&interval=1d&limit=1000"],
  ["BNBBRL", "https://api.binance.com/api/v3/uiKlines?symbol=BNBBRL&interval=1d&limit=1000"]
]
```

---

## 5. Como Executar

### Interface Gráfica (Recomendado)
```bash
python3 rebalanceamento_cover_gui.py
```
Ou através do script principal:
```bash
python3 rebalanceamento_cover.py --gui
```

### Linha de Comando (CLI)
* **Modo interativo (busca cotações online e pergunta saldos no terminal):**
  ```bash
  python3 rebalanceamento_cover.py
  ```
* **Passando saldos, estratégia e limiar diretamente por parâmetros:**
  ```bash
  python3 rebalanceamento_cover.py \
    --saldos "BNB=2.5,XRP=500,SOL=3,TRX=2000,ZEC=0,DOGE=1000,LTC=1" \
    --estrategia universal \
    --limiar 2.0
  ```
* **Focando apenas em um subconjunto de moedas ativas (ex.: `BNB`, `TRX` e `XRP`):**
  ```bash
  python3 rebalanceamento_cover.py \
    --saldos "BNB=2.5,XRP=500,TRX=2000" \
    --ativos "BNB,TRX,XRP" \
    --estrategia universal
  ```
* **Modo Offline (usando apenas os arquivos `.json` locais):**
  ```bash
  python3 rebalanceamento_cover.py --offline
  ```

---

## 6. Recomendações Operacionais e Melhores Horários

1. **Melhor Horário para Atualização dos Candles (21:05 às 21:15 BRT / UTC-3):**
   * O candle diário (`1d`) da Binance fecha exatamente à **00:00 UTC** (**21:00 no horário de Brasília**).
   * Executar o script entre **21:05 e 21:15 (BRT)** garante que o candle diário recém-fechado já foi consolidado, alimentando o modelo Universal ($\text{Dirichlet}(1/2)$) e o BCRP com 1000 dias completos.
2. **Melhor Janela de Liquidez para Execução de Ordens (10:00 às 13:00 BRT):**
   * Caso execute ordens de volume maior, o horário entre **10:00 e 13:00 (BRT)** concentra a sobreposição dos mercados europeu e norte-americano, oferecendo menor *spread* nos livros de ofertas dos pares cotados em BNB.
3. **Ordem de Execução na Binance:**
   * Execute sempre as ordens de **VENDA (`Par -> BNB`) primeiro** para liberar saldo livre em BNB, e em seguida execute as ordens de **COMPRA (`BNB -> Par`)**.

---

## 7. Estrutura de Arquivos do Projeto

| Arquivo | Descrição |
| :--- | :--- |
| `rebalanceamento_cover.py` | Motor matemático (CRP, Portfólio Universal Dirichlet 1/2, BCRP), cliente HTTP/HMAC da API da Binance, persistência de histórico e interface de linha de comando (CLI). |
| `rebalanceamento_cover_gui.py` | Interface gráfica em `PyQt5` para visualização da carteira em BNB e BRL, seleção de modelos e simulação passo a passo das ordens. |
| `paresXlinks.json` | Configuração dos pares negociados contra `BNB` (+ `BNBBRL`) e URLs da API de candles da Binance. |
| `keys.json` | Arquivo de configuração das chaves de leitura da API da Binance (`apiKey` e `secretKey`). |
| `run.sh` | Script auxiliar para execução rápida via linha de comando. |
| `DOGEBNB.json`, `LTCBNB.json`, `SOLBNB.json`, `TRXBNB.json`, `XRPBNB.json`, `ZECBNB.json`, `bnbbrl.json` | Séries históricas locais de 1000 candles diários (atualizadas automaticamente quando online e utilizadas como fallback quando offline). |
| `historico_carteira.json` | Gerado automaticamente ao salvar leituras da carteira (ignorado pelo Git via `.gitignore`). |
