#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface Gráfica (PyQt5) — Rebalanceamento de Portfólio de Tom Cover (Acumulação de BNB)
-----------------------------------------------------------------------------------------
Utiliza as funções de cálculo e busca de dados de `rebalanceamento_cover.py` e o arquivo
`paresXlinks.json` para:
  1. Atualizar cotações online da Binance (ou usar os JSONs locais como fallback)
  2. Informar quanto há de cada moeda na carteira no momento
  3. Exibir o valor da carteira em BNB e convertido para Reais (BRL)
  4. Apresentar sugestões visuais de VENDA e COMPRA segundo Tom Cover (CRP, Universal, BCRP)
  5. Armazenar cada leitura com data e hora em `historico_carteira.json`
"""

import json
import os
import sys
from datetime import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

import rebalanceamento_cover as core


class PriceFetchWorker(QtCore.QThread):
    """Thread em segundo plano para buscar cotações e saldo Spot (keys.json) sem travar a interface."""

    finished_signal = QtCore.pyqtSignal(dict, float, str, list, dict, str, bool)
    error_signal = QtCore.pyqtSignal(str)

    def __init__(self, pairs_links: list, offline: bool = False):
        super().__init__()
        self.pairs_links = pairs_links
        self.offline = offline

    def run(self):
        try:
            coin_data = {}
            bnb_brl_price = None
            bnb_brl_source = ""
            coins_order = ["BNB"]

            for item in self.pairs_links:
                symbol = item[0].strip().upper()
                url = item[1].strip()
                klines, source = core.fetch_klines(symbol, url, offline=self.offline)
                series, last_close, last_time_ms = core.parse_close_series(klines)
                dt_str = datetime.fromtimestamp(last_time_ms / 1000.0).strftime(
                    "%Y-%m-%d %H:%M"
                )

                if symbol == "BNBBRL":
                    bnb_brl_price = last_close
                    bnb_brl_source = f"{source} ({dt_str})"
                elif symbol.endswith("BNB"):
                    coin = symbol[:-3]
                    coins_order.append(coin)
                    coin_data[coin] = {
                        "symbol": symbol,
                        "price_bnb": last_close,
                        "series": series,
                        "last_time": dt_str,
                        "source": source,
                    }

            if bnb_brl_price is None:
                raise RuntimeError("Par BNBBRL não encontrado em paresXlinks.json.")

            if not self.offline:
                spot_balances, spot_msg, spot_ok = core.fetch_spot_balances(
                    coins_order
                )
            else:
                spot_balances, spot_msg, spot_ok = {}, "Modo offline", False

            self.finished_signal.emit(
                coin_data,
                bnb_brl_price,
                bnb_brl_source,
                coins_order,
                spot_balances,
                spot_msg,
                spot_ok,
            )
        except Exception as exc:
            self.error_signal.emit(str(exc))


class CoverRebalancerWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Tom Cover Portfolio Rebalancer — Acumulação de BNB (BNB & BRL)"
        )
        screen = QtWidgets.QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            w = min(1020, int(avail.width() * 0.90))
            h = min(650, int(avail.height() * 0.86))
            self.resize(w, h)
        else:
            self.resize(980, 620)
        self.setMinimumSize(720, 460)

        self.pairs_links = []
        self.coin_data = {}
        self.bnb_brl_price = 0.0
        self.bnb_brl_source = ""
        self.coins_order = ["BNB"]
        self.qty_inputs = {}
        self.active_checks = {}
        self.last_computed = None

        self._apply_dark_theme()
        self._build_ui()
        self._load_links_and_fetch(offline=False)

    def _apply_dark_theme(self):
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #181A20;
                color: #EAECEF;
                font-family: 'Segoe UI', 'Ubuntu', 'DejaVu Sans', sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #2B3139;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #F0B90B;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QLineEdit, QComboBox, QDoubleSpinBox {
                background-color: #2B3139;
                border: 1px solid #474D57;
                border-radius: 5px;
                padding: 5px 8px;
                color: #EAECEF;
                selection-background-color: #F0B90B;
                selection-color: #181A20;
            }
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #F0B90B;
            }
            QPushButton {
                background-color: #2B3139;
                border: 1px solid #474D57;
                border-radius: 6px;
                padding: 8px 14px;
                color: #EAECEF;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #363C45;
                border-color: #F0B90B;
            }
            QPushButton#primaryBtn {
                background-color: #F0B90B;
                border-color: #F0B90B;
                color: #181A20;
            }
            QPushButton#primaryBtn:hover {
                background-color: #FCD535;
            }
            QPushButton#successBtn {
                background-color: #0ECB81;
                border-color: #0ECB81;
                color: #181A20;
            }
            QPushButton#successBtn:hover {
                background-color: #26DF95;
            }
            QTableWidget {
                background-color: #1E2329;
                alternate-background-color: #232830;
                gridline-color: #2B3139;
                border: 1px solid #2B3139;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #2B3139;
                color: #B7BDC6;
                font-weight: bold;
                padding: 6px;
                border: none;
                border-right: 1px solid #1E2329;
                border-bottom: 1px solid #1E2329;
            }
            QTabWidget::pane {
                border: 1px solid #2B3139;
                border-radius: 6px;
                background-color: #1E2329;
            }
            QTabBar::tab {
                background-color: #2B3139;
                color: #B7BDC6;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #F0B90B;
                color: #181A20;
            }
            QTextEdit {
                background-color: #1E2329;
                border: 1px solid #2B3139;
                border-radius: 6px;
                padding: 8px;
                color: #EAECEF;
                font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
            }
            QCheckBox {
                spacing: 6px;
            }
            """
        )

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # 1. TOP SUMMARY BAR (1/3 da altura original: barra compacta de 34px)
        cards_layout = QtWidgets.QHBoxLayout()
        cards_layout.setSpacing(6)
        cards_layout.setContentsMargins(0, 0, 0, 0)

        self.card_bnb_val = self._create_summary_card(
            "Total BNB:",
            "0.000000 BNB",
            "Meta: acumular BNBs via bombeamento de volatilidade",
            "#F0B90B",
        )
        self.card_brl_val = self._create_summary_card(
            "Total BRL:",
            "R$ 0,00",
            "Conversão pelo par BNBBRL",
            "#0ECB81",
        )
        self.card_bnb_price = self._create_summary_card(
            "BNBBRL:",
            "R$ 0,00",
            "Carregando...",
            "#EAECEF",
        )
        self.card_evolution = self._create_summary_card(
            "Evolução:",
            "Sem histórico",
            "Salve um registro para acompanhar a evolução",
            "#3861FB",
        )

        cards_layout.addWidget(self.card_bnb_val["frame"], 1)
        cards_layout.addWidget(self.card_brl_val["frame"], 1)
        cards_layout.addWidget(self.card_bnb_price["frame"], 1)
        cards_layout.addWidget(self.card_evolution["frame"], 1)
        main_layout.addLayout(cards_layout)

        # 2. MIDDLE SPLITTER: LEFT (INPUTS & CONFIG) | RIGHT (TABLES & ORDERS)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # --- LEFT PANEL ---
        left_widget = QtWidgets.QWidget()
        left_widget.setMaximumWidth(350)
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(6)

        # Group: Quantidades Atuais
        self.holdings_group = QtWidgets.QGroupBox(
            "1. Quantidades na Carteira"
        )
        self.holdings_form_layout = QtWidgets.QGridLayout(self.holdings_group)
        self.holdings_form_layout.setSpacing(5)
        self.holdings_form_layout.setContentsMargins(8, 10, 8, 8)
        left_layout.addWidget(self.holdings_group)

        # Group: Parâmetros de Tom Cover
        config_group = QtWidgets.QGroupBox("2. Estratégia de Tom Cover")
        config_layout = QtWidgets.QFormLayout(config_group)
        config_layout.setSpacing(6)
        config_layout.setContentsMargins(8, 10, 8, 8)

        self.strategy_combo = QtWidgets.QComboBox()
        self.strategy_combo.addItem(
            "Portfólio Universal (Dirichlet 1/2)", "universal"
        )
        self.strategy_combo.addItem("CRP — Pesos Iguais (1/N)", "crp")
        self.strategy_combo.addItem("BCRP — Ótimo Histórico", "bcrp")
        self.strategy_combo.setCurrentIndex(0)
        config_layout.addRow("Modelo:", self.strategy_combo)

        self.threshold_spin = QtWidgets.QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 25.0)
        self.threshold_spin.setSingleStep(0.5)
        self.threshold_spin.setDecimals(1)
        self.threshold_spin.setSuffix(" %")
        self.threshold_spin.setValue(1.0)
        self.threshold_spin.setToolTip(
            "Só sugere COMPRA ou VENDA se o peso do ativo desviar mais do que este percentual."
        )
        config_layout.addRow("Desvio Mín.:", self.threshold_spin)

        left_layout.addWidget(config_group)

        # Buttons (sem o botão JSONs Locais)
        btn_grid = QtWidgets.QGridLayout()
        btn_grid.setSpacing(6)

        self.btn_apply_sim = QtWidgets.QPushButton("⚡ Simular Ordens")
        self.btn_apply_sim.setObjectName("successBtn")
        self.btn_apply_sim.setToolTip(
            "Calcula e atualiza a carteira e o passo a passo das ordens de compra e venda."
        )
        self.btn_apply_sim.clicked.connect(self.recalculate_portfolio)

        self.btn_save_snapshot = QtWidgets.QPushButton("💾 Salvar Registro")
        self.btn_save_snapshot.setObjectName("primaryBtn")
        self.btn_save_snapshot.clicked.connect(self.save_current_snapshot)

        self.btn_refresh_online = QtWidgets.QPushButton(
            "🔄 Atualizar Candles & Saldo"
        )
        self.btn_refresh_online.clicked.connect(
            lambda: self._load_links_and_fetch(offline=False)
        )

        btn_grid.addWidget(self.btn_apply_sim, 0, 0, 1, 2)
        btn_grid.addWidget(self.btn_save_snapshot, 1, 0)
        btn_grid.addWidget(self.btn_refresh_online, 1, 1)
        left_layout.addLayout(btn_grid)

        left_layout.addStretch(1)
        splitter.addWidget(left_widget)

        # --- RIGHT PANEL (TABS) ---
        right_tabs = QtWidgets.QTabWidget()

        # Tab 1: Sugestões de Compra/Venda e Posição
        tab_rebalance = QtWidgets.QWidget()
        tab_reb_layout = QtWidgets.QVBoxLayout(tab_rebalance)
        tab_reb_layout.setContentsMargins(6, 6, 6, 6)
        tab_reb_layout.setSpacing(6)

        self.table_positions = QtWidgets.QTableWidget(7, 10)
        self.table_positions.setAlternatingRowColors(True)
        self.table_positions.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.table_positions.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        self.table_positions.verticalHeader().setVisible(False)
        self.table_positions.verticalHeader().setDefaultSectionSize(26)
        self.table_positions.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )
        self.table_positions.setHorizontalHeaderLabels(
            [
                "Ativo",
                "Qtd Atual",
                "Preço (BNB)",
                "Valor (BNB)",
                "Valor (R$)",
                "Peso",
                "Alvo",
                "Ação",
                "Qtd Ordem",
                "Dif. (BNB / R$)",
            ]
        )
        header = self.table_positions.horizontalHeader()
        header.setFixedHeight(28)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QtWidgets.QHeaderView.ResizeToContents)
        # Altura exata para cabeçalho (28px) + 7 linhas (7 * 26px = 182px) + borda (4px) = 214px
        self.table_positions.setFixedHeight(214)
        tab_reb_layout.addWidget(self.table_positions, 0)

        orders_group = QtWidgets.QGroupBox(
            "Simular Ordens — Passo a Passo na Binance (Acumular BNB)"
        )
        orders_layout = QtWidgets.QVBoxLayout(orders_group)
        orders_layout.setContentsMargins(6, 8, 6, 6)
        self.orders_text = QtWidgets.QTextEdit()
        self.orders_text.setReadOnly(True)
        orders_layout.addWidget(self.orders_text)
        tab_reb_layout.addWidget(orders_group, 1)

        right_tabs.addTab(
            tab_rebalance, "⚖️ Carteira & Ordens"
        )

        # Tab 2: Comparativo dos 3 Modelos de Tom Cover
        tab_models = QtWidgets.QWidget()
        tab_models_layout = QtWidgets.QVBoxLayout(tab_models)
        tab_models_layout.setContentsMargins(6, 6, 6, 6)

        self.table_models = QtWidgets.QTableWidget(0, 6)
        self.table_models.setAlternatingRowColors(True)
        self.table_models.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.table_models.setHorizontalHeaderLabels(
            [
                "Ativo",
                "Preço (BNB)",
                "Peso Atual",
                "CRP (1/N)",
                "Universal Cover",
                "BCRP Histórico",
            ]
        )
        m_header = self.table_models.horizontalHeader()
        m_header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        tab_models_layout.addWidget(self.table_models)
        right_tabs.addTab(
            tab_models, "📊 Modelos Cover"
        )

        # Tab 3: Histórico de Registros (Dia e Hora)
        tab_history = QtWidgets.QWidget()
        tab_hist_layout = QtWidgets.QVBoxLayout(tab_history)
        tab_hist_layout.setContentsMargins(6, 6, 6, 6)

        self.table_history = QtWidgets.QTableWidget(0, 6)
        self.table_history.setAlternatingRowColors(True)
        self.table_history.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.table_history.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        self.table_history.setHorizontalHeaderLabels(
            [
                "Data e Hora",
                "Total BNB",
                "Evolução BNB",
                "Total BRL",
                "BNBBRL",
                "Estratégia",
            ]
        )
        h_header = self.table_history.horizontalHeader()
        h_header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        tab_hist_layout.addWidget(self.table_history)

        hist_btn_layout = QtWidgets.QHBoxLayout()
        btn_load_hist = QtWidgets.QPushButton(
            "📥 Carregar Registro Selecionado"
        )
        btn_load_hist.clicked.connect(self.load_selected_history_row)
        btn_del_hist = QtWidgets.QPushButton("🗑️ Excluir Selecionado")
        btn_del_hist.clicked.connect(self.delete_selected_history_row)
        hist_btn_layout.addWidget(btn_load_hist)
        hist_btn_layout.addWidget(btn_del_hist)
        hist_btn_layout.addStretch(1)
        tab_hist_layout.addLayout(hist_btn_layout)

        right_tabs.addTab(
            tab_history, "🕒 Histórico"
        )

        splitter.addWidget(right_tabs)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        main_layout.addWidget(splitter, 1)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Pronto.")

    def _create_summary_card(
        self, title: str, main_text: str, sub_text: str, accent_color: str
    ) -> dict:
        frame = QtWidgets.QFrame()
        frame.setFixedHeight(34)
        frame.setToolTip(sub_text)
        frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: #1E2329;
                border: 1px solid #2B3139;
                border-left: 3px solid {accent_color};
                border-radius: 5px;
            }}
            """
        )
        h = QtWidgets.QHBoxLayout(frame)
        h.setContentsMargins(8, 2, 8, 2)
        h.setSpacing(6)

        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setStyleSheet(
            "color: #848E9C; font-size: 11px; font-weight: bold; border: none;"
        )
        lbl_main = QtWidgets.QLabel(main_text)
        lbl_main.setStyleSheet(
            f"color: {accent_color}; font-size: 13px; font-weight: bold; border: none;"
        )
        lbl_sub = QtWidgets.QLabel("")
        lbl_sub.setVisible(False)

        h.addWidget(lbl_title)
        h.addWidget(lbl_main, 1, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        return {
            "frame": frame,
            "title": lbl_title,
            "main": lbl_main,
            "sub": lbl_sub,
        }

    def _load_links_and_fetch(self, offline: bool = False):
        if not os.path.exists(core.LINKS_FILE):
            QtWidgets.QMessageBox.critical(
                self,
                "Arquivo não encontrado",
                f"Não foi encontrado o arquivo:\n{core.LINKS_FILE}",
            )
            return

        with open(core.LINKS_FILE, "r", encoding="utf-8") as fp:
            self.pairs_links = json.load(fp)

        self.btn_refresh_online.setEnabled(False)
        self.status_bar.showMessage(
            "Atualizando candles (paresXlinks.json) e saldo Spot da carteira (keys.json)..."
        )

        self.worker = PriceFetchWorker(self.pairs_links, offline=offline)
        self.worker.finished_signal.connect(self._on_prices_loaded)
        self.worker.error_signal.connect(self._on_prices_error)
        self.worker.start()

    def _on_prices_error(self, err_msg: str):
        self.btn_refresh_online.setEnabled(True)
        self.status_bar.showMessage(f"Erro ao carregar cotações: {err_msg}")
        QtWidgets.QMessageBox.warning(
            self, "Erro ao carregar cotações", err_msg
        )

    def _on_prices_loaded(
        self,
        coin_data: dict,
        bnb_brl_price: float,
        bnb_brl_source: str,
        coins_order: list,
        spot_balances: dict,
        spot_msg: str,
        spot_ok: bool,
    ):
        self.btn_refresh_online.setEnabled(True)
        self.coin_data = coin_data
        self.bnb_brl_price = bnb_brl_price
        self.bnb_brl_source = bnb_brl_source
        self.coins_order = coins_order

        self.card_bnb_price["main"].setText(core.format_brl(bnb_brl_price))
        self.card_bnb_price["frame"].setToolTip(bnb_brl_source)

        self._rebuild_holdings_inputs(
            spot_balances=spot_balances if spot_ok else None
        )
        self.refresh_history_table()
        self._init_waiting_view()
        self.status_bar.showMessage(
            f"Candles atualizados! BNBBRL = {core.format_brl(bnb_brl_price)} | {spot_msg}. "
            "Clique em '⚡ Simular Ordens'."
        )

    def _init_waiting_view(self):
        """Preenche a tabela apenas com os 7 ativos até o usuário clicar em 'Simular Ordens'."""
        n_rows = min(7, len(self.coins_order))
        self.table_positions.setRowCount(n_rows)
        for row_idx in range(n_rows):
            c = self.coins_order[row_idx]
            p_bnb = 1.0 if c == "BNB" else self.coin_data[c]["price_bnb"]
            q_val = (
                self._parse_input_float(self.qty_inputs[c].text())
                if c in self.qty_inputs
                else 0.0
            )
            cells = [
                c,
                f"{q_val:.6f}",
                f"{p_bnb:.8f}",
                "—",
                "—",
                "—",
                "—",
                "Aguardando",
                "—",
                "—",
            ]
            for col_idx, txt in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(txt)
                item.setTextAlignment(
                    QtCore.Qt.AlignCenter
                    if col_idx in (0, 7)
                    else (QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                )
                if col_idx == 0:
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                    if c == "BNB":
                        item.setForeground(QtGui.QColor("#F0B90B"))
                elif col_idx == 7:
                    item.setForeground(QtGui.QColor("#848E9C"))
                self.table_positions.setItem(row_idx, col_idx, item)

        self.orders_text.setPlainText(
            "Saldos carregados à esquerda. Confira/ajuste as quantidades e clique no botão "
            "'⚡ Simular Ordens' para atualizar a tabela das 7 carteiras e o passo a passo das ordens."
        )

    def _rebuild_holdings_inputs(self, spot_balances: dict = None):
        # Usa o saldo carregado via API (keys.json) quando disponível; senão mantém o que foi digitado ou 0
        prev_typed = {}
        for c, line_edit in self.qty_inputs.items():
            prev_typed[c] = self._parse_input_float(line_edit.text())

        # Limpa layout anterior
        while self.holdings_form_layout.count():
            item = self.holdings_form_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        self.qty_inputs.clear()
        self.active_checks.clear()

        lbl_h0 = QtWidgets.QLabel("Ativo")
        lbl_h1 = QtWidgets.QLabel("Moeda")
        lbl_h2 = QtWidgets.QLabel("Qtd Atual")
        lbl_h3 = QtWidgets.QLabel("Preço (BNB)")
        for lbl in (lbl_h0, lbl_h1, lbl_h2, lbl_h3):
            lbl.setStyleSheet("color: #848E9C; font-weight: bold; font-size: 11px;")
        self.holdings_form_layout.addWidget(lbl_h0, 0, 0)
        self.holdings_form_layout.addWidget(lbl_h1, 0, 1)
        self.holdings_form_layout.addWidget(lbl_h2, 0, 2)
        self.holdings_form_layout.addWidget(lbl_h3, 0, 3)

        for row_idx, c in enumerate(self.coins_order, start=1):
            chk = QtWidgets.QCheckBox()
            chk.setChecked(True)
            self.active_checks[c] = chk

            lbl_coin = QtWidgets.QLabel(f"{c}")
            lbl_coin.setStyleSheet(
                "font-weight: bold; color: #F0B90B;"
                if c == "BNB"
                else "font-weight: bold; color: #EAECEF;"
            )

            if spot_balances is not None and c in spot_balances:
                default_val = float(spot_balances.get(c, 0.0))
            else:
                default_val = prev_typed.get(c, 0.0)
            inp = QtWidgets.QLineEdit(f"{default_val:g}")
            inp.setPlaceholderText("0")
            inp.setMaximumWidth(105)
            inp.setAlignment(QtCore.Qt.AlignRight)
            self.qty_inputs[c] = inp

            if c == "BNB":
                price_txt = "1.000000"
                tip_txt = f"1 BNB = {core.format_brl(self.bnb_brl_price)}"
            else:
                p_bnb = self.coin_data[c]["price_bnb"]
                p_brl = p_bnb * self.bnb_brl_price
                price_txt = f"{p_bnb:.6f}"
                tip_txt = f"1 {c} = {p_bnb:.8f} BNB ({core.format_brl(p_brl)})"
            lbl_price = QtWidgets.QLabel(price_txt)
            lbl_price.setToolTip(tip_txt)
            lbl_price.setStyleSheet("color: #B7BDC6; font-size: 11px;")

            self.holdings_form_layout.addWidget(chk, row_idx, 0, QtCore.Qt.AlignCenter)
            self.holdings_form_layout.addWidget(lbl_coin, row_idx, 1)
            self.holdings_form_layout.addWidget(inp, row_idx, 2)
            self.holdings_form_layout.addWidget(lbl_price, row_idx, 3)

    @staticmethod
    def _parse_input_float(text: str) -> float:
        t = text.strip().replace(",", ".")
        if not t:
            return 0.0
        try:
            v = float(t)
            return max(0.0, v)
        except ValueError:
            return 0.0

    def recalculate_portfolio(self):
        if not self.coins_order or self.bnb_brl_price <= 0:
            return

        holdings = {
            c: self._parse_input_float(self.qty_inputs[c].text())
            for c in self.coins_order
            if c in self.qty_inputs
        }
        active_universe = [
            c
            for c in self.coins_order
            if c in self.active_checks and self.active_checks[c].isChecked()
        ]
        if not active_universe:
            active_universe = list(self.coins_order)

        positions = {}
        total_bnb = 0.0
        for c in self.coins_order:
            qty = holdings.get(c, 0.0)
            p_bnb = 1.0 if c == "BNB" else self.coin_data[c]["price_bnb"]
            v_bnb = qty * p_bnb
            v_brl = v_bnb * self.bnb_brl_price
            total_bnb += v_bnb
            positions[c] = {
                "quantidade": qty,
                "preco_bnb": p_bnb,
                "preco_brl": p_bnb * self.bnb_brl_price,
                "valor_bnb": v_bnb,
                "valor_brl": v_brl,
            }

        total_brl = total_bnb * self.bnb_brl_price
        for c in self.coins_order:
            positions[c]["peso_atual"] = (
                positions[c]["valor_bnb"] / total_bnb if total_bnb > 0 else 0.0
            )

        # Matriz de preços relativos para ativos selecionados
        non_bnb_active = [c for c in active_universe if c != "BNB"]
        all_lengths = [
            len(self.coin_data[c]["series"]) for c in non_bnb_active
        ]
        window_len = min(all_lengths) if all_lengths else 0
        relatives_matrix = []
        if window_len >= 2:
            sorted_prices = {}
            for c in non_bnb_active:
                s_dict = self.coin_data[c]["series"]
                times_sorted = sorted(s_dict.keys())[-window_len:]
                sorted_prices[c] = [s_dict[t] for t in times_sorted]
            for t in range(1, window_len):
                row = []
                for c in active_universe:
                    if c == "BNB":
                        row.append(1.0)
                    else:
                        row.append(
                            sorted_prices[c][t] / sorted_prices[c][t - 1]
                        )
                relatives_matrix.append(row)

        m_active = len(active_universe)
        w_crp_sub = [1.0 / m_active] * m_active
        w_univ_sub = (
            core.compute_universal_weights(relatives_matrix, num_experts=1500)
            if relatives_matrix
            else w_crp_sub
        )
        w_bcrp_sub = (
            core.compute_bcrp_weights(relatives_matrix, iters=300)
            if relatives_matrix
            else w_crp_sub
        )

        def expand_w(w_sub):
            out = {c: 0.0 for c in self.coins_order}
            for c, w in zip(active_universe, w_sub):
                out[c] = w
            return out

        w_crp = expand_w(w_crp_sub)
        w_univ = expand_w(w_univ_sub)
        w_bcrp = expand_w(w_bcrp_sub)

        strategy_key = self.strategy_combo.currentData() or "crp"
        if strategy_key == "universal":
            target_weights = w_univ
        elif strategy_key == "bcrp":
            target_weights = w_bcrp
        else:
            target_weights = w_crp

        min_drift_frac = self.threshold_spin.value() / 100.0
        suggestions = []
        for c in self.coins_order:
            w_cur = positions[c]["peso_atual"]
            w_tgt = target_weights[c]
            target_bnb = total_bnb * w_tgt
            diff_bnb = target_bnb - positions[c]["valor_bnb"]
            diff_brl = diff_bnb * self.bnb_brl_price
            p_bnb = positions[c]["preco_bnb"]
            diff_qty = diff_bnb / p_bnb if p_bnb > 0 else 0.0

            if total_bnb <= 0 or abs(w_tgt - w_cur) < min_drift_frac:
                acao = "MANTER"
            elif diff_bnb > 0:
                acao = "COMPRAR" if c != "BNB" else "RESERVAR BNB"
            else:
                acao = "VENDER" if c != "BNB" else "USAR BNB"

            suggestions.append(
                {
                    "moeda": c,
                    "acao": acao,
                    "peso_atual_pct": round(w_cur * 100, 2),
                    "peso_alvo_pct": round(w_tgt * 100, 2),
                    "desvio_pct": round((w_cur - w_tgt) * 100, 2),
                    "qtd_atual": positions[c]["quantidade"],
                    "qtd_alvo": target_bnb / p_bnb if p_bnb > 0 else 0.0,
                    "delta_qtd": diff_qty,
                    "delta_bnb": diff_bnb,
                    "delta_brl": diff_brl,
                }
            )

        self.last_computed = {
            "strategy_key": strategy_key,
            "total_bnb": total_bnb,
            "total_brl": total_brl,
            "positions": positions,
            "w_crp": w_crp,
            "w_univ": w_univ,
            "w_bcrp": w_bcrp,
            "target_weights": target_weights,
            "suggestions": suggestions,
        }

        self._update_summary_cards(total_bnb, total_brl)
        self._update_positions_table(positions, suggestions)
        self._update_models_table(positions, w_crp, w_univ, w_bcrp)
        self._update_orders_instructions(suggestions, total_bnb)

    def _update_summary_cards(self, total_bnb: float, total_brl: float):
        self.card_bnb_val["main"].setText(f"{total_bnb:.6f} BNB")
        self.card_brl_val["main"].setText(core.format_brl(total_brl))

        history = core.load_history()
        if history and total_bnb > 0:
            prev = history[-1]
            prev_bnb = float(prev.get("total_bnb", 0.0))
            if prev_bnb > 0:
                diff = total_bnb - prev_bnb
                pct = (total_bnb / prev_bnb - 1.0) * 100.0
                color = "#0ECB81" if diff >= 0 else "#F6465D"
                self.card_evolution["main"].setText(
                    f"{diff:+.4f} BNB ({pct:+.2f}%)"
                )
                self.card_evolution["main"].setStyleSheet(
                    f"color: {color}; font-size: 13px; font-weight: bold; border: none;"
                )
                self.card_evolution["frame"].setToolTip(
                    f"vs. último salvo em {prev.get('data_hora', '')}"
                )

    def _update_positions_table(self, positions: dict, suggestions: list):
        display_coins = self.coins_order[:7]
        self.table_positions.setRowCount(len(display_coins))
        sug_map = {s["moeda"]: s for s in suggestions}

        for row_idx, c in enumerate(display_coins):
            p = positions[c]
            s = sug_map[c]

            acao = s["acao"]
            if acao in ("COMPRAR", "RESERVAR BNB"):
                acao_color = QtGui.QColor("#0ECB81")
            elif acao in ("VENDER", "USAR BNB"):
                acao_color = QtGui.QColor("#F6465D")
            else:
                acao_color = QtGui.QColor("#848E9C")

            cells = [
                c,
                f"{p['quantidade']:.6f}",
                f"{p['preco_bnb']:.8f}",
                f"{p['valor_bnb']:.8f} BNB",
                core.format_brl(p["valor_brl"]),
                f"{p['peso_atual']*100:.2f}%",
                f"{s['peso_alvo_pct']:.2f}%",
                acao,
                f"{s['delta_qtd']:+.6f} {c}",
                f"{s['delta_bnb']:+.6f} BNB ({core.format_brl(abs(s['delta_brl']))})",
            ]

            for col_idx, text in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(text)
                if col_idx in (1, 2, 3, 4, 5, 6, 8, 9):
                    item.setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                    )
                else:
                    item.setTextAlignment(QtCore.Qt.AlignCenter)

                if col_idx == 0:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    if c == "BNB":
                        item.setForeground(QtGui.QColor("#F0B90B"))
                elif col_idx in (7, 8, 9):
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setForeground(acao_color)

                self.table_positions.setItem(row_idx, col_idx, item)

    def _update_models_table(
        self, positions: dict, w_crp: dict, w_univ: dict, w_bcrp: dict
    ):
        self.table_models.setRowCount(len(self.coins_order))
        for row_idx, c in enumerate(self.coins_order):
            p = positions[c]
            cells = [
                c,
                f"{p['preco_bnb']:.8f} BNB",
                f"{p['peso_atual']*100:.2f}%",
                f"{w_crp[c]*100:.2f}%",
                f"{w_univ[c]*100:.2f}%",
                f"{w_bcrp[c]*100:.2f}%",
            ]
            for col_idx, txt in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(txt)
                item.setTextAlignment(
                    QtCore.Qt.AlignCenter
                    if col_idx == 0
                    else (QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                )
                if col_idx == 0:
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                self.table_models.setItem(row_idx, col_idx, item)

    def _update_orders_instructions(
        self, suggestions: list, total_bnb: float
    ):
        if total_bnb <= 0:
            self.orders_text.setPlainText(
                "Informe as quantidades atuais da sua carteira à esquerda para calcular "
                "o valor em BNB, em Reais (R$) e gerar as sugestões de COMPRA e VENDA."
            )
            return

        coin_sells = [
            s
            for s in suggestions
            if s["moeda"] != "BNB"
            and s["delta_bnb"] < 0
            and s["acao"] != "MANTER"
        ]
        coin_buys = [
            s
            for s in suggestions
            if s["moeda"] != "BNB"
            and s["delta_bnb"] > 0
            and s["acao"] != "MANTER"
        ]

        if not coin_sells and not coin_buys:
            self.orders_text.setPlainText(
                f"✓ Sua carteira já está equilibrada dentro da banda de {self.threshold_spin.value():.1f}%.\n"
                "Nenhuma ordem de compra ou venda necessária neste momento!"
            )
            return

        lines = []
        step = 1
        if coin_sells:
            lines.append(
                "1º PASSO — ORDENS DE VENDA (Realizar lucro das moedas que subiram em troca de BNB):"
            )
            for s in coin_sells:
                c = s["moeda"]
                lines.append(
                    f"   [{step}] VENDER {abs(s['delta_qtd']):.6f} {c} no par {c}BNB  "
                    f"➔  Recebe +{abs(s['delta_bnb']):.8f} BNB ({core.format_brl(abs(s['delta_brl']))})"
                )
                step += 1
            lines.append("")

        if coin_buys:
            lines.append(
                "2º PASSO — ORDENS DE COMPRA (Comprar na baixa utilizando BNB):"
            )
            for s in coin_buys:
                c = s["moeda"]
                lines.append(
                    f"   [{step}] COMPRAR {abs(s['delta_qtd']):.6f} {c} no par {c}BNB  "
                    f"➔  Investe {abs(s['delta_bnb']):.8f} BNB ({core.format_brl(abs(s['delta_brl']))})"
                )
                step += 1
            lines.append("")

        bnb_sug = next(s for s in suggestions if s["moeda"] == "BNB")
        est_fee_bnb = (
            sum(abs(s["delta_bnb"]) for s in coin_sells + coin_buys)
            * core.BINANCE_FEE
        )
        lines.append(
            f"• Reserva de BNB em caixa após rebalancear : {bnb_sug['qtd_alvo']:.8f} BNB "
            f"({core.format_brl(bnb_sug['qtd_alvo'] * self.bnb_brl_price)})"
        )
        lines.append(
            f"• Taxa estimada da Binance (0,10% Spot)    : ~{est_fee_bnb:.8f} BNB "
            f"({core.format_brl(est_fee_bnb * self.bnb_brl_price)})"
        )
        self.orders_text.setPlainText("\n".join(lines))

    def save_current_snapshot(self):
        self.recalculate_portfolio()
        if not self.last_computed:
            return
        now_dt = datetime.now().astimezone()
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S %z")
        comp = self.last_computed
        positions = comp["positions"]
        target_weights = comp["target_weights"]

        entry = {
            "data_hora": now_str,
            "timestamp": int(now_dt.timestamp()),
            "estrategia": comp["strategy_key"],
            "cotacao_bnb_brl": self.bnb_brl_price,
            "total_bnb": round(comp["total_bnb"], 8),
            "total_brl": round(comp["total_brl"], 2),
            "quantidades": {
                c: positions[c]["quantidade"] for c in self.coins_order
            },
            "precos_bnb": {
                c: positions[c]["preco_bnb"] for c in self.coins_order
            },
            "valores_bnb": {
                c: round(positions[c]["valor_bnb"], 8)
                for c in self.coins_order
            },
            "valores_brl": {
                c: round(positions[c]["valor_brl"], 2)
                for c in self.coins_order
            },
            "pesos_atuais": {
                c: round(positions[c]["peso_atual"], 6)
                for c in self.coins_order
            },
            "pesos_alvo": {
                c: round(target_weights[c], 6) for c in self.coins_order
            },
            "sugestoes": comp["suggestions"],
        }
        core.save_history_entry(entry)
        self.refresh_history_table()
        self.recalculate_portfolio()
        self.status_bar.showMessage(
            f"Registro salvo em {core.HISTORY_FILE} ({now_str})"
        )
        QtWidgets.QMessageBox.information(
            self,
            "Registro Salvo",
            f"Estado da carteira salvo com sucesso!\n\n"
            f"Data/Hora: {now_str}\n"
            f"Total em BNB: {comp['total_bnb']:.8f} BNB\n"
            f"Total em BRL: {core.format_brl(comp['total_brl'])}",
        )

    def simulate_order_execution(self):
        if not self.last_computed or self.last_computed["total_bnb"] <= 0:
            return
        for s in self.last_computed["suggestions"]:
            c = s["moeda"]
            if c in self.qty_inputs:
                self.qty_inputs[c].blockSignals(True)
                self.qty_inputs[c].setText(f"{s['qtd_alvo']:.6f}")
                self.qty_inputs[c].blockSignals(False)
        self.recalculate_portfolio()
        self.status_bar.showMessage(
            "Quantidades atualizadas com a simulação pós-rebalanceamento."
        )

    def refresh_history_table(self):
        history = core.load_history()
        self.table_history.setRowCount(len(history))
        for idx, item in enumerate(reversed(history)):
            orig_idx = len(history) - 1 - idx
            t_bnb = float(item.get("total_bnb", 0.0))
            t_brl = float(item.get("total_brl", 0.0))
            cot = float(item.get("cotacao_bnb_brl", 0.0))
            if orig_idx > 0:
                prev_bnb = float(history[orig_idx - 1].get("total_bnb", 0.0))
                diff_bnb = t_bnb - prev_bnb
                pct = (t_bnb / prev_bnb - 1.0) * 100.0 if prev_bnb > 0 else 0.0
                evol_str = f"{diff_bnb:+.6f} BNB ({pct:+.2f}%)"
            else:
                evol_str = "1º Registro"

            row_vals = [
                item.get("data_hora", ""),
                f"{t_bnb:.8f} BNB",
                evol_str,
                core.format_brl(t_brl),
                core.format_brl(cot),
                item.get("estrategia", "crp").upper(),
            ]
            for col_idx, val in enumerate(row_vals):
                cell = QtWidgets.QTableWidgetItem(val)
                cell.setData(QtCore.Qt.UserRole, orig_idx)
                cell.setTextAlignment(QtCore.Qt.AlignCenter)
                self.table_history.setItem(idx, col_idx, cell)

    def load_selected_history_row(self):
        row = self.table_history.currentRow()
        if row < 0:
            return
        orig_idx = self.table_history.item(row, 0).data(QtCore.Qt.UserRole)
        history = core.load_history()
        if 0 <= orig_idx < len(history):
            q_dict = history[orig_idx].get("quantidades", {})
            for c, inp in self.qty_inputs.items():
                inp.blockSignals(True)
                inp.setText(f"{float(q_dict.get(c, 0.0)):g}")
                inp.blockSignals(False)
            self.recalculate_portfolio()
            self.status_bar.showMessage(
                f"Quantidades carregadas do registro de {history[orig_idx].get('data_hora')}"
            )

    def delete_selected_history_row(self):
        row = self.table_history.currentRow()
        if row < 0:
            return
        orig_idx = self.table_history.item(row, 0).data(QtCore.Qt.UserRole)
        history = core.load_history()
        if 0 <= orig_idx < len(history):
            del history[orig_idx]
            with open(core.HISTORY_FILE, "w", encoding="utf-8") as fp:
                json.dump(history, fp, indent=2, ensure_ascii=False)
            self.refresh_history_table()
            self.recalculate_portfolio()


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = CoverRebalancerWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

