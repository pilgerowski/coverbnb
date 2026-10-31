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
  ["XRPBNB", "https://api.binance.com/api/v3/uiKlines?symbol=XRPBNB&interval=1d&limit=1000"],
  ["SOLBNB", "https://api.binance.com/api/v3/uiKlines?symbol=SOLBNB&interval=1d&limit=1000"],
  ["TRXBNB", "https://api.binance.com/api/v3/uiKlines?symbol=TRXBNB&interval=1d&limit=1000"],
  ["ZECBNB", "https://api.binance.com/api/v3/uiKlines?symbol=ZECBNB&interval=1d&limit=1000"],
  ["DOGEBNB", "https://api.binance.com/api/v3/uiKlines?symbol=DOGEBNB&interval=1d&limit=1000"],
  ["LTCBNB", "https://api.binance.com/api/v3/uiKlines?symbol=LTCBNB&interval=1d&limit=1000"],
  ["BNBBRL", "https://api.binance.com/api/v3/uiKlines?symbol=BNBBRL&interval=1d&limit=1000"]
]
```

Ao iniciar o script (com conexão à internet), os últimos 1.000 candles diários de cada par são baixados automaticamente a partir desses links e salvos nos arquivos `.json` correspondentes (`XRPBNB.json`, `SOLBNB.json`, etc.) para uso imediato e fallback offline.

