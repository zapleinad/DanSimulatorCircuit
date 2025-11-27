#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QWidget, QMenu, QInputDialog, QMessageBox
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QTransform, QCursor
import math
import uuid


class CircuitCanvas(QWidget):
    COMPONENT_DEFAULTS = {
        'resistor': {'value': '1k', 'unit': 'Ω', 'category': 'Passivos'},
        'capacitor': {'value': '100n', 'unit': 'F', 'category': 'Passivos'},
        'indutor': {'value': '10m', 'unit': 'H', 'category': 'Passivos'},
        'potentiometer': {'value': '10k', 'unit': 'Ω', 'category': 'Passivos'},
        'voltage_source': {'value': '12', 'unit': 'V', 'category': 'Fontes'},
        'voltage_ac': {'value': '120', 'unit': 'Vac', 'category': 'Fontes'},
        'current_source': {'value': '1m', 'unit': 'A', 'category': 'Fontes'},
        'gnd': {'value': '0', 'unit': 'V', 'category': 'Fontes'},
        'vcc': {'value': '5', 'unit': 'V', 'category': 'Fontes'},
        'diode': {'value': '1N4148', 'unit': '', 'category': 'Semicondutores'},
        'zener': {'value': '5.1', 'unit': 'V', 'category': 'Semicondutores'},
        'led': {'value': 'RED', 'unit': '', 'category': 'Semicondutores'},
        'schottky': {'value': '1N5819', 'unit': '', 'category': 'Semicondutores'},
        'transistor_npn': {'value': '2N2222', 'unit': '', 'category': 'Transistores'},
        'transistor_pnp': {'value': '2N2907', 'unit': '', 'category': 'Transistores'},
        'mosfet_n': {'value': 'IRF540', 'unit': '', 'category': 'Transistores'},
        'mosfet_p': {'value': 'IRF9540', 'unit': '', 'category': 'Transistores'},
        'opamp': {'value': 'LM741', 'unit': '', 'category': 'Integrados'},
        'comparator': {'value': 'LM393', 'unit': '', 'category': 'Integrados'},
        'relay': {'value': '12V', 'unit': '', 'category': 'Integrados'},
        'timer555': {'value': 'NE555', 'unit': '', 'category': 'Integrados'},
        'voltmeter': {'value': '', 'unit': 'V', 'category': 'Instrumentos'},
        'ammeter': {'value': '', 'unit': 'A', 'category': 'Instrumentos'},
        'oscilloscope': {'value': '', 'unit': '', 'category': 'Instrumentos'},
        'probe': {'value': '', 'unit': '', 'category': 'Instrumentos'},
        'switch': {'value': 'SPST', 'unit': '', 'category': 'Outros'},
        'fuse': {'value': '1', 'unit': 'A', 'category': 'Outros'},
        'transformer': {'value': '1:1', 'unit': '', 'category': 'Outros'},
        'crystal': {'value': '16M', 'unit': 'Hz', 'category': 'Outros'},
    }
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.components = []
        self.connections = []
        self.undo_stack = []
        self.redo_stack = []
        self.selected_component = None
        self.dragging = False
        self.drag_offset = QPoint(0, 0)
        self.wire_mode = False
        self.wire_start = None
        self.wire_start_terminal = None
        self.temp_wire_end = None
        self.zoom_level = 1.0
        self.pan_offset = QPoint(0, 0)
        self.panning = False
        self.pan_start = QPoint(0, 0)
        self.grid_size = 20
        self.show_grid = True
        self.component_counter = {}
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: #1a1a2e;")
    
    def snap_to_grid(self, pos):
        x = round(pos.x() / self.grid_size) * self.grid_size
        y = round(pos.y() / self.grid_size) * self.grid_size
        return QPoint(int(x), int(y))
    
    def screen_to_canvas(self, pos):
        x = (pos.x() - self.pan_offset.x()) / self.zoom_level
        y = (pos.y() - self.pan_offset.y()) / self.zoom_level
        return QPoint(int(x), int(y))
    
    def canvas_to_screen(self, pos):
        x = pos.x() * self.zoom_level + self.pan_offset.x()
        y = pos.y() * self.zoom_level + self.pan_offset.y()
        return QPoint(int(x), int(y))
    
    def get_component_name(self, comp_type):
        prefix_map = {'resistor': 'R', 'capacitor': 'C', 'indutor': 'L', 'voltage_source': 'V', 'voltage_ac': 'V', 'current_source': 'I', 'gnd': 'GND', 'vcc': 'VCC', 'diode': 'D', 'zener': 'D', 'led': 'D', 'schottky': 'D', 'transistor_npn': 'Q', 'transistor_pnp': 'Q', 'mosfet_n': 'M', 'mosfet_p': 'M', 'opamp': 'U', 'comparator': 'U', 'relay': 'K', 'timer555': 'U', 'voltmeter': 'VM', 'ammeter': 'AM', 'oscilloscope': 'OSC', 'probe': 'P', 'switch': 'SW', 'fuse': 'F', 'transformer': 'T', 'crystal': 'Y', 'potentiometer': 'RV'}
        prefix = prefix_map.get(comp_type, 'X')
        if prefix not in self.component_counter:
            self.component_counter[prefix] = 0
        self.component_counter[prefix] += 1
        return f"{prefix}{self.component_counter[prefix]}"
    
    def add_component(self, comp_type, x, y):
        defaults = self.COMPONENT_DEFAULTS.get(comp_type, {'value': '', 'unit': '', 'category': 'Outros'})
        component = {'id': str(uuid.uuid4()), 'type': comp_type, 'name': self.get_component_name(comp_type), 'x': x, 'y': y, 'rotation': 0, 'value': defaults['value'], 'unit': defaults['unit'], 'category': defaults['category'], 'visible': True, 'terminals': self.get_terminals(comp_type)}
        self.components.append(component)
        self.undo_stack.append(('add', component.copy()))
        self.redo_stack.clear()
        self.update()
        return component
    
    def get_terminals(self, comp_type):
        terminals = {'resistor': [(-40, 0), (40, 0)], 'capacitor': [(-30, 0), (30, 0)], 'indutor': [(-40, 0), (40, 0)], 'potentiometer': [(-40, 0), (40, 0), (0, -30)], 'voltage_source': [(0, -30), (0, 30)], 'voltage_ac': [(0, -30), (0, 30)], 'current_source': [(0, -30), (0, 30)], 'gnd': [(0, -20)], 'vcc': [(0, 20)], 'diode': [(-30, 0), (30, 0)], 'zener': [(-30, 0), (30, 0)], 'led': [(-30, 0), (30, 0)], 'schottky': [(-30, 0), (30, 0)], 'transistor_npn': [(-30, 0), (30, -20), (30, 20)], 'transistor_pnp': [(-30, 0), (30, -20), (30, 20)], 'mosfet_n': [(-30, 0), (30, -20), (30, 20)], 'mosfet_p': [(-30, 0), (30, -20), (30, 20)], 'opamp': [(-40, -15), (-40, 15), (40, 0)], 'comparator': [(-40, -15), (-40, 15), (40, 0)], 'relay': [(-40, -20), (-40, 20), (40, -20), (40, 20)], 'timer555': [(-40, -30), (-40, 0), (-40, 30), (40, -30), (40, 0), (40, 30)], 'voltmeter': [(-20, 0), (20, 0)], 'ammeter': [(-20, 0), (20, 0)], 'oscilloscope': [(0, 30)], 'probe': [(0, 20)], 'switch': [(-30, 0), (30, 0)], 'fuse': [(-30, 0), (30, 0)], 'transformer': [(-40, -20), (-40, 20), (40, -20), (40, 20)], 'crystal': [(-25, 0), (25, 0)]}
        return terminals.get(comp_type, [(-30, 0), (30, 0)])
    
    def get_terminal_positions(self, component):
        terminals = component.get('terminals', [(-30, 0), (30, 0)])
        cx, cy = component['x'], component['y']
        rotation = component.get('rotation', 0)
        positions = []
        for tx, ty in terminals:
            rad = math.radians(rotation)
            rx = tx * math.cos(rad) - ty * math.sin(rad)
            ry = tx * math.sin(rad) + ty * math.cos(rad)
            positions.append((cx + rx, cy + ry))
        return positions
    
    def find_terminal_at(self, pos, exclude_comp=None):
        threshold = 15
        for comp in self.components:
            if comp == exclude_comp or not comp.get('visible', True):
                continue
            terminals = self.get_terminal_positions(comp)
            for i, (tx, ty) in enumerate(terminals):
                dist = math.sqrt((pos.x() - tx)**2 + (pos.y() - ty)**2)
                if dist < threshold:
                    return comp, i, (tx, ty)
        return None, None, None
    
    def find_component_at(self, pos):
        for comp in reversed(self.components):
            if not comp.get('visible', True):
                continue
            cx, cy = comp['x'], comp['y']
            if abs(pos.x() - cx) < 50 and abs(pos.y() - cy) < 40:
                return comp
        return None
    
    def mousePressEvent(self, event):
        canvas_pos = self.screen_to_canvas(event.pos())
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = True
            self.pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() == Qt.MouseButton.RightButton:
            comp = self.find_component_at(canvas_pos)
            if comp:
                self.selected_component = comp
                self.show_context_menu(event.globalPosition().toPoint(), comp)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if self.wire_mode:
                comp, term_idx, term_pos = self.find_terminal_at(canvas_pos)
                if comp:
                    if self.wire_start is None:
                        self.wire_start = comp
                        self.wire_start_terminal = term_idx
                        self.temp_wire_end = term_pos
                    else:
                        if comp != self.wire_start:
                            self.add_connection(self.wire_start, self.wire_start_terminal, comp, term_idx)
                        self.wire_start = None
                        self.wire_start_terminal = None
                        self.temp_wire_end = None
                else:
                    self.wire_start = None
                    self.wire_start_terminal = None
                    self.temp_wire_end = None
            else:
                comp = self.find_component_at(canvas_pos)
                if comp:
                    self.selected_component = comp
                    self.dragging = True
                    self.drag_offset = QPoint(canvas_pos.x() - comp['x'], canvas_pos.y() - comp['y'])
                else:
                    self.selected_component = None
            self.update()
    
    def mouseMoveEvent(self, event):
        canvas_pos = self.screen_to_canvas(event.pos())
        if self.panning:
            delta = event.pos() - self.pan_start
            self.pan_offset += delta
            self.pan_start = event.pos()
            self.update()
            return
        if self.dragging and self.selected_component:
            new_pos = self.snap_to_grid(QPoint(canvas_pos.x() - self.drag_offset.x(), canvas_pos.y() - self.drag_offset.y()))
            self.selected_component['x'] = new_pos.x()
            self.selected_component['y'] = new_pos.y()
            self.update()
        if self.wire_mode and self.wire_start:
            self.temp_wire_end = (canvas_pos.x(), canvas_pos.y())
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
    
    def mouseDoubleClickEvent(self, event):
        canvas_pos = self.screen_to_canvas(event.pos())
        comp = self.find_component_at(canvas_pos)
        if comp:
            self.edit_component_value(comp)
    
    def wheelEvent(self, event):
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.zoom(factor, event.position().toPoint())
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
        elif event.key() == Qt.Key.Key_R:
            self.rotate_selected()
        elif event.key() == Qt.Key.Key_W:
            self.start_wire_mode()
        elif event.key() == Qt.Key.Key_Escape:
            self.cancel_operation()
        elif event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.undo()
        elif event.key() == Qt.Key.Key_Y and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.redo()
        elif event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.select_all()
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        comp_type = event.mimeData().text()
        canvas_pos = self.screen_to_canvas(event.position().toPoint())
        snapped = self.snap_to_grid(canvas_pos)
        self.add_component(comp_type, snapped.x(), snapped.y())
        event.acceptProposedAction()
    
    def add_connection(self, comp1, term1, comp2, term2):
        connection = {'id': str(uuid.uuid4()), 'from_component': comp1['id'], 'from_terminal': term1, 'to_component': comp2['id'], 'to_terminal': term2}
        self.connections.append(connection)
        self.undo_stack.append(('add_wire', connection.copy()))
        self.redo_stack.clear()
        self.update()
    
    def start_wire_mode(self):
        self.wire_mode = True
        self.wire_start = None
        self.setCursor(Qt.CursorShape.CrossCursor)
    
    def cancel_operation(self):
        self.wire_mode = False
        self.wire_start = None
        self.wire_start_terminal = None
        self.temp_wire_end = None
        self.selected_component = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
    
    def delete_selected(self):
        if self.selected_component:
            comp_id = self.selected_component['id']
            self.connections = [c for c in self.connections if c['from_component'] != comp_id and c['to_component'] != comp_id]
            self.components.remove(self.selected_component)
            self.undo_stack.append(('delete', self.selected_component.copy()))
            self.redo_stack.clear()
            self.selected_component = None
            self.update()
    
    def rotate_selected(self):
        if self.selected_component:
            self.selected_component['rotation'] = (self.selected_component.get('rotation', 0) + 90) % 360
            self.update()
    
    def clear(self):
        self.components = []
        self.connections = []
        self.selected_component = None
        self.component_counter = {}
        self.update()
    
    def clear_selection(self):
        self.selected_component = None
        self.update()
    
    def select_all(self):
        if self.components:
            self.selected_component = self.components[-1]
            self.update()
    
    def zoom(self, factor, center=None):
        old_zoom = self.zoom_level
        self.zoom_level = max(0.2, min(3.0, self.zoom_level * factor))
        if center and self.zoom_level != old_zoom:
            scale = self.zoom_level / old_zoom
            self.pan_offset = QPoint(int(center.x() - (center.x() - self.pan_offset.x()) * scale), int(center.y() - (center.y() - self.pan_offset.y()) * scale))
        self.update()
    
    def fit_to_window(self):
        if not self.components:
            return
        min_x = min(c['x'] for c in self.components) - 100
        max_x = max(c['x'] for c in self.components) + 100
        min_y = min(c['y'] for c in self.components) - 100
        max_y = max(c['y'] for c in self.components) + 100
        width = max_x - min_x
        height = max_y - min_y
        zoom_x = self.width() / width
        zoom_y = self.height() / height
        self.zoom_level = min(zoom_x, zoom_y, 2.0)
        self.pan_offset = QPoint(int(self.width() / 2 - (min_x + width / 2) * self.zoom_level), int(self.height() / 2 - (min_y + height / 2) * self.zoom_level))
        self.update()
    
    def toggle_grid(self):
        self.show_grid = not self.show_grid
        self.update()
    
    def auto_arrange(self):
        if not self.components:
            return
        cols = int(math.ceil(math.sqrt(len(self.components))))
        spacing = 120
        for i, comp in enumerate(self.components):
            comp['x'] = 100 + (i % cols) * spacing
            comp['y'] = 100 + (i // cols) * spacing
        self.update()
    
    def undo(self):
        if not self.undo_stack:
            return
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        if action[0] == 'add':
            self.components = [c for c in self.components if c['id'] != action[1]['id']]
        elif action[0] == 'delete':
            self.components.append(action[1])
        elif action[0] == 'add_wire':
            self.connections = [c for c in self.connections if c['id'] != action[1]['id']]
        self.update()
    
    def redo(self):
        if not self.redo_stack:
            return
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        if action[0] == 'add':
            self.components.append(action[1])
        elif action[0] == 'delete':
            self.components = [c for c in self.components if c['id'] != action[1]['id']]
        elif action[0] == 'add_wire':
            self.connections.append(action[1])
        self.update()
    
    def show_context_menu(self, pos, component):
        menu = QMenu(self)
        menu.addAction("Editar Valor").triggered.connect(lambda: self.edit_component_value(component))
        menu.addAction("Rotacionar").triggered.connect(self.rotate_selected)
        menu.addSeparator()
        menu.addAction("Excluir").triggered.connect(self.delete_selected)
        menu.exec(pos)
    
    def edit_component_value(self, component):
        text, ok = QInputDialog.getText(self, "Editar", f"Valor para {component['name']}:", text=component.get('value', ''))
        if ok:
            component['value'] = text
            self.update()
    
    def get_circuit_data(self):
        return {'components': self.components, 'connections': self.connections, 'counter': self.component_counter}
    
    def load_circuit_data(self, data):
        self.components = data.get('components', [])
        self.connections = data.get('connections', [])
        self.component_counter = data.get('counter', {})
        self.selected_component = None
        self.update()
    
    def get_netlist(self):
        lines = ["* Dan_simulation_circuit - SPICE Netlist", ""]
        node_counter = 1
        for comp in self.components:
            t, n, v = comp['type'], comp['name'], comp.get('value', '')
            if t == 'gnd':
                continue
            if t in ['resistor', 'capacitor', 'indutor']:
                lines.append(f"{n} n{node_counter} n{node_counter+1} {v}")
                node_counter += 2
            elif t == 'voltage_source':
                lines.append(f"{n} n{node_counter} 0 DC {v}")
                node_counter += 1
        lines.append("\n.END")
        return "\n".join(lines)
    
    def parse_value(self, value_str):
        if not value_str:
            return 0.0
        mults = {'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3, 'k': 1e3, 'K': 1e3, 'M': 1e6, 'G': 1e9}
        value_str = str(value_str).replace(' ', '').replace('Ω', '').replace('V', '').replace('A', '').replace('F', '').replace('H', '')
        for s, m in mults.items():
            if s in value_str:
                try:
                    return float(value_str.replace(s, '')) * m
                except:
                    pass
        try:
            return float(value_str)
        except:
            return 0.0
    
    def get_component_by_id(self, comp_id):
        for c in self.components:
            if c['id'] == comp_id:
                return c
        return None
    
    def find_connected_components(self, component):
        connected = []
        cid = component['id']
        for conn in self.connections:
            if conn['from_component'] == cid:
                other = self.get_component_by_id(conn['to_component'])
                if other:
                    connected.append({'component': other})
            elif conn['to_component'] == cid:
                other = self.get_component_by_id(conn['from_component'])
                if other:
                    connected.append({'component': other})
        return connected
    
    def simulate(self):
        results = {'nodes': {}, 'currents': {}, 'power': {}, 'voltages': {}}
        voltage_sources = [{'name': c['name'], 'voltage': self.parse_value(c.get('value', '0'))} for c in self.components if c['type'] in ['voltage_source', 'vcc']]
        for vs in voltage_sources:
            results['voltages'][vs['name']] = vs['voltage']
        total_voltage = sum(vs['voltage'] for vs in voltage_sources) or 12.0
        resistors = [{'name': c['name'], 'resistance': self.parse_value(c.get('value', '1k')), 'component': c} for c in self.components if c['type'] == 'resistor']
        total_resistance = sum(r['resistance'] for r in resistors if r['resistance'] > 0)
        total_current = total_voltage / total_resistance if total_resistance > 0 else 0.0
        for vs in voltage_sources:
            results['nodes'][f"V({vs['name']}+)"] = vs['voltage']
            results['nodes'][f"V({vs['name']}-)"] = 0.0
        node_voltage = total_voltage
        for res in resistors:
            r, name = res['resistance'], res['name']
            connected = self.find_connected_components(res['component'])
            current = next((self.parse_value(c['component'].get('value', '0')) for c in connected if c['component']['type'] == 'current_source'), None) or total_current
            v_drop = current * r
            results['currents'][name] = current
            results['power'][name] = current * current * r
            results['voltages'][name] = v_drop
            results['nodes'][f"V({name}+)"] = node_voltage
            node_voltage -= v_drop
            results['nodes'][f"V({name}-)"] = node_voltage
        for c in self.components:
            if c['type'] in ['diode', 'led', 'schottky']:
                vd = {'led': 2.0, 'schottky': 0.3}.get(c['type'], 0.7)
                if total_current > 0:
                    results['currents'][c['name']] = total_current
                    results['power'][c['name']] = vd * total_current
                    results['voltages'][c['name']] = vd
            elif c['type'] == 'capacitor':
                results['currents'][c['name']] = 0.0
                results['power'][c['name']] = 0.0
                results['voltages'][c['name']] = total_voltage
            elif c['type'] == 'indutor':
                results['currents'][c['name']] = total_current
                results['power'][c['name']] = 0.0
                results['voltages'][c['name']] = 0.0
        results['summary'] = {'total_voltage': total_voltage, 'total_resistance': total_resistance, 'total_current': total_current, 'num_components': len(self.components), 'num_connections': len(self.connections)}
        return results
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1a1a2e"))
        painter.translate(self.pan_offset)
        painter.scale(self.zoom_level, self.zoom_level)
        if self.show_grid:
            self.draw_grid(painter)
        self.draw_connections(painter)
        if self.wire_mode and self.wire_start and self.temp_wire_end:
            self.draw_temp_wire(painter)
        for comp in self.components:
            if comp.get('visible', True):
                self.draw_component(painter, comp)
        if self.selected_component:
            self.draw_selection(painter, self.selected_component)
    
    def draw_grid(self, painter):
        view_rect = QRectF(-self.pan_offset.x() / self.zoom_level, -self.pan_offset.y() / self.zoom_level, self.width() / self.zoom_level, self.height() / self.zoom_level)
        sx, sy = int(view_rect.left() / self.grid_size) * self.grid_size, int(view_rect.top() / self.grid_size) * self.grid_size
        painter.setPen(QPen(QColor("#3a3a5a"), 2))
        for x in range(sx, int(view_rect.right()) + self.grid_size, self.grid_size):
            for y in range(sy, int(view_rect.bottom()) + self.grid_size, self.grid_size):
                painter.drawPoint(x, y)
    
    def draw_connections(self, painter):
        painter.setPen(QPen(QColor("#00ff88"), 2))
        for conn in self.connections:
            fc = next((c for c in self.components if c['id'] == conn['from_component']), None)
            tc = next((c for c in self.components if c['id'] == conn['to_component']), None)
            if fc and tc:
                ft, tt = self.get_terminal_positions(fc), self.get_terminal_positions(tc)
                fi, ti = conn.get('from_terminal', 0), conn.get('to_terminal', 0)
                if fi < len(ft) and ti < len(tt):
                    x1, y1, x2, y2 = ft[fi][0], ft[fi][1], tt[ti][0], tt[ti][1]
                    path = QPainterPath()
                    path.moveTo(x1, y1)
                    path.lineTo((x1+x2)/2, y1)
                    path.lineTo((x1+x2)/2, y2)
                    path.lineTo(x2, y2)
                    painter.drawPath(path)
    
    def draw_temp_wire(self, painter):
        painter.setPen(QPen(QColor("#ffff00"), 2, Qt.PenStyle.DashLine))
        ft = self.get_terminal_positions(self.wire_start)
        if self.wire_start_terminal < len(ft):
            painter.drawLine(int(ft[self.wire_start_terminal][0]), int(ft[self.wire_start_terminal][1]), int(self.temp_wire_end[0]), int(self.temp_wire_end[1]))
    
    def draw_selection(self, painter, comp):
        painter.setPen(QPen(QColor("#00aaff"), 2, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(int(comp['x'] - 55), int(comp['y'] - 45), 110, 90)
    
    def draw_component(self, painter, comp):
        cx, cy, ct, rot = comp['x'], comp['y'], comp['type'], comp.get('rotation', 0)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(rot)
        painter.setPen(QPen(QColor("#00ff88"), 2))
        painter.setBrush(QBrush(QColor("#1a1a2e")))
        {'resistor': self.draw_resistor, 'capacitor': self.draw_capacitor, 'indutor': self.draw_inductor, 'voltage_source': lambda p: self.draw_voltage_source(p, False), 'voltage_ac': lambda p: self.draw_voltage_source(p, True), 'current_source': self.draw_current_source, 'gnd': self.draw_ground, 'vcc': self.draw_vcc, 'diode': self.draw_diode, 'schottky': self.draw_diode, 'zener': self.draw_zener, 'led': self.draw_led, 'transistor_npn': self.draw_transistor_npn, 'transistor_pnp': self.draw_transistor_pnp, 'mosfet_n': lambda p: self.draw_mosfet(p, True), 'mosfet_p': lambda p: self.draw_mosfet(p, False), 'opamp': self.draw_opamp, 'switch': self.draw_switch, 'probe': self.draw_probe, 'relay': self.draw_relay, 'ammeter': self.draw_ammeter}.get(ct, self.draw_generic)(painter)
        painter.restore()
        self.draw_terminals(painter, comp)
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(int(cx - 40), int(cy + 35), comp.get('name', ''))
        if comp.get('value'):
            painter.drawText(int(cx - 40), int(cy + 48), f"{comp['value']}{comp.get('unit', '')}")
    
    def draw_terminals(self, painter, comp):
        painter.setPen(QPen(QColor("#ff6600"), 2))
        painter.setBrush(QBrush(QColor("#ff6600")))
        for tx, ty in self.get_terminal_positions(comp):
            painter.drawEllipse(int(tx - 4), int(ty - 4), 8, 8)
    
    def draw_resistor(self, p):
        path = QPainterPath()
        path.moveTo(-40, 0)
        path.lineTo(-30, 0)
        for i in range(6):
            path.lineTo(-25 + i * 10, -10 if i % 2 == 0 else 10)
        path.lineTo(30, 0)
        path.lineTo(40, 0)
        p.drawPath(path)
    
    def draw_capacitor(self, p):
        p.drawLine(-30, 0, -8, 0)
        p.drawLine(8, 0, 30, 0)
        p.drawLine(-8, -20, -8, 20)
        p.drawLine(8, -20, 8, 20)
    
    def draw_inductor(self, p):
        p.drawLine(-40, 0, -30, 0)
        for i in range(4):
            p.drawArc(int(-30 + i * 15), -8, 15, 16, 0, 180 * 16)
        p.drawLine(30, 0, 40, 0)
    
    def draw_voltage_source(self, p, ac=False):
        p.drawEllipse(-20, -20, 40, 40)
        p.drawLine(0, -30, 0, -20)
        p.drawLine(0, 20, 0, 30)
        if ac:
            path = QPainterPath()
            path.moveTo(-10, 0)
            path.cubicTo(-5, -10, 5, 10, 10, 0)
            p.drawPath(path)
        else:
            p.drawLine(-8, -8, 8, -8)
            p.drawLine(0, -14, 0, -2)
            p.drawLine(-8, 8, 8, 8)
    
    def draw_current_source(self, p):
        p.drawEllipse(-20, -20, 40, 40)
        p.drawLine(0, 15, 0, -15)
        p.drawLine(0, -15, -5, -5)
        p.drawLine(0, -15, 5, -5)
        p.drawLine(0, -30, 0, -20)
        p.drawLine(0, 20, 0, 30)
    
    def draw_ground(self, p):
        p.drawLine(0, -20, 0, 0)
        p.drawLine(-15, 0, 15, 0)
        p.drawLine(-10, 6, 10, 6)
        p.drawLine(-5, 12, 5, 12)
    
    def draw_vcc(self, p):
        p.drawLine(0, 20, 0, 5)
        path = QPainterPath()
        path.moveTo(-12, 5)
        path.lineTo(12, 5)
        path.lineTo(0, -15)
        path.closeSubpath()
        p.drawPath(path)
    
    def draw_diode(self, p):
        p.drawLine(-30, 0, -10, 0)
        p.drawLine(10, 0, 30, 0)
        path = QPainterPath()
        path.moveTo(-10, -15)
        path.lineTo(-10, 15)
        path.lineTo(10, 0)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(10, -15, 10, 15)
    
    def draw_zener(self, p):
        self.draw_diode(p)
        p.drawLine(10, -15, 5, -15)
        p.drawLine(10, 15, 15, 15)
    
    def draw_led(self, p):
        self.draw_diode(p)
        p.drawLine(0, -20, 8, -28)
        p.drawLine(8, -28, 4, -24)
        p.drawLine(8, -28, 4, -28)
        p.drawLine(8, -15, 16, -23)
        p.drawLine(16, -23, 12, -19)
        p.drawLine(16, -23, 12, -23)
    
    def draw_transistor_npn(self, p):
        p.drawEllipse(-25, -25, 50, 50)
        p.drawLine(-30, 0, -10, 0)
        p.drawLine(-10, -15, -10, 15)
        p.drawLine(-10, -10, 20, -20)
        p.drawLine(20, -20, 30, -20)
        p.drawLine(-10, 10, 20, 20)
        p.drawLine(20, 20, 30, 20)
    
    def draw_transistor_pnp(self, p):
        p.drawEllipse(-25, -25, 50, 50)
        p.drawLine(-30, 0, -10, 0)
        p.drawLine(-10, -15, -10, 15)
        p.drawLine(-10, -10, 20, -20)
        p.drawLine(20, -20, 30, -20)
        p.drawLine(-10, 10, 20, 20)
        p.drawLine(20, 20, 30, 20)
    
    def draw_mosfet(self, p, n=True):
        p.drawLine(-30, 0, -15, 0)
        p.drawLine(-15, -15, -15, 15)
        p.drawLine(-10, -15, -10, -5)
        p.drawLine(-10, 5, -10, 15)
        p.drawLine(-10, -10, 20, -10)
        p.drawLine(20, -10, 30, -20)
        p.drawLine(-10, 10, 20, 10)
        p.drawLine(20, 10, 30, 20)
    
    def draw_opamp(self, p):
        path = QPainterPath()
        path.moveTo(-30, -30)
        path.lineTo(-30, 30)
        path.lineTo(30, 0)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(-40, -15, -30, -15)
        p.drawLine(-40, 15, -30, 15)
        p.drawLine(30, 0, 40, 0)
        p.setFont(QFont("Arial", 10))
        p.drawText(-27, -10, "+")
        p.drawText(-27, 20, "-")
    
    def draw_switch(self, p):
        p.drawLine(-30, 0, -10, 0)
        p.drawLine(10, 0, 30, 0)
        p.drawEllipse(-12, -4, 8, 8)
        p.drawEllipse(4, -4, 8, 8)
        p.drawLine(-8, 0, 15, -15)
    
    def draw_probe(self, p):
        p.drawEllipse(-15, -15, 30, 30)
        p.drawLine(-8, -8, 8, 8)
        p.drawLine(-8, 8, 8, -8)
        p.drawLine(0, 15, 0, 20)
    
    def draw_relay(self, p):
        p.drawRect(-20, -25, 15, 50)
        p.drawLine(10, -20, 10, -10)
        p.drawLine(10, 10, 10, 20)
        p.drawLine(10, -10, 25, 5)
        p.drawLine(-40, -20, -20, -20)
        p.drawLine(-40, 20, -20, 20)
        p.drawLine(10, -20, 40, -20)
        p.drawLine(10, 20, 40, 20)
    
    def draw_ammeter(self, p):
        p.drawEllipse(-20, -20, 40, 40)
        p.drawLine(-20, 0, -30, 0)
        p.drawLine(20, 0, 30, 0)
        p.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        p.drawText(-6, 6, "A")
    
    def draw_generic(self, p):
        p.drawRect(-25, -20, 50, 40)
        p.drawLine(-40, 0, -25, 0)
        p.drawLine(25, 0, 40, 0)
