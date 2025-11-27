#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dan_simulation_circuit - Simulador Profissional Estilo Multisim
Versão 2.3
"""

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QToolBar, QDockWidget, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QListWidget, QListWidgetItem, QTextEdit, QLabel,
    QStatusBar, QSplitter, QScrollArea, QFrame, QStyleFactory,
    QMessageBox, QFileDialog, QInputDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QMimeData, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QColor, QAction, QDrag
import sys
import json
import os

from circuit_canvas import CircuitCanvas


class DraggableTreeWidget(QTreeWidget):
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
    
    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item and item.parent() is not None and item.childCount() == 0:
            comp_type = item.data(0, Qt.ItemDataRole.UserRole)
            if comp_type:
                mimedata = QMimeData()
                mimedata.setText(comp_type)
                drag = QDrag(self)
                drag.setMimeData(mimedata)
                drag.exec(Qt.DropAction.CopyAction)
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)


class DraggableFrame(QFrame):
    def __init__(self, comp_type, label):
        super().__init__()
        self.comp_type = comp_type
        self.label_text = label
        self.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def mousePressEvent(self, event):
        mimedata = QMimeData()
        mimedata.setText(self.comp_type)
        drag = QDrag(self)
        drag.setMimeData(mimedata)
        drag.exec(Qt.DropAction.CopyAction)


class HierarchyTab(QWidget):
    component_selected = pyqtSignal(str)
    
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Atualizar")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_expand = QPushButton("➕ Expandir Tudo")
        self.btn_expand.clicked.connect(self.expand_all)
        self.btn_collapse = QPushButton("➖ Recolher Tudo")
        self.btn_collapse.clicked.connect(self.collapse_all)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addWidget(self.btn_expand)
        toolbar.addWidget(self.btn_collapse)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Componente", "Tipo", "Valor"])
        self.tree.setColumnCount(3)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.tree)
        
    def refresh(self):
        self.tree.clear()
        root = QTreeWidgetItem(self.tree, ["Design1", "", ""])
        root.setExpanded(True)
        categories = {}
        for comp in self.canvas.components:
            cat = comp.get('category', 'Outros')
            if cat not in categories:
                categories[cat] = QTreeWidgetItem(root, [cat, "", ""])
                categories[cat].setExpanded(True)
            item = QTreeWidgetItem(categories[cat], [comp.get('name', 'Unknown'), comp.get('type', ''), comp.get('value', '')])
            item.setData(0, Qt.ItemDataRole.UserRole, comp.get('id'))
        if self.canvas.connections:
            conn_root = QTreeWidgetItem(root, ["Conexões", "", f"{len(self.canvas.connections)}"])
            conn_root.setExpanded(True)
            for i, conn in enumerate(self.canvas.connections):
                QTreeWidgetItem(conn_root, [f"Wire_{i+1}", "Fio", ""])
    
    def expand_all(self):
        self.tree.expandAll()
    
    def collapse_all(self):
        self.tree.collapseAll()
    
    def on_item_clicked(self, item, column):
        comp_id = item.data(0, Qt.ItemDataRole.UserRole)
        if comp_id:
            self.component_selected.emit(comp_id)


class VisibilityTab(QWidget):
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Atualizar")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_show_all = QPushButton("👁 Mostrar Todos")
        self.btn_show_all.clicked.connect(self.show_all)
        self.btn_hide_all = QPushButton("🚫 Ocultar Todos")
        self.btn_hide_all.clicked.connect(self.hide_all)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addWidget(self.btn_show_all)
        toolbar.addWidget(self.btn_hide_all)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Visível", "Componente", "Tipo", "Valor"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.table)
        
    def refresh(self):
        self.table.setRowCount(0)
        for i, comp in enumerate(self.canvas.components):
            self.table.insertRow(i)
            checkbox = QCheckBox()
            checkbox.setChecked(comp.get('visible', True))
            checkbox.stateChanged.connect(lambda state, idx=i: self.toggle_visibility(idx, state))
            widget = QWidget()
            lo = QHBoxLayout(widget)
            lo.addWidget(checkbox)
            lo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lo.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(i, 0, widget)
            self.table.setItem(i, 1, QTableWidgetItem(comp.get('name', 'Unknown')))
            self.table.setItem(i, 2, QTableWidgetItem(comp.get('type', '')))
            self.table.setItem(i, 3, QTableWidgetItem(comp.get('value', '')))
    
    def toggle_visibility(self, index, state):
        if index < len(self.canvas.components):
            self.canvas.components[index]['visible'] = (state == Qt.CheckState.Checked.value)
            self.canvas.update()
    
    def show_all(self):
        for comp in self.canvas.components:
            comp['visible'] = True
        self.refresh()
        self.canvas.update()
    
    def hide_all(self):
        for comp in self.canvas.components:
            comp['visible'] = False
        self.refresh()
        self.canvas.update()


class ProjectViewTab(QWidget):
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Atualizar")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_export = QPushButton("📄 Exportar Info")
        self.btn_export.clicked.connect(self.export_info)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addWidget(self.btn_export)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setFont(QFont("Consolas", 11))
        self.info_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.info_text)
        self.refresh()
        
    def refresh(self):
        info = []
        info.append("=" * 60)
        info.append("            DAN_SIMULATION_CIRCUIT")
        info.append("            Project Information")
        info.append("=" * 60)
        info.append("")
        info.append(f"📁 Projeto: Design1")
        info.append(f"📋 Schematic Sheet: 1")
        info.append("")
        info.append("─" * 60)
        info.append("📊 ESTATÍSTICAS DO CIRCUITO")
        info.append("─" * 60)
        info.append(f"  • Total de Componentes: {len(self.canvas.components)}")
        info.append(f"  • Total de Conexões: {len(self.canvas.connections)}")
        info.append("")
        type_count = {}
        for comp in self.canvas.components:
            t = comp.get('type', 'unknown')
            type_count[t] = type_count.get(t, 0) + 1
        if type_count:
            info.append("─" * 60)
            info.append("📦 COMPONENTES POR TIPO")
            info.append("─" * 60)
            for t, count in sorted(type_count.items()):
                info.append(f"  • {t}: {count}")
        info.append("")
        info.append("─" * 60)
        info.append("⚡ STATUS")
        info.append("─" * 60)
        info.append("  ✅ Pronto para simulação")
        self.info_text.setText("\n".join(info))
    
    def export_info(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar Informações", "project_info.txt", "Text (*.txt)")
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.info_text.toPlainText())
            QMessageBox.information(self, "Sucesso", f"Informações exportadas para:\n{filename}")


class NetlistTab(QWidget):
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        toolbar = QHBoxLayout()
        self.btn_generate = QPushButton("⚡ Gerar Netlist")
        self.btn_generate.clicked.connect(self.generate_netlist)
        self.btn_copy = QPushButton("📋 Copiar")
        self.btn_copy.clicked.connect(self.copy_netlist)
        self.btn_export = QPushButton("💾 Exportar .cir")
        self.btn_export.clicked.connect(self.export_netlist)
        toolbar.addWidget(self.btn_generate)
        toolbar.addWidget(self.btn_copy)
        toolbar.addWidget(self.btn_export)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.netlist_text = QTextEdit()
        self.netlist_text.setFont(QFont("Consolas", 11))
        self.netlist_text.setPlaceholderText("Clique em 'Gerar Netlist' para criar o netlist SPICE...")
        self.netlist_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.netlist_text)
        
    def generate_netlist(self):
        netlist = self.canvas.get_netlist()
        self.netlist_text.setText(netlist)
    
    def copy_netlist(self):
        text = self.netlist_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "Copiado", "Netlist copiado para a área de transferência!")
    
    def export_netlist(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar Netlist", "circuit.cir", "SPICE Netlist (*.cir);;Text (*.txt)")
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.netlist_text.toPlainText())
            QMessageBox.information(self, "Sucesso", f"Netlist exportado para:\n{filename}")


class SimulationTab(QWidget):
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        toolbar = QHBoxLayout()
        self.btn_run = QPushButton("▶ Executar Simulação")
        self.btn_run.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 8px 16px;")
        self.btn_run.clicked.connect(self.run_simulation)
        self.btn_clear = QPushButton("🗑 Limpar")
        self.btn_clear.clicked.connect(self.clear_results)
        self.btn_export = QPushButton("💾 Exportar Resultados")
        self.btn_export.clicked.connect(self.export_results)
        toolbar.addWidget(self.btn_run)
        toolbar.addWidget(self.btn_clear)
        toolbar.addWidget(self.btn_export)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Consolas", 12))
        self.results_text.setPlaceholderText("Execute uma simulação para ver os resultados aqui...")
        self.results_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.results_text.setMinimumHeight(100)
        layout.addWidget(self.results_text)
        
    def run_simulation(self):
        results = self.canvas.simulate()
        output = []
        output.append("=" * 70)
        output.append("              RESULTADOS DA SIMULAÇÃO DC")
        output.append("              Dan_simulation_circuit v2.3")
        output.append("=" * 70)
        output.append("")
        if 'summary' in results:
            summary = results['summary']
            output.append("┌" + "─" * 68 + "┐")
            output.append("│  📋 RESUMO DO CIRCUITO                                              │")
            output.append("├" + "─" * 68 + "┤")
            output.append(f"│    Tensão Total: {summary.get('total_voltage', 0):12.4f} V                              │")
            output.append(f"│    Resistência Total: {summary.get('total_resistance', 0):12.4f} Ω                         │")
            output.append(f"│    Corrente Total: {summary.get('total_current', 0)*1000:12.4f} mA                            │")
            output.append("└" + "─" * 68 + "┘")
            output.append("")
        if 'nodes' in results and results['nodes']:
            output.append("┌" + "─" * 68 + "┐")
            output.append("│  📊 TENSÕES NODAIS                                                  │")
            output.append("├" + "─" * 68 + "┤")
            for node, voltage in results['nodes'].items():
                line = f"│    {node} = {voltage:12.4f} V"
                line = line + " " * (69 - len(line)) + "│"
                output.append(line)
            output.append("└" + "─" * 68 + "┘")
            output.append("")
        if 'currents' in results and results['currents']:
            output.append("┌" + "─" * 68 + "┐")
            output.append("│  ⚡ CORRENTES                                                        │")
            output.append("├" + "─" * 68 + "┤")
            for branch, current in results['currents'].items():
                if abs(current) >= 1:
                    current_str = f"{current:12.4f} A"
                elif abs(current) >= 1e-3:
                    current_str = f"{current*1000:12.4f} mA"
                elif abs(current) >= 1e-6:
                    current_str = f"{current*1e6:12.4f} µA"
                else:
                    current_str = f"{current*1e9:12.4f} nA"
                line = f"│    I({branch}) = {current_str}"
                line = line + " " * (69 - len(line)) + "│"
                output.append(line)
            output.append("└" + "─" * 68 + "┘")
            output.append("")
        if 'power' in results and results['power']:
            output.append("┌" + "─" * 68 + "┐")
            output.append("│  🔋 POTÊNCIA DISSIPADA                                              │")
            output.append("├" + "─" * 68 + "┤")
            total_power = 0
            for comp, power in results['power'].items():
                total_power += power
                if power >= 1:
                    power_str = f"{power:12.4f} W"
                elif power >= 1e-3:
                    power_str = f"{power*1000:12.4f} mW"
                else:
                    power_str = f"{power*1e6:12.4f} µW"
                line = f"│    P({comp}) = {power_str}"
                line = line + " " * (69 - len(line)) + "│"
                output.append(line)
            output.append("├" + "─" * 68 + "┤")
            if total_power >= 1:
                total_str = f"{total_power:12.4f} W"
            elif total_power >= 1e-3:
                total_str = f"{total_power*1000:12.4f} mW"
            else:
                total_str = f"{total_power*1e6:12.4f} µW"
            line = f"│    TOTAL = {total_str}"
            line = line + " " * (69 - len(line)) + "│"
            output.append(line)
            output.append("└" + "─" * 68 + "┘")
            output.append("")
        if 'voltages' in results and results['voltages']:
            output.append("┌" + "─" * 68 + "┐")
            output.append("│  🔌 QUEDA DE TENSÃO NOS COMPONENTES                                 │")
            output.append("├" + "─" * 68 + "┤")
            for comp, voltage in results['voltages'].items():
                line = f"│    V({comp}) = {voltage:12.4f} V"
                line = line + " " * (69 - len(line)) + "│"
                output.append(line)
            output.append("└" + "─" * 68 + "┘")
            output.append("")
        output.append("=" * 70)
        output.append("  ✅ Simulação concluída com sucesso!")
        output.append(f"  📊 Componentes analisados: {len(self.canvas.components)}")
        output.append(f"  🔗 Conexões: {len(self.canvas.connections)}")
        output.append("=" * 70)
        self.results_text.setText("\n".join(output))
    
    def clear_results(self):
        self.results_text.clear()
    
    def export_results(self):
        text = self.results_text.toPlainText()
        if not text:
            QMessageBox.warning(self, "Aviso", "Nenhum resultado para exportar.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar Resultados", "simulation_results.txt", "Text (*.txt)")
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(text)
            QMessageBox.information(self, "Sucesso", f"Resultados exportados para:\n{filename}")


class DanSimulationCircuit(QMainWindow):
    VERSION = "2.3"
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Design1 - Dan_simulation_circuit [Design1]")
        self.setGeometry(100, 50, 1600, 950)
        self.circuit_canvas = CircuitCanvas()
        self.create_central_widget()
        self.create_menubar()
        self.create_toolbars()
        self.create_docks()
        self.create_statusbar()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.auto_refresh_tabs)
        self.update_timer.start(2000)
        self.show()
    
    def create_menubar(self):
        menubar = self.menuBar()
        menubar.setFont(QFont("Arial", 10))
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New", self.new_project)
        file_menu.addAction("Open...", self.open_project)
        file_menu.addAction("Save", self.save_project)
        file_menu.addAction("Save As...", self.save_as_project)
        file_menu.addSeparator()
        file_menu.addAction("Export Netlist...", self.export_netlist)
        file_menu.addAction("Export Image...", self.export_image)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        edit_menu = menubar.addMenu("Edit")
        edit_menu.addAction("Undo", self.circuit_canvas.undo)
        edit_menu.addAction("Redo", self.circuit_canvas.redo)
        edit_menu.addSeparator()
        edit_menu.addAction("Select All", self.circuit_canvas.select_all)
        edit_menu.addAction("Deselect All", self.circuit_canvas.clear_selection)
        edit_menu.addSeparator()
        edit_menu.addAction("Delete", self.circuit_canvas.delete_selected)
        edit_menu.addAction("Rotate", self.circuit_canvas.rotate_selected)
        view_menu = menubar.addMenu("View")
        view_menu.addAction("Zoom In", lambda: self.circuit_canvas.zoom(1.2))
        view_menu.addAction("Zoom Out", lambda: self.circuit_canvas.zoom(0.8))
        view_menu.addAction("Fit to Window", self.circuit_canvas.fit_to_window)
        view_menu.addSeparator()
        view_menu.addAction("Toggle Grid", self.circuit_canvas.toggle_grid)
        view_menu.addAction("Refresh", self.circuit_canvas.update)
        place_menu = menubar.addMenu("Place")
        place_menu.addAction("Resistor", lambda: self.quick_place("resistor"))
        place_menu.addAction("Capacitor", lambda: self.quick_place("capacitor"))
        place_menu.addAction("Inductor", lambda: self.quick_place("indutor"))
        place_menu.addSeparator()
        place_menu.addAction("Voltage Source", lambda: self.quick_place("voltage_source"))
        place_menu.addAction("Ground", lambda: self.quick_place("gnd"))
        place_menu.addSeparator()
        place_menu.addAction("Wire Mode", self.circuit_canvas.start_wire_mode)
        simulate_menu = menubar.addMenu("Simulate")
        simulate_menu.addAction("Run DC Analysis", self.run_simulation)
        simulate_menu.addAction("Run AC Analysis", self.run_ac_simulation)
        simulate_menu.addAction("Run Transient", self.run_transient)
        simulate_menu.addSeparator()
        simulate_menu.addAction("Stop")
        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Clear Canvas", self.circuit_canvas.clear)
        tools_menu.addAction("Auto-arrange", self.circuit_canvas.auto_arrange)
        tools_menu.addSeparator()
        tools_menu.addAction("Options...")
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self.show_about)
        help_menu.addAction("Keyboard Shortcuts", self.show_shortcuts)
    
    def create_toolbars(self):
        self.main_toolbar = QToolBar("Main Toolbar")
        self.main_toolbar.setIconSize(QSize(24, 24))
        self.main_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_toolbar)
        self.main_toolbar.addAction("🆕 New", self.new_project)
        self.main_toolbar.addAction("📂 Open", self.open_project)
        self.main_toolbar.addAction("💾 Save", self.save_project)
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction("↩ Undo", self.circuit_canvas.undo)
        self.main_toolbar.addAction("↪ Redo", self.circuit_canvas.redo)
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction("🔍+ Zoom In", lambda: self.circuit_canvas.zoom(1.2))
        self.main_toolbar.addAction("🔍- Zoom Out", lambda: self.circuit_canvas.zoom(0.8))
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction("▶ Simulate", self.run_simulation)
        self.main_toolbar.addAction("⏹ Stop")
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction("🔌 Wire", self.circuit_canvas.start_wire_mode)
        self.main_toolbar.addAction("🗑 Clear", self.circuit_canvas.clear)
    
    def create_central_widget(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.setChildrenCollapsible(False)
        self.circuit_canvas.setMinimumHeight(200)
        self.main_splitter.addWidget(self.circuit_canvas)
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setMinimumHeight(150)
        self.bottom_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.hierarchy_tab = HierarchyTab(self.circuit_canvas)
        self.visibility_tab = VisibilityTab(self.circuit_canvas)
        self.project_tab = ProjectViewTab(self.circuit_canvas)
        self.netlist_tab = NetlistTab(self.circuit_canvas)
        self.simulation_tab = SimulationTab(self.circuit_canvas)
        self.bottom_tabs.addTab(self.hierarchy_tab, "📊 Hierarchy")
        self.bottom_tabs.addTab(self.visibility_tab, "👁 Visibility")
        self.bottom_tabs.addTab(self.project_tab, "📁 Project View")
        self.bottom_tabs.addTab(self.netlist_tab, "📝 Netlist")
        self.bottom_tabs.addTab(self.simulation_tab, "⚡ Simulation")
        self.bottom_tabs.currentChanged.connect(self.on_tab_changed)
        self.hierarchy_tab.component_selected.connect(self.select_component_by_id)
        self.main_splitter.addWidget(self.bottom_tabs)
        self.main_splitter.setStretchFactor(0, 7)
        self.main_splitter.setStretchFactor(1, 3)
        total_height = 900
        self.main_splitter.setSizes([int(total_height * 0.65), int(total_height * 0.35)])
        layout.addWidget(self.main_splitter)
    
    def create_docks(self):
        left_dock = QDockWidget("Design Toolbox")
        left_dock.setMinimumWidth(180)
        left_dock.setMaximumWidth(280)
        left_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)
        self.tree = DraggableTreeWidget()
        self.tree.setHeaderLabel("Components")
        self.tree.setColumnCount(1)
        root = QTreeWidgetItem(self.tree, ["Design1"])
        passive = QTreeWidgetItem(root, ["📦 Passivos"])
        items = [("Resistor", "resistor"), ("Capacitor", "capacitor"), ("Indutor", "indutor"), ("Potenciômetro", "potentiometer")]
        for name, comp_type in items:
            item = QTreeWidgetItem(passive, [name])
            item.setData(0, Qt.ItemDataRole.UserRole, comp_type)
        sources = QTreeWidgetItem(root, ["⚡ Fontes"])
        items = [("Fonte DC", "voltage_source"), ("Fonte AC", "voltage_ac"), ("Fonte Corrente", "current_source"), ("Terra (GND)", "gnd"), ("VCC", "vcc")]
        for name, comp_type in items:
            item = QTreeWidgetItem(sources, [name])
            item.setData(0, Qt.ItemDataRole.UserRole, comp_type)
        semi = QTreeWidgetItem(root, ["🔌 Semicondutores"])
        items = [("Diodo", "diode"), ("Zener", "zener"), ("LED", "led"), ("Schottky", "schottky")]
        for name, comp_type in items:
            item = QTreeWidgetItem(semi, [name])
            item.setData(0, Qt.ItemDataRole.UserRole, comp_type)
        trans = QTreeWidgetItem(root, ["🔺 Transistores"])
        items = [("NPN", "transistor_npn"), ("PNP", "transistor_pnp"), ("NMOS", "mosfet_n"), ("PMOS", "mosfet_p")]
        for name, comp_type in items:
            item = QTreeWidgetItem(trans, [name])
            item.setData(0, Qt.ItemDataRole.UserRole, comp_type)
        ics = QTreeWidgetItem(root, ["🔲 Integrados"])
        items = [("Op-Amp", "opamp"), ("Comparador", "comparator"), ("Relé", "relay"), ("Timer 555", "timer555")]
        for name, comp_type in items:
            item = QTreeWidgetItem(ics, [name])
            item.setData(0, Qt.ItemDataRole.UserRole, comp_type)
        instr = QTreeWidgetItem(root, ["📏 Instrumentos"])
        items = [("Voltímetro", "voltmeter"), ("Amperímetro", "ammeter"), ("Osciloscópio", "oscilloscope"), ("Probe", "probe")]
        for name, comp_type in items:
            item = QTreeWidgetItem(instr, [name])
            item.setData(0, Qt.ItemDataRole.UserRole, comp_type)
        others = QTreeWidgetItem(root, ["🔧 Outros"])
        items = [("Chave", "switch"), ("Fusível", "fuse"), ("Transformador", "transformer"), ("Cristal", "crystal")]
        for name, comp_type in items:
            item = QTreeWidgetItem(others, [name])
            item.setData(0, Qt.ItemDataRole.UserRole, comp_type)
        root.setExpanded(True)
        for i in range(root.childCount()):
            root.child(i).setExpanded(True)
        left_layout.addWidget(self.tree)
        left_dock.setWidget(left_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, left_dock)
        right_dock = QDockWidget("Quick Components")
        right_dock.setMinimumWidth(70)
        right_dock.setMaximumWidth(90)
        right_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(3, 3, 3, 3)
        right_layout.setSpacing(3)
        components_grid = [
            ("R", QColor(255, 107, 53), "resistor"), ("C", QColor(78, 205, 196), "capacitor"),
            ("L", QColor(155, 89, 182), "indutor"), ("V", QColor(231, 76, 60), "voltage_source"),
            ("I", QColor(26, 188, 156), "current_source"), ("D", QColor(52, 152, 219), "diode"),
            ("Z", QColor(41, 128, 185), "zener"), ("Q", QColor(142, 68, 173), "transistor_npn"),
            ("U", QColor(96, 125, 139), "opamp"), ("G", QColor(44, 62, 80), "gnd"),
            ("K", QColor(121, 85, 72), "switch"), ("P", QColor(255, 193, 7), "probe"),
        ]
        for label, color, comp_type in components_grid:
            btn = DraggableFrame(comp_type, label)
            btn.setStyleSheet(f"QFrame {{ background-color: {color.name()}; border: 2px solid {color.darker(120).name()}; border-radius: 6px; min-height: 45px; max-height: 45px; }} QFrame:hover {{ border: 2px solid white; }}")
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            lbl.setStyleSheet("color: white; background: transparent;")
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout_frame = QVBoxLayout(btn)
            layout_frame.setContentsMargins(0, 0, 0, 0)
            layout_frame.addWidget(lbl)
            right_layout.addWidget(btn)
        right_layout.addStretch()
        right_dock.setWidget(right_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, right_dock)
    
    def create_statusbar(self):
        self.status = self.statusBar()
        self.status.showMessage("Pronto. Arraste componentes para o canvas.")
        self.status.setFont(QFont("Arial", 9))
        self.comp_count_label = QLabel("Componentes: 0")
        self.conn_count_label = QLabel("Conexões: 0")
        self.zoom_label = QLabel("Zoom: 100%")
        self.status.addPermanentWidget(self.comp_count_label)
        self.status.addPermanentWidget(self.conn_count_label)
        self.status.addPermanentWidget(self.zoom_label)
    
    def on_tab_changed(self, index):
        tab = self.bottom_tabs.widget(index)
        if hasattr(tab, 'refresh'):
            tab.refresh()
    
    def auto_refresh_tabs(self):
        self.comp_count_label.setText(f"Componentes: {len(self.circuit_canvas.components)}")
        self.conn_count_label.setText(f"Conexões: {len(self.circuit_canvas.connections)}")
        self.zoom_label.setText(f"Zoom: {int(self.circuit_canvas.zoom_level * 100)}%")
    
    def select_component_by_id(self, comp_id):
        for comp in self.circuit_canvas.components:
            if comp.get('id') == comp_id:
                self.circuit_canvas.selected_component = comp
                self.circuit_canvas.update()
                break
    
    def quick_place(self, comp_type):
        self.circuit_canvas.add_component(comp_type, 400, 300)
        self.status.showMessage(f"Componente {comp_type} adicionado.")
    
    def new_project(self):
        reply = QMessageBox.question(self, "Novo Projeto", "Deseja salvar o projeto atual antes de criar um novo?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Cancel:
            return
        if reply == QMessageBox.StandardButton.Yes:
            self.save_project()
        self.circuit_canvas.clear()
        self.refresh_all_tabs()
        self.status.showMessage("Novo projeto criado.")
    
    def open_project(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Abrir Projeto", "", "Dan Circuit (*.dsc);;JSON (*.json);;Todos (*.*)")
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.circuit_canvas.load_circuit_data(data)
                self.refresh_all_tabs()
                self.status.showMessage(f"Projeto carregado: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao carregar:\n{str(e)}")
    
    def save_project(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Salvar Projeto", "circuit.dsc", "Dan Circuit (*.dsc);;JSON (*.json)")
        if filename:
            try:
                data = self.circuit_canvas.get_circuit_data()
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.status.showMessage(f"Projeto salvo: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao salvar:\n{str(e)}")
    
    def save_as_project(self):
        self.save_project()
    
    def export_netlist(self):
        self.netlist_tab.generate_netlist()
        self.netlist_tab.export_netlist()
    
    def export_image(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar Imagem", "circuit.png", "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)")
        if filename:
            pixmap = self.circuit_canvas.grab()
            pixmap.save(filename)
            self.status.showMessage(f"Imagem exportada: {filename}")
    
    def run_simulation(self):
        self.bottom_tabs.setCurrentWidget(self.simulation_tab)
        self.simulation_tab.run_simulation()
        self.status.showMessage("Simulação DC concluída.")
    
    def run_ac_simulation(self):
        QMessageBox.information(self, "Simulação AC", "Simulação AC será implementada em versão futura.")
    
    def run_transient(self):
        QMessageBox.information(self, "Transiente", "Análise transiente será implementada em versão futura.")
    
    def refresh_all_tabs(self):
        self.hierarchy_tab.refresh()
        self.visibility_tab.refresh()
        self.project_tab.refresh()
    
    def show_about(self):
        QMessageBox.about(self, "Sobre Dan_simulation_circuit", f"<h2>Dan_simulation_circuit</h2><p>Versão {self.VERSION}</p><p>Simulador de circuitos eletrônicos profissional.</p><p>© 2025 Daniel - MJSP</p>")
    
    def show_shortcuts(self):
        QMessageBox.information(self, "Atalhos de Teclado", "<h3>Atalhos</h3><p><b>Ctrl+N</b>: Novo<br><b>Ctrl+O</b>: Abrir<br><b>Ctrl+S</b>: Salvar<br><b>Ctrl+Z</b>: Desfazer<br><b>Ctrl+Y</b>: Refazer<br><b>Delete</b>: Excluir<br><b>R</b>: Rotacionar<br><b>W</b>: Modo fio<br><b>Escape</b>: Cancelar</p>")


def main():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('Fusion'))
    app.setStyleSheet("""
        QMainWindow { background-color: #2b2b2b; }
        QDockWidget { color: #ffffff; }
        QDockWidget::title { background-color: #3c3c3c; padding: 5px; }
        QTreeWidget { background-color: #1e1e1e; color: #ffffff; border: 1px solid #3c3c3c; }
        QTreeWidget::item:hover { background-color: #3c3c3c; }
        QTreeWidget::item:selected { background-color: #0078d4; }
        QTabWidget::pane { border: 1px solid #3c3c3c; background-color: #2b2b2b; }
        QTabBar::tab { background-color: #3c3c3c; color: #ffffff; padding: 8px 16px; margin-right: 2px; }
        QTabBar::tab:selected { background-color: #0078d4; }
        QTabBar::tab:hover { background-color: #4c4c4c; }
        QTextEdit { background-color: #1e1e1e; color: #00ff88; border: 1px solid #3c3c3c; }
        QTableWidget { background-color: #1e1e1e; color: #ffffff; border: 1px solid #3c3c3c; gridline-color: #3c3c3c; }
        QTableWidget::item:selected { background-color: #0078d4; }
        QHeaderView::section { background-color: #3c3c3c; color: #ffffff; padding: 5px; border: 1px solid #2b2b2b; }
        QPushButton { background-color: #3c3c3c; color: #ffffff; border: 1px solid #5c5c5c; padding: 6px 16px; border-radius: 4px; }
        QPushButton:hover { background-color: #4c4c4c; border: 1px solid #6c6c6c; }
        QPushButton:pressed { background-color: #0078d4; }
        QMenuBar { background-color: #2b2b2b; color: #ffffff; }
        QMenuBar::item:selected { background-color: #3c3c3c; }
        QMenu { background-color: #2b2b2b; color: #ffffff; border: 1px solid #3c3c3c; }
        QMenu::item:selected { background-color: #0078d4; }
        QToolBar { background-color: #2b2b2b; border: none; spacing: 5px; }
        QStatusBar { background-color: #007acc; color: #ffffff; }
        QScrollBar:vertical { background-color: #2b2b2b; width: 14px; }
        QScrollBar::handle:vertical { background-color: #5c5c5c; border-radius: 7px; min-height: 30px; }
        QScrollBar::handle:vertical:hover { background-color: #7c7c7c; }
        QScrollBar:horizontal { background-color: #2b2b2b; height: 14px; }
        QScrollBar::handle:horizontal { background-color: #5c5c5c; border-radius: 7px; min-width: 30px; }
        QScrollBar::handle:horizontal:hover { background-color: #7c7c7c; }
        QSplitter::handle { background-color: #0078d4; }
        QSplitter::handle:hover { background-color: #00aaff; }
        QSplitter::handle:vertical { height: 8px; }
    """)
    window = DanSimulationCircuit()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
