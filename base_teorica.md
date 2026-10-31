# Base Teórica — Rebalanceamento Universal de Portfólios (Thomas M. Cover)

[← Voltar ao README principal](README.md)

---

## 1. A Teoria de Portfólios de Thomas M. Cover

**Thomas M. Cover (1938–2012)**, professor de Engenharia Elétrica e Estatística na Universidade de Stanford e autor do clássico *Elements of Information Theory*, desenvolveu uma abordagem matemática para alocação de capital baseada em **Teoria da Informação** (*Universal Portfolios*, *Mathematical Finance*, 1991). Em vez de tentar prever preços futuros ou assumir distribuições estatísticas para o mercado, o investidor extrai crescimento exponencial diretamente da **volatilidade relativa** entre os ativos por meio do rebalanceamento sistemático.

### 1.1. O Modelo de Mercado
Considere um mercado com $m$ ativos (onde o ativo de referência/caixa é o próprio **BNB**, cujo retorno em relação a si mesmo é `1,0`, e os demais ativos são altcoins cotadas em BNB).
Em cada período (candle diário) $t = 1, 2, \dots, n$, o comportamento do mercado é descrito por um vetor de retornos relativos:

$$
\mathbf{x}_t = (x_{t,1}, x_{t,2}, \dots, x_{t,m}), \quad x_{t,i} = \frac{\text{Fechamento}_{t,i}}{\text{Fechamento}_{t-1,i}}
$$

Um portfólio no período $t$ é definido por um vetor de pesos $\mathbf{b}_t$ pertencente ao simplex unitário:

$$
\mathbf{b}_t = (b_{t,1}, b_{t,2}, \dots, b_{t,m}) \in \Delta_m
$$

$$
\Delta_m = \left\lbrace \mathbf{b} \in \mathbb{R}^m : b_i \ge 0, \sum_{i=1}^{m} b_i = 1 \right\rbrace
$$

Após $n$ períodos, a riqueza acumulada (em unidades de **BNB**) por uma sequência de portfólios $\mathbf{b}_t$ é o produto dos retornos diários da carteira:

$$
S_n = \prod_{t=1}^{n} \mathbf{b}_t^\top \mathbf{x}_t = \prod_{t=1}^{n} \left( \sum_{i=1}^{m} b_{t,i} \, x_{t,i} \right)
$$

---

### 1.2. Portfólios Constantemente Rebalanceados (CRP)
Uma estratégia **CRP** (*Constant Rebalanced Portfolio*) mantém a mesma proporção fixa $\mathbf{b}$ em todos os períodos ($\mathbf{b}_t = \mathbf{b}$).
* Na prática, a cada período o investidor **vende parcialmente os ativos que subiram acima do peso-alvo** e **compra os ativos que caíram abaixo do peso-alvo**, restaurando exatamente as frações do vetor $\mathbf{b}$.
* A riqueza acumulada após $n$ períodos e sua taxa média de crescimento exponencial $W_n(\mathbf{b})$ são dadas por:

$$
S_n(\mathbf{b}) = \prod_{t=1}^{n} \mathbf{b}^\top \mathbf{x}_t = \exp\left( n \cdot W_n(\mathbf{b}) \right), \quad W_n(\mathbf{b}) = \frac{1}{n} \sum_{t=1}^{n} \ln(\mathbf{b}^\top \mathbf{x}_t)
$$

---

