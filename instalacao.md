# Guia de Instalação e Configuração

[← Voltar ao README principal](README.md)

---

## 1. Requisitos do Sistema

* **Sistema Operacional:** Linux, macOS ou Windows.
* **Python 3.8 ou superior:**
  * O motor matemático (`rebalanceamento_cover.py`) utiliza **exclusivamente a biblioteca padrão do Python** (`math`, `random`, `hmac`, `hashlib`, `urllib.request`, `json`) — **não** requer `numpy` nem `pandas`.
* **PyQt5** (necessário apenas para abrir a interface gráfica `rebalanceamento_cover_gui.py`):
  * **Ubuntu / Debian / Linux Mint:**
    ```bash
    sudo apt update && sudo apt install -y python3-pyqt5
    ```
  * **Via `pip` (qualquer plataforma / ambiente virtual):**
    ```bash
    pip install PyQt5
    ```

---

## 2. Clonando o Repositório

```bash
git clone https://github.com/pilgerowski/coverbnb.git
cd coverbnb
```

---

## 3. Configuração das Chaves da Binance (`keys.json`) — Opcional

Para que o programa carregue automaticamente os saldos reais da sua carteira **Spot** na Binance ao iniciar, configure o arquivo `keys.json` na raiz do projeto.

### 3.1. Como criar uma Chave de API Segura (Somente Leitura) na Binance
1. Acesse sua conta na Binance e vá em **Perfil → Gerenciamento de API (*API Management*)**.
2. Clique em **Criar API (*Create API*)** → escolha **Chave de API gerada pelo sistema (*System generated*)**.
3. Nas permissões da chave, deixe marcada **APENAS** a opção **"Habilitar Leitura" (*Enable Reading*)** — **não** habilite saques nem permissões desnecessárias.
4. Copie a `API Key` e a `Secret Key` geradas.

### 3.2. Editando o arquivo `keys.json`
Abra o arquivo `keys.json` (que já vem com um modelo de exemplo) e substitua pelos seus dados seguindo o padrão JSON da Binance:

```json
{
  "apiKey": "SUA_API_KEY_DA_BINANCE_AQUI",
  "secretKey": "SUA_SECRET_KEY_DA_BINANCE_AQUI",
  "comment": "Chave de API da Binance (apenas permissao de Leitura / Read-Only)"
}
```

> **Observação:** Se você optar por **não** preencher o `keys.json` (mantendo os valores de exemplo), o sistema funcionará normalmente e iniciará com os campos da carteira zerados (`0`) para que você digite as quantidades manualmente.

---

## 4. Configuração dos Pares e Links (`paresXlinks.json`)

O arquivo `paresXlinks.json` define os pares cotados em `BNB` que compõem o portfólio e o par `BNBBRL` usado para converter os valores para Reais (`R$`):

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

Ao iniciar o script (com conexão à internet), para cada entrada `[SIMBOLO, URL_CANDLES, URL_PRECO_RECENTE]`:
1. Os candles diários (`1d`) são baixados a partir do **1º link** (`new-otc/pair-klines`);
2. A cotação mais recente em tempo real é obtida a partir do **2º link** (`new-otc/pair-price-change`);
3. Os dados atualizados são gravados nos arquivos `.json` locais correspondentes (`XRPBNB.json`, `SOLBNB.json`, `TRXBNB.json`, `DOGEBNB.json`, `LTCBNB.json` e `BNBBRL.json`) para uso imediato e *fallback* offline.

