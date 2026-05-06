"""
Module: MD-GUI-004 — execution_panel.py
FO-GUI-004 Execution Panel: pending signals + override qty + execute entry.
"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QAbstractTableModel, QDate, QModelIndex, QSortFilterProxyModel, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from us_swing.data.models import FilteredStockEntry
from us_swing.gui.app_service import AppService
from us_swing.gui._types import TradeSignal
from us_swing.gui.theme import C


# ── Single signal row ─────────────────────────────────────────────────────────

class _SignalRow(QFrame):
    """One row in the signal list: symbol label, stats, quantity override, execute."""

    execute_requested = pyqtSignal(object, int)  # (TradeSignal, qty)

    def __init__(self, signal: TradeSignal, mode: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._signal   = signal
        self._mode     = mode
        self._original_qty = signal.recommended_qty

        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet(f"QFrame {{ border: 1px solid {C.OVERLAY}; border-radius: 6px; }}")

        # ── Labels ─────────────────────────────────────────────────────────────
        sym = QLabel(signal.symbol)
        sym.setStyleSheet(f"color: {C.BLUE}; font-size: 13pt; font-weight: bold; border: none;")

        strat = QLabel(signal.strategy_id)
        strat.setStyleSheet(f"color: {C.MUTED}; font-size: 8pt; border: none;")

        status_badge = QLabel("⬤  READY")
        status_badge.setStyleSheet(f"color: {C.GREEN}; font-weight: bold; font-size: 9pt; border: none;")

        price_lbl = QLabel(f"Entry: {signal.entry_price:.2f}")
        stop_lbl  = QLabel(f"Stop: {signal.stop_loss:.2f}")
        tgt_lbl   = QLabel(f"Target: {signal.target_price:.2f}")
        rr_val    = (signal.target_price - signal.entry_price) / (signal.entry_price - signal.stop_loss)
        rr_lbl    = QLabel(f"R/R: {rr_val:.1f}×")
        for lbl in (price_lbl, stop_lbl, tgt_lbl, rr_lbl):
            lbl.setStyleSheet(f"color: {C.TEXT}; font-size: 9pt; border: none;")
        rr_lbl.setStyleSheet(f"color: {C.YELLOW}; font-weight: bold; font-size: 9pt; border: none;")

        # Info column
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.addWidget(sym)
        info_col.addWidget(strat)
        info_col.addWidget(status_badge)

        # Price column
        price_col = QVBoxLayout()
        price_col.setSpacing(2)
        price_col.addWidget(price_lbl)
        price_col.addWidget(stop_lbl)
        price_col.addWidget(tgt_lbl)
        price_col.addWidget(rr_lbl)

        # Quantity column
        rec_lbl = QLabel("Rec. Qty")
        rec_lbl.setStyleSheet(f"color: {C.MUTED}; font-size: 8pt; border: none;")
        self._spin = QSpinBox()
        self._spin.setRange(1, 10_000)
        self._spin.setValue(signal.recommended_qty)
        self._spin.setFixedWidth(90)
        self._override_lbl = QLabel("")
        self._override_lbl.setStyleSheet(f"color: {C.ORANGE}; font-size: 8pt; border: none;")
        self._spin.valueChanged.connect(self._on_qty_changed)

        qty_col = QVBoxLayout()
        qty_col.setSpacing(2)
        qty_col.addWidget(rec_lbl)
        qty_col.addWidget(self._spin)
        qty_col.addWidget(self._override_lbl)

        # Execute button
        self._exec_btn = QPushButton(f"Execute  {signal.side}")
        self._exec_btn.setObjectName("buy_btn")
        self._exec_btn.setMinimumWidth(120)
        self._exec_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._exec_btn.clicked.connect(self._on_execute)

        # Row layout
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(24)
        row.addLayout(info_col)
        row.addLayout(price_col)
        row.addStretch()
        row.addLayout(qty_col)
        row.addWidget(self._exec_btn)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_qty_changed(self, value: int) -> None:
        if value != self._original_qty:
            self._override_lbl.setText("(overridden)")
        else:
            self._override_lbl.setText("")

    def _on_execute(self) -> None:
        qty    = self._spin.value()
        symbol = self._signal.symbol
        price  = self._signal.entry_price
        mode   = self._mode.upper()
        target_lbl = self._get_target_user_label()
        executing_for = f"<br><span style='color:{C.YELLOW}; font-size:8pt;'>🔐 Admin · Executing for: {target_lbl}</span>" if target_lbl else ""
        msg    = (
            f"Submit <b>{self._signal.side}</b> order for <b>{symbol}</b>?<br><br>"
            f"Qty: {qty}&nbsp;&nbsp; Entry: {price:.2f}&nbsp;&nbsp; Mode: {mode}"
            f"{executing_for}"
        )
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Confirm Order")
        dlg.setIcon(QMessageBox.Icon.Question)
        dlg.setText(msg)
        dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dlg.setDefaultButton(QMessageBox.StandardButton.Yes)
        ret = dlg.exec()
        if ret == QMessageBox.StandardButton.Yes:
            self.execute_requested.emit(self._signal, qty)
            self.setEnabled(False)
            self._exec_btn.setText("✔  Submitted")
            self._exec_btn.setStyleSheet(f"color: {C.MUTED};")

    def _get_target_user_label(self) -> str:
        """Return the label of the target user selected in the Execution panel combo."""
        w = self.parent()
        while w is not None:
            if isinstance(w, ExecutionPanel):
                idx = w._exec_user_combo.currentIndex()
                return w._exec_user_combo.itemText(idx)
            w = w.parent()
        return ""

    def set_circuit_breaker(self, active: bool) -> None:
        self._exec_btn.setEnabled(not active)

    def refresh_mode(self, mode: str) -> None:
        self._mode = mode


# ── Filtered Stocks table model ───────────────────────────────────────────────

_COL_SYMBOL  = 0
_COL_SCORE   = 1
_COL_RUN     = 2
_COL_STYLE   = 3
_COL_SCREENER = 4


class _FilteredStocksModel(QAbstractTableModel):
    """Table model for the filtered stocks left pane."""

    HEADERS = ["Symbol", "Score", "Run", "Style", "Screener"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[FilteredStockEntry] = []

    def load(self, entries: list[FilteredStockEntry]) -> None:
        self.beginResetModel()
        self._rows = entries
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._rows):
            return None
        entry = self._rows[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == _COL_SYMBOL:
                return entry.symbol
            if col == _COL_SCORE:
                return f"{entry.score:.3f}"
            if col == _COL_STYLE:
                return ", ".join(entry.trading_styles) if entry.trading_styles else "—"
            if col == _COL_SCREENER:
                return entry.screener_name
            if col == _COL_RUN:
                return "Auto" if entry.run_type == "scheduled" else "Manual"

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == _COL_SYMBOL:
                return QColor(C.BLUE)
            if col == _COL_SCORE:
                if entry.score >= 0.70:
                    return QColor(C.GREEN)
                if entry.score >= 0.40:
                    return QColor(C.YELLOW)
                return QColor(C.RED)
            if col == _COL_RUN:
                return QColor(C.TEAL) if entry.run_type == "scheduled" else QColor(C.BLUE)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (_COL_SCORE, _COL_RUN):
                return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        return None


# ── Filtered Stocks left pane ─────────────────────────────────────────────────

class _FilteredStocksPane(QWidget):
    """Left panel showing the most recent screener output across all presets."""

    def __init__(self, svc: AppService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(180)
        self._all_entries: list[FilteredStockEntry] = []

        # ── Header ─────────────────────────────────────────────────────────────
        hdr_lbl = QLabel("FILTERED STOCKS")
        hdr_lbl.setStyleSheet(
            f"color: {C.MUTED}; font-size: 7pt; font-weight: bold; letter-spacing: 2px;"
        )
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(f"color: {C.MUTED}; font-size: 8pt;")

        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(0, 0, 0, 0)
        hdr_row.addWidget(hdr_lbl)
        hdr_row.addStretch()
        hdr_row.addWidget(self._count_lbl)

        # ── Date selector ──────────────────────────────────────────────────────
        date_lbl = QLabel("Date")
        date_lbl.setStyleSheet(f"color: {C.MUTED}; font-size: 8pt;")
        self._date_combo = QComboBox()
        self._date_combo.setFixedWidth(120)
        self._date_combo.setStyleSheet("QComboBox { outline: none; } QComboBox:focus { outline: none; }")

        date_row = QHBoxLayout()
        date_row.setContentsMargins(0, 0, 0, 0)
        date_row.setSpacing(6)
        date_row.addWidget(date_lbl)
        date_row.addWidget(self._date_combo)
        date_row.addStretch()

        self._date_combo.currentIndexChanged.connect(self._filter_by_date)

        # ── Table ──────────────────────────────────────────────────────────────
        self._model = _FilteredStocksModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.sortByColumn(_COL_SCORE, Qt.SortOrder.DescendingOrder)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        v_hdr = self._table.verticalHeader()
        assert v_hdr is not None
        v_hdr.setVisible(False)
        self._table.setShowGrid(False)
        self._table.setWordWrap(False)

        hdrs = self._table.horizontalHeader()
        assert hdrs is not None
        hdrs.setSectionResizeMode(_COL_SYMBOL,   QHeaderView.ResizeMode.Interactive)
        hdrs.resizeSection(_COL_SYMBOL, 75)
        hdrs.setSectionResizeMode(_COL_SCORE,    QHeaderView.ResizeMode.Interactive)
        hdrs.resizeSection(_COL_SCORE, 52)
        hdrs.setSectionResizeMode(_COL_RUN,      QHeaderView.ResizeMode.Interactive)
        hdrs.resizeSection(_COL_RUN, 58)
        hdrs.setSectionResizeMode(_COL_STYLE,    QHeaderView.ResizeMode.Interactive)
        hdrs.resizeSection(_COL_STYLE, 65)
        hdrs.setSectionResizeMode(_COL_SCREENER, QHeaderView.ResizeMode.Stretch)

        # ── Empty state label ─────────────────────────────────────────────────
        self._empty_lbl = QLabel("No screener results yet.\nRun a preset in the Screener tab.")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(f"color: {C.MUTED}; font-size: 9pt; padding: 20px;")
        self._empty_lbl.setWordWrap(True)

        # Stack table and empty label — show one at a time
        self._table.setVisible(False)
        self._empty_lbl.setVisible(True)

        # ── Layout ─────────────────────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 6, 0)
        root.setSpacing(6)
        root.addLayout(hdr_row)
        root.addLayout(date_row)
        root.addWidget(self._table, 1)
        root.addWidget(self._empty_lbl, 1)

        # ── Wire up to service ─────────────────────────────────────────────────
        svc.screener_results_updated.connect(self._on_updated)
        self._on_updated(svc.get_latest_screener_results())

    def _on_updated(self, entries: list[FilteredStockEntry]) -> None:
        self._all_entries = entries
        dates = sorted({e.date for e in entries}, reverse=True)
        self._date_combo.blockSignals(True)
        try:
            self._date_combo.clear()
            for d in dates:
                qd = QDate.fromString(d, "yyyy-MM-dd")
                self._date_combo.addItem(qd.toString("dd MMM yyyy"), d)
        finally:
            self._date_combo.blockSignals(False)
        if not dates:
            self._count_lbl.setText("")
            self._table.setVisible(False)
            self._empty_lbl.setVisible(True)
            return
        self._filter_by_date()

    def _filter_by_date(self) -> None:
        date_str = self._date_combo.currentData() or ""
        visible = [e for e in self._all_entries if e.date == date_str]
        self._model.load(visible)
        count = len(visible)
        self._count_lbl.setText(f"{count} stock{'s' if count != 1 else ''}")
        self._table.setVisible(count > 0)
        self._empty_lbl.setVisible(count == 0)


# ── Execution Panel ───────────────────────────────────────────────────────────

class ExecutionPanel(QWidget):
    """
    FO-GUI-004 Execution Panel.
    Shows pending signals with recommended quantities and execute controls.
    Left pane: filtered stocks from the most recent screener runs.
    Right pane: pending signals with qty override and execute controls.
    """

    def __init__(self, demo: AppService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._demo = demo
        self._cb_active = False

        main = QVBoxLayout(self)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(12)

        # ── Header row ─────────────────────────────────────────────────────────
        title = QLabel("Trade Execution")
        title.setStyleSheet(f"color: {C.BLUE}; font-size: 12pt; font-weight: bold;")

        admin_badge = QLabel("🔐 ADMIN")
        admin_badge.setStyleSheet(
            f"color:{C.YELLOW}; background:{C.YELLOW}18; border:1px solid {C.YELLOW}55;"
            f"border-radius:5px; padding:1px 7px; font-size:7pt; font-weight:bold;"
        )

        exec_for_lbl = QLabel("Execute for:")
        exec_for_lbl.setStyleSheet(f"color:{C.MUTED}; font-size:8pt;")
        self._exec_user_combo = QComboBox()
        self._exec_user_combo.setMinimumWidth(140)
        self._exec_user_combo.setStyleSheet("QComboBox { outline: none; } QComboBox:focus { outline: none; }")
        self._exec_user_combo.addItem("🌐  All / Broadcast", None)
        for u in demo.get_users():
            flag = "🔴" if u.mode == "live" else "🔵"
            self._exec_user_combo.addItem(f"{flag}  {u.username}  ({u.mode.upper()})", u.user_id)
        demo.viewing_changed.connect(self._on_scope_changed)

        hdr = QHBoxLayout()
        hdr.addWidget(title)
        hdr.addWidget(admin_badge)
        hdr.addStretch()
        hdr.addWidget(exec_for_lbl)
        hdr.addWidget(self._exec_user_combo)
        main.addLayout(hdr)

        # ── Circuit breaker banner (hidden by default) ─────────────────────────
        self._cb_banner = QLabel(
            "⚠  Circuit Breaker ACTIVE — daily loss limit reached. "
            "New entries are disabled."
        )
        self._cb_banner.setObjectName("cb_banner")
        self._cb_banner.setVisible(False)
        self._cb_banner.setWordWrap(True)
        main.addWidget(self._cb_banner)

        # ── Horizontal split: filtered stocks | pending signals ────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {C.OVERLAY}; }}")

        splitter.addWidget(_FilteredStocksPane(demo))
        splitter.addWidget(self._build_right_pane(demo))
        splitter.setSizes([260, 900])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        main.addWidget(splitter, 1)

    def _build_right_pane(self, demo: AppService) -> QWidget:
        """Build the right side: pending signals scroll area + status + demo button."""
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(6, 0, 0, 0)
        layout.setSpacing(12)

        # Pending signals group
        group = QGroupBox("Pending Signals")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)

        signals = demo.get_pending_signals()
        self._signal_rows: list[_SignalRow] = []
        if signals:
            mode = demo.get_active_user().mode
            for sig in signals:
                row = _SignalRow(sig, mode)
                row.execute_requested.connect(self._on_execute)
                self._signal_rows.append(row)
                group_layout.addWidget(row)
        else:
            no_sig = QLabel("No pending signals at this time.")
            no_sig.setStyleSheet(f"color: {C.MUTED}; padding: 20px;")
            no_sig.setAlignment(Qt.AlignmentFlag.AlignCenter)
            group_layout.addWidget(no_sig)

        scroll = QScrollArea()
        scroll.setWidget(group)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {C.BG}; }}")
        layout.addWidget(scroll, 1)

        # Status line
        self._status_lbl = QLabel(f"{len(signals)} signal(s) pending — review and execute above")
        self._status_lbl.setStyleSheet(f"color: {C.MUTED}; font-size: 9pt;")
        layout.addWidget(self._status_lbl)

        # Demo CB toggle
        self._cb_toggle = QPushButton("Demo: Toggle Circuit Breaker")
        self._cb_toggle.setObjectName("danger_btn")
        self._cb_toggle.setFixedWidth(240)
        self._cb_toggle.clicked.connect(self._toggle_cb)
        cb_row = QHBoxLayout()
        cb_row.addStretch()
        cb_row.addWidget(self._cb_toggle)
        layout.addLayout(cb_row)

        return pane

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_scope_changed(self) -> None:
        """Sync the Execute-for combo with the admin viewing scope."""
        uid = self._demo.get_viewing_uid()
        for i in range(self._exec_user_combo.count()):
            if self._exec_user_combo.itemData(i) == uid:
                self._exec_user_combo.setCurrentIndex(i)
                break

    def _on_execute(self, signal: TradeSignal, qty: int) -> None:
        order_id = self._demo.execute_signal(signal, qty)
        self._status_lbl.setText(
            f"✔  Order #{order_id} submitted for {signal.symbol} × {qty}  —  "
            f"check Log Viewer for details"
        )
        self._status_lbl.setStyleSheet(f"color: {C.GREEN}; font-size: 9pt;")

    def _toggle_cb(self) -> None:
        self._cb_active = not self._cb_active
        self.on_circuit_breaker(self._cb_active)

    def on_circuit_breaker(self, active: bool) -> None:
        """Enable/disable all entry buttons and show banner."""
        self._cb_active = active
        self._cb_banner.setVisible(active)
        for row in self._signal_rows:
            row.set_circuit_breaker(active)
        if active:
            self._demo.log_message.emit("WARNING", "Circuit breaker activated — entries disabled")
