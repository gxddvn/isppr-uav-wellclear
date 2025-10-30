from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal, QTimer

class PropertiesPanel(QWidget):
    """Редактор параметрів вибраної моделі з двостороннім зв'язуванням."""
    # емитить модель коли ми її змінили через панель
    model_updated = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_model = None

        self.layout = QVBoxLayout(self)
        self.label_model = QLabel("Обрана модель: —")
        self.layout.addWidget(self.label_model)

        self.form = QFormLayout()
        self.edit_speed = QLineEdit()
        self.edit_altitude = QLineEdit()

        self.form.addRow("Швидкість:", self.edit_speed)
        self.form.addRow("Висота:", self.edit_altitude)
        self.layout.addLayout(self.form)

        self.btn_apply = QPushButton("Застосувати")
        self.layout.addWidget(self.btn_apply)
        self.layout.addStretch()

        # сигнали
        self.btn_apply.clicked.connect(self.apply_changes)
        # застосовуємо значення при завершенні редагування (не кожен символ)
        self.edit_speed.editingFinished.connect(self.apply_changes)
        self.edit_altitude.editingFinished.connect(self.apply_changes)

        # таймер для опитування моделі (щоб відображати оновлення в реальному часі)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(200)  # ms
        self._poll_timer.timeout.connect(self._poll_model)
        self._poll_timer.start()

        # збережені значення для виявлення змін (щоб не переписувати якщо користувач редагує)
        self._last_speed = None
        self._last_altitude = None

    def set_model(self, model):
        """Підключення нової моделі до редактора."""
        self.current_model = model
        if model:
            self.label_model.setText(f"Обрана модель: {model.name}")
            # підставляємо значення
            self.edit_speed.setText(str(model.speed))
            self.edit_altitude.setText(str(model.altitude))
            # оновлюємо last-значення
            self._last_speed = model.speed
            self._last_altitude = model.altitude
        else:
            self.label_model.setText("Обрана модель: —")
            self.edit_speed.clear()
            self.edit_altitude.clear()
            self._last_speed = None
            self._last_altitude = None

    def apply_changes(self):
        """Зберегти зміни до об’єкта."""
        if not self.current_model:
            return

        # Якщо користувач зараз редагує (фокус) — не перезаписувати з таймера
        try:
            s_text = self.edit_speed.text().strip()
            a_text = self.edit_altitude.text().strip()

            if s_text != "":
                new_speed = float(s_text)
            else:
                new_speed = self.current_model.speed

            if a_text != "":
                new_alt = float(a_text)
            else:
                new_alt = self.current_model.altitude

            # тільки якщо зміни є — записуємо
            changed = False
            if abs(self.current_model.speed - new_speed) > 1e-9:
                self.current_model.speed = new_speed
                changed = True
            if abs(self.current_model.altitude - new_alt) > 1e-9:
                self.current_model.altitude = new_alt
                changed = True

            if changed:
                # оновлюємо пам'ятні значення
                self._last_speed = self.current_model.speed
                self._last_altitude = self.current_model.altitude
                # емитимо сигнал про оновлення (щоб Scene3D або інші знали)
                self.model_updated.emit(self.current_model)
        except ValueError:
            # тут можна вивести повідомлення про помилку
            pass

    def _poll_model(self):
        """Опитування моделі — оновлюємо поля, якщо модель змінилася зовні."""
        m = self.current_model
        if m is None:
            return

        # Якщо користувач активно редагує поле — не перезаписуємо його
        if self.edit_speed.hasFocus() or self.edit_altitude.hasFocus():
            return

        # Порівняй і онови UI якщо потрібно
        if self._last_speed is None or abs(m.speed - self._last_speed) > 1e-6:
            self.edit_speed.setText(str(m.speed))
            self._last_speed = m.speed

        if self._last_altitude is None or abs(m.altitude - self._last_altitude) > 1e-6:
            self.edit_altitude.setText(str(m.altitude))
            self._last_altitude = m.altitude
