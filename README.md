# CoverBNB — Rebalanceamento de Portfólios de Thomas M. Cover para Acumulação de BNB

Ferramenta em Python (modo gráfico **PyQt5** e linha de comando **CLI**) que aplica a teoria de **Portfólios Constantemente Rebalanceados (`CRP`)**, **Portfólios Universais (`Dirichlet 1/2`)** e **Melhor Portfólio Constante (`BCRP`)** de **Thomas M. Cover** para acumular **BNB** operando pares de criptomoedas na **Binance** (`XRPBNB`, `SOLBNB`, `TRXBNB`, `ZECBNB`, `DOGEBNB`, `LTCBNB` e conversão para Reais via `BNBBRL`).

---

## 📚 Documentação do Projeto

* 📘 **[Base Teórica e Backtest (`base_teorica.md`)](base_teorica.md)** — Fundamentação matemática da Teoria de Portfólios de Thomas M. Cover, *Volatility Pumping*, diferenças entre os modelos `CRP`, `Universal (Dirichlet 1/2)` e `BCRP`, análise de *Maximum Drawdown* e resultados dos backtests em 1.000 candles diários.
* ⚙️ **[Detalhes Técnicos e Implementação (`implementacao.md`)](implementacao.md)** — Arquitetura interna do motor matemático em Python puro, integração `HMAC-SHA256` com a API Spot da Binance, funcionamento da interface gráfica `PyQt5`, horários recomendados de operação e estrutura de arquivos.
* 🛠️ **[Guia de Instalação e Configuração (`instalacao.md`)](instalacao.md)** — Requisitos (`Python 3.8+` e `PyQt5`), criação e configuração segura das chaves de leitura em `keys.json` e configuração dos links de candles em `paresXlinks.json`.

---

## 🚀 Execução Rápida

### 1. Interface Gráfica (`PyQt5`)
Para abrir a janela gráfica (que atualiza automaticamente os candles a partir de `paresXlinks.json`, carrega o saldo Spot via `keys.json` e utiliza o modelo **Dirichlet 1/2** por padrão):

```bash
python3 rebalanceamento_cover_gui.py
```
Ou usando a opção `--gui` do script principal:
```bash
python3 rebalanceamento_cover.py --gui
```

### 2. Modo Interativo no Terminal (CLI)
```bash
python3 rebalanceamento_cover.py
```

---

## 🎛️ Opções Detalhadas de `rebalanceamento_cover.py`

Sintaxe geral:
```bash
python3 rebalanceamento_cover.py [--gui] [--offline] [--estrategia {crp,universal,bcrp}] [--apenas-ativas] [--saldos SALDOS] [--limiar LIMIAR]
```

### Tabela de Parâmetros

| Opção / Flag | Valores Aceitos | Padrão | Descrição Detalhada |
| :--- | :---: | :---: | :--- |
| **`--gui`** | *(flag booleana)* | Desativado | Inicia diretamente a interface gráfica em **PyQt5** (`rebalanceamento_cover_gui.py`) em vez do modo texto no terminal. |
| **`--estrategia`** | `crp`<br>`universal`<br>`bcrp` | Interativo *(ou `crp` quando `--saldos` é usado)* | Define o modelo matemático de Tom Cover para calcular os pesos-alvo:<br>• **`universal`**: Portfólio Universal de Cover com distribuição *a priori* `Dirichlet(1/2)` ponderada pelo desempenho histórico nos últimos 1.000 candles.<br>• **`crp`**: Pesos iguais (`1/N`) distribuídos uniformemente entre as moedas ativas.<br>• **`bcrp`**: Melhor Portfólio Constante em retrospectiva (otimização por ponto fixo que maximizou o retorno em BNB nos últimos 1.000 candles). |
| **`--limiar`** | Número decimal (`float`, em `%`) | `1.0` | Define o **desvio mínimo percentual** entre o peso atual e o peso-alvo (`\|peso_atual - peso_alvo\| >= limiar`) para que uma ordem de `COMPRA` ou `VENDA` seja sugerida. Ativos cujo desvio seja menor que `--limiar` recebem a recomendação `MANTER`, evitando pagar taxas de corretagem (`0,10%`) em micro-oscilações. |
| **`--saldos`** | String `CHAVE=VALOR` ou JSON | Leitura via `keys.json` / prompt interativo | Permite informar as quantidades atuais de cada moeda diretamente pela linha de comando (sem perguntas interativas no terminal). Aceita dois formatos:<br>• **Lista `MOEDA=QTD`:** `"BNB=2.5,XRP=500,SOL=3,TRX=2000"`<br>• **String JSON:** `'{"BNB": 2.5, "XRP": 500, "TRX": 2000}'`<br>Moedas omitidas na string assumem saldo `0.0`. |
| **`--apenas-ativas`** | *(flag booleana)* | Desativado | Quando ativada, restringe o cálculo de rebalanceamento **apenas às moedas que já possuem saldo maior que zero (`> 0`) na carteira** (além do próprio `BNB`). Moedas com saldo `0` recebem peso-alvo `0%` e não geram sugestões de compra. |
| **`--offline`** | *(flag booleana)* | Desativado | Força o script a **não** realizar requisições de rede à API da Binance, lendo exclusivamente os arquivos de candles locais (`XRPBNB.json`, `SOLBNB.json`, `TRXBNB.json`, `ZECBNB.json`, `DOGEBNB.json`, `LTCBNB.json` e `bnbbrl.json`). |
| **`-h`**, **`--help`** | *(flag booleana)* | — | Exibe o resumo de ajuda com todas as opções disponíveis e encerra. |

---

## 💡 Exemplos Práticos de Uso na Linha de Comando

1. **Executar com o modelo Universal (`Dirichlet 1/2`) e limiar de desvio de `2,0%` (perguntando/confirmando os saldos no terminal):**
   ```bash
   python3 rebalanceamento_cover.py --estrategia universal --limiar 2.0
   ```

2. **Execução 100% não-interativa passando os saldos por parâmetro (`CHAVE=VALOR`):**
   ```bash
   python3 rebalanceamento_cover.py \
     --estrategia universal \
     --limiar 1.5 \
     --saldos "BNB=1.5,XRP=400,TRX=3000,SOL=2.0,DOGE=1500,LTC=0,ZEC=0"
   ```

3. **Rebalancear somente entre as moedas que você já possui em carteira (`--apenas-ativas`), ignorando moedas zeradas:**
   ```bash
   python3 rebalanceamento_cover.py \
     --estrategia universal \
     --apenas-ativas \
     --saldos "BNB=2.0,XRP=600,TRX=4000"
   ```

4. **Simular usando o modelo `BCRP` (Ótimo Histórico) em modo totalmente `--offline`:**
   ```bash
   python3 rebalanceamento_cover.py --offline --estrategia bcrp --limiar 2.0
   ```
