from PyQt6.QtWidgets import QLineEdit, QSpinBox
from .inputs import Input, InputTypes


class PyQtInputFactory:

    @staticmethod
    def create(input_def: Input):
        if input_def.type() == InputTypes.TEXT:
            widget = QLineEdit()
            widget.setPlaceholderText(input_def.placeholder())

            if input_def.default() is not None:
                widget.setText(str(input_def.default()))

            c = input_def.constraints()
            if "maxLength" in c:
                widget.setMaxLength(int(c["maxLength"]))

            return widget

        if input_def.type() == InputTypes.NUMBER:
            widget = QSpinBox()

            c = input_def.constraints()
            if "min" in c:
                widget.setMinimum(int(c["min"]))
            if "max" in c:
                widget.setMaximum(int(c["max"]))

            if input_def.default() is not None:
                widget.setValue(int(input_def.default()))

            return widget

        raise ValueError(f"Unsupported input type: {input_def.type()}")
