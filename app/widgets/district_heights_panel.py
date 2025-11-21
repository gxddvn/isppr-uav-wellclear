from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout,
    QSpinBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt

class DistrictHeightsPanel(QWidget):
    heights_updated = pyqtSignal(dict)

    def __init__(self, kyiv_map_layer, parent=None):
        super().__init__(parent)
        self.kyiv = kyiv_map_layer
        self.init_ui()
        self.reload_table()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Район", "Мінімальна висота (м)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Експорт висот")
        self.load_btn = QPushButton("Імпорт висот")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.load_btn)
        layout.addLayout(btn_layout)

        self.save_btn.clicked.connect(self.on_export)
        self.load_btn.clicked.connect(self.on_import)

    def reload_table(self):
        districts = self.kyiv.districts
        self.table.setRowCount(len(districts))
        for i, d in enumerate(districts):
            name_item = QTableWidgetItem(d["name"])
            name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(i, 0, name_item)

            spin = QSpinBox()
            spin.setRange(0, 5000)
            spin.setValue(int(d.get("min_altitude", 0)))
            spin.valueChanged.connect(self._make_on_value_changed(i))
            self.table.setCellWidget(i, 1, spin)

    def _make_on_value_changed(self, row):
        def handler(val):
            name = self.table.item(row, 0).text()
            self.kyiv.set_min_altitude_for_district_by_name(name, float(val))
            mapping = {d["name"]: d["min_altitude"] for d in self.kyiv.districts}
            self.heights_updated.emit(mapping)
        return handler

    def on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти мін. висоти", "", "JSON Files (*.json)")
        if path:
            try:
                self.kyiv.export_min_altitudes(path)
                QMessageBox.information(self, "Експорт", "Експортовано успішно")
            except Exception as e:
                QMessageBox.warning(self, "Помилка", f"Не вдалось експортувати: {e}")

    def on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Імпортувати мін. висоти", "", "JSON Files (*.json)")
        if path:
            ok = self.kyiv.import_min_altitudes(path)
            if ok:
                self.reload_table()
                mapping = {d["name"]: d["min_altitude"] for d in self.kyiv.districts}
                self.heights_updated.emit(mapping)
                QMessageBox.information(self, "Імпорт", "Імпортовано успішно")
            else:
                QMessageBox.warning(self, "Помилка", "Не вдалося імпортувати файл")
