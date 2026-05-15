from __future__ import annotations


def set_label_text_if_changed(label, text: object) -> bool:
    value = str(text)
    if label.text() == value:
        return False
    label.setText(value)
    return True


def set_bar_value_if_changed(bar, value: int) -> bool:
    active = int(value)
    if bar.value() == active:
        return False
    bar.setValue(active)
    return True


def set_widget_property_if_changed(widget, name: str, value: object, *, repolish: bool = False) -> bool:
    if widget.property(name) == value:
        return False
    widget.setProperty(name, value)
    if repolish:
        repolish_if_changed(widget, True)
    return True


def repolish_if_changed(widget, changed: bool) -> None:
    if not changed:
        return
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def set_chip_text_and_tone_if_changed(chip, text: object, tone: str) -> bool:
    text_changed = set_label_text_if_changed(chip, text)
    tone_changed = set_widget_property_if_changed(chip, "chipTone", tone)
    repolish_if_changed(chip, text_changed or tone_changed)
    return text_changed or tone_changed


def set_combo_value_if_changed(combo, value: str) -> bool:
    if combo.currentText() == value:
        return False
    combo.setCurrentText(value)
    return True