### 1.3. O Fenômeno de *Volatility Pumping* (Bombeamento de Volatilidade)
A propriedade mais surpreendente demonstrada por Cover (e relacionada ao critério de Kelly / *Shannon's Demon*) é que **um portfólio constantemente rebalanceado pode crescer exponencialmente mesmo quando nenhum dos ativos individuais cresce no longo prazo**.

**Exemplo clássico:**
Suponha que tenhamos **BNB** (retorno fixo `1,0`) e uma altcoin que, a cada período, dobra de preço em BNB (`× 2,0`) ou cai pela metade (`× 0,5`) em ciclos alternados:
* **Buy & Hold da Altcoin:** `× 2,0 → × 0,5 → × 2,0 → × 0,5` $\implies$ ganho líquido de **0%** (`1,00x`).
* **Buy & Hold de BNB:** ganho líquido de **0%** (`1,00x`).
* **CRP 50% / 50%:**
  * Nos dias de alta: `0,5 × 1,0 + 0,5 × 2,0 = 1,50`
  * Nos dias de queda: `0,5 × 1,0 + 0,5 × 0,5 = 0,75`
  * Em cada par de dias, o patrimônio em BNB é multiplicado por `1,50 × 0,75` = **1,125** (**+12,5% de lucro em BNB a cada ciclo completo**), puramente vendendo caro na alta e recomprando barato na baixa.

Matematicamente, pela concavidade estrita da função logaritmo (Desigualdade de Jensen), a taxa de crescimento do portfólio rebalanceado supera a média ponderada das taxas de crescimento dos ativos individuais pelo termo de **excesso de crescimento (ganho de rebalanceamento)**:

$$
\ln(\mathbf{b}^\top \mathbf{x}) > \sum_{i=1}^{m} b_i \ln(x_i)
$$

---

### 1.4. Melhor Portfólio Constantemente Rebalanceado (BCRP)
O **BCRP** (*Best Constant Rebalanced Portfolio*) é a carteira de pesos fixos $\mathbf{b}^*$ que teria maximizado a riqueza final caso o investidor conhecesse toda a sequência histórica de preços em retrospectiva:

$$
\mathbf{b}^* = \arg\max_{\mathbf{b} \in \Delta_m} S_n(\mathbf{b}) = \arg\max_{\mathbf{b} \in \Delta_m} \sum_{t=1}^{n} \ln(\mathbf{b}^\top \mathbf{x}_t)
$$

O BCRP possui propriedades notáveis sobre **qualquer** sequência de preços:
1. **Supera o melhor ativo individual do mercado:**

$$
S_n(\mathbf{b}^*) \ge \max_i S_n(\mathbf{e}_i)
$$

2. **Supera a média aritmética (Buy & Hold uniforme):**

$$
S_n(\mathbf{b}^*) \ge \sum_{i=1}^{m} b_i \, S_n(\mathbf{e}_i)
$$

3. **Supera a média geométrica dos ativos:**

$$
S_n(\mathbf{b}^*) \ge \prod_{i=1}^{m} S_n(\mathbf{e}_i)^{b_i}
$$

---

### 1.5. O Algoritmo do Portfólio Universal de Cover
Como $\mathbf{b}^*$ depende do conhecimento prévio dos preços futuros, Cover propôs o **Portfólio Universal**: em vez de escolher um único vetor $\mathbf{b}$ a priori, divide-se o capital inicial entre **todos os portfólios possíveis no simplex** segundo uma distribuição a priori $\mu(\mathbf{b})$ — tipicamente a distribuição de Jeffreys $\text{Dirichlet}(1/2, \dots, 1/2)$ — e deixa-se cada subcarteira crescer com sua própria riqueza acumulada $S_{t-1}(\mathbf{b})$.

No início do período $t$, o peso efetivo atribuído a cada ativo é a **média ponderada pelo desempenho acumulado** de todas as carteiras possíveis até $t-1$:

$$
\hat{\mathbf{b}}_t = \frac{\int_{\Delta_m} \mathbf{b} \, S_{t-1}(\mathbf{b}) \, d\mu(\mathbf{b})}{\int_{\Delta_m} S_{t-1}(\mathbf{b}) \, d\mu(\mathbf{b})}
$$

**Teorema Principal de Cover (1991):** Sem fazer **nenhuma suposição estatística** sobre os preços (mesmo sob sequências escolhidas de forma adversária), o Portfólio Universal atinge assintoticamente a **mesma taxa de crescimento exponencial de primeira ordem** do melhor portfólio em retrospectiva $S_n(\mathbf{b}^*)$:

$$
\lim_{n \to \infty} \frac{1}{n} \ln \frac{S_n(\mathbf{b}^*)}{\hat{S}_n} = 0
$$

Com a priori $\text{Dirichlet}(1/2, \dots, 1/2)$ (Cover & Ordentlich, 1996), o arrependimento logarítmico é limitado por $\frac{m-1}{2}\ln n + O(1)$.

---

### 1.6. Diferença Prática entre os 3 Modelos

| Modelo | Como Calcula os Pesos-Alvo | Ponto Forte | Ponto de Atenção |
| :--- | :--- | :--- | :--- |
| **`CRP` — Pesos Iguais (`1/N`)** | Divide o patrimônio igualmente entre todas as moedas marcadas como ativas (ex.: 7 moedas → **14,29%** em cada). | Máxima diversificação e captura toda oscilação entre os pares sem viés do passado. | Se uma moeda estiver em tendência secular de queda sem recuperação, continuará comprando-a até que seja desmarcada. |
| **`Universal` (`Dirichlet 1/2`)** *(Padrão)* | Simula milhares de carteiras no simplex $\Delta_m$ usando `Dirichlet(1/2)` ao longo dos 1000 candles e pondera cada uma pelo lucro real acumulado. | Equilíbrio ótimo entre diversificação e adaptação: sobrepondera as moedas que mais geram BNB, mantendo reserva tática nas demais para capturar reversões. | Reage de forma suave e progressiva (não zera completamente ativos secundários). |
| **`BCRP` — Ótimo Histórico** | Otimização por ponto fixo / gradiente exponenciado para encontrar os pesos exatos que maximizaram o estoque de BNB nos últimos 1000 candles. | Descarta automaticamente (**0,0%**) moedas que perderam valor estruturalmente contra o BNB e foca apenas nas vencedoras. | Pode concentrar excessivamente em poucos ativos caso o ciclo futuro seja diferente do ciclo passado (*overfitting*). |

---

## 2. Estudo Empírico e Backtest nos Pares de BNB (1000 Candles Diários)

O repositório acompanha séries históricas de **1.000 candles diários (`1d`)** da Binance cotadas diretamente em **BNB** (`DOGEBNB`, `LTCBNB`, `SOLBNB`, `TRXBNB`, `XRPBNB`, `ZECBNB`) e o par de conversão para Reais (`BNBBRL`). Como todas as altcoins estão cotadas em BNB, **qualquer ganho percentual acima de `1,00x` significa aumento real na quantidade de moedas BNB na carteira**.

### 2.1. Desempenho Individual dos Pares contra o BNB (Buy & Hold)

| Par | Período dos 1000 Candles | Preço Inicial (BNB) | Preço Final (BNB) | Retorno Buy & Hold (em BNB) |
| :--- | :---: | :---: | :---: | :---: |
| **`TRXBNB`** | Jul/2023 – Mar/2026 | `0,00033490` | `0,00038890` | **+16,12% (`1,1612x`)** |
| **`DOGEBNB`** | Abr/2019 – Jan/2022 | `0,00014780` | `0,00012940` | **-12,45% (`0,8755x`)** |
| **`XRPBNB`** | Jul/2023 – Mar/2026 | `0,00192200` | `0,00153200` | **-20,29% (`0,7971x`)** |
| **`SOLBNB`** | Jul/2023 – Mar/2026 | `0,07809000` | `0,03348000` | **-57,13% (`0,4287x`)** |
| **`LTCBNB`** | Jul/2023 – Mar/2026 | `0,39220000` | `0,09570000` | **-75,60% (`0,2440x`)** |
| **`ZECBNB`** | Nov/2020 – Ago/2023 | `2,04300000` | `0,10010000` | **-95,10% (`0,0490x`)** |

---

### 2.2. Análise de Quedas Violentas (*Maximum Drawdown*)
A eficácia do rebalanceamento depende crucialmente de distinguir entre **volatilidade cíclica** (queda seguida de recuperação) e **deterioração secular** (queda contínua sem retorno):

| Par | Maior Queda do Topo ao Fundo (*Max Drawdown*) | Maior Queda em 1 Único Dia | Comportamento Frente ao BNB |
| :--- | :---: | :---: | :--- |
| **`ZECBNB`** | **-96,58%** | -24,63% | **Colapso secular sem recuperação:** perdeu 95% do valor em BNB de ponta a ponta. |
| **`LTCBNB`** | **-78,67%** | -18,91% | **Tendência de baixa contínua:** perda estrutural de 3/4 do valor em BNB. |
| **`DOGEBNB`** | **-78,81%** | -37,63% | **Explosão episódica seguida de forte correção:** subiu +1.100% até Mai/2021 e recuou -78,8% depois. |
| **`XRPBNB`** | **-74,35%** | -16,82% | **Queda forte seguida de recuperação explosiva:** caiu até Jun/2024 e depois **triplicou** frente ao BNB. |
| **`SOLBNB`** | **-73,88%** | -14,25% | **Ciclo de alta seguido de correção severa:** subiu +237% até Ago/2024 e depois recuou -73,9%. |
| **`TRXBNB`** | **-59,87%** | -15,24% | **Oscilação saudável com tendência de alta:** bateu topo em Dez/2024, corrigiu e voltou a subir, encerrando no positivo (+16,12%). |

---

### 2.3. Resultados de Rebalanceamento Par a Par (Moeda + BNB)
Comparação de `1,00 BNB` inicial investido em cada par isolado contra o BNB (sem taxas):

| Par | Buy & Hold Moeda | Buy & Hold BNB | **CRP 50%/50%** | **Portfólio Universal** | **BCRP (Peso Ótimo Moeda / BNB)** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`TRX + BNB`** | `1,1612x` | `1,0000x` | **`1,1877x` (+18,77%)** | `1,1556x` (+15,56%) | **`1,2072x`** (73% TRX / 27% BNB) |
| **`XRP + BNB`** | `0,7971x` | `1,0000x` | **`1,0467x` (+4,67%)** | **`1,0247x` (+2,47%)** | **`1,0475x`** (46% XRP / 54% BNB) |
| **`DOGE + BNB`**| `0,8755x` | `1,0000x` | **`1,4649x` (+46,49%)** | **`1,3630x` (+36,30%)** | **`1,4658x`** (48% DOGE / 52% BNB) |
| **`SOL + BNB`** | `0,4287x` | `1,0000x` | `0,7802x` (-21,98%) | `0,8226x` (-17,74%) | `1,0000x` (0% SOL / 100% BNB) |
| **`LTC + BNB`** | `0,2440x` | `1,0000x` | `0,5619x` (-43,81%) | `0,6620x` (-33,80%) | `1,0000x` (0% LTC / 100% BNB) |
| **`ZEC + BNB`** | `0,0490x` | `1,0000x` | `0,2855x` (-71,45%) | `0,4668x` (-53,32%) | `1,0000x` (0% ZEC / 100% BNB) |

> **Destaque Empírico do *Volatility Pumping*:** Nos pares **`XRPBNB`** (-20,29%) e **`DOGEBNB`** (-12,45%), o ativo caiu em relação ao BNB no período total, mas o portfólio rebalanceado **gerou lucro positivo em BNB** (+4,67% em XRP e +46,49% em DOGE), superando simultaneamente o Buy & Hold de ambos os ativos.

---

### 2.4. Resultados em Portfólios Multimoedas (Janela Comum 2023–2026)

1. **Carteira com todas as 5 moedas contemporâneas (`BNB + LTC + SOL + TRX + XRP`):**
   * Média Buy & Hold (pesos iguais sem rebalancear): **`0,7988x` (-20,12%)**
   * **CRP Uniforme (20% cada):** **`0,9736x` (-2,64%)** — ganho de rebalanceamento de +17,48 pontos percentuais sobre o Buy & Hold.
   * **Portfólio Universal (`Dirichlet 1/2`):** **`0,9939x` (-0,61%)** — aprendeu a reduzir exposição a `LTC` e `SOL` e aumentou o peso em `TRX`, `BNB` e `XRP`.
   * **BCRP (Ótimo em Retrospectiva):** **`1,6425x` (+64,25% em BNB)** — pesos ótimos: **85,3% `TRX` + 14,7% `XRP`** (e 0% em `LTC` e `SOL`).

2. **Carteira Focada (`BNB + TRX + XRP`):**
   * **CRP Uniforme (1/3 cada):** **`1,3635x` (+36,35% em BNB)**
   * **Portfólio Universal:** **`1,3592x` (+35,92% em BNB)**
   * **BCRP:** **`1,6425x` (+64,25% em BNB)**

---

### 2.5. Impacto das Taxas de Corretagem e Limiar de Desvio
Na Binance Spot, a taxa padrão é de **0,10% por ordem** (0,075% pagando taxas em BNB). Rebalancear cegamente todos os dias para corrigir micro-oscilações consome parte do ganho de *volatility pumping*.
* **Solução implementada no sistema:** uso de um **Limiar de Desvio ($\tau$, padrão 1,0% a 2,0%)** ou execução semanal. Na cesta `BNB + TRX + XRP` com taxa de 0,10% por operação, o rebalanceamento acionado apenas quando o desvio supera o limiar gera **+52,35% de lucro líquido em BNB** (`1,5235x`, já descontadas todas as taxas).

