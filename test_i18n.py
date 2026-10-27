import json
from pathlib import Path
from string import Formatter
import tempfile
import tkinter as tk
import unittest
from i18n import EN, LocalizedVar, flag_image, load_language, message, save_language, translate


class LanguageTests(unittest.TestCase):
    def test_format_fields_match_in_every_translation(self):
        fields = lambda value: {field for _, field, _, _ in Formatter().parse(value) if field is not None}
        for portuguese, english in EN.items():
            self.assertTrue(english)
            self.assertEqual(fields(portuguese), fields(english), portuguese)

    def test_nested_status_and_prompt_translate_at_render_time(self):
        status = message('{state} • Bola {ball:.0%} • Raquete {paddle:.0%} • {mode}',
                         state='Instrução de lançamento detectada: 0.5/0.8s', ball=.95, paddle=.8, mode='Observação')
        self.assertEqual(translate('en', status), 'Launch prompt detected: 0.5/0.8s • Ball 95% • Paddle 80% • Preview')
        self.assertIn('Bola 95%', translate('pt-BR', status))

    def test_existing_message_refreshes_without_changing_its_data(self):
        language = ['pt-BR']
        variable = LocalizedVar(tk.Tcl(), lambda: language[0], message('Diagnóstico salvo em {folder}', folder=r'C:\capture'))
        language[0] = 'en'
        variable.refresh()
        self.assertEqual(variable.get(), r'Diagnostics saved to C:\capture')
        language[0] = 'pt-BR'
        variable.refresh()
        self.assertEqual(variable.get(), r'Diagnóstico salvo em C:\capture')

    def test_language_round_trip_preserves_calibration_and_other_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder/'config.json').write_bytes(b'calibration must remain identical')
            (folder/'settings.json').write_text(json.dumps({'other': 42}), encoding='utf-8')
            for language in ('en', 'pt-BR'):
                save_language(folder, language)
                self.assertEqual(load_language(folder), language)
                self.assertEqual(json.loads((folder/'settings.json').read_text())['other'], 42)
                self.assertEqual((folder/'config.json').read_bytes(), b'calibration must remain identical')
            self.assertFalse((folder/'settings.tmp').exists())

    def test_missing_or_invalid_preferences_default_to_portuguese_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'new'
            self.assertEqual(load_language(folder), 'pt-BR')
            self.assertFalse(folder.exists())
            folder.mkdir()
            for content in ('{', '[]', '{"language":"fr"}', 'null'):
                (folder/'settings.json').write_text(content)
                self.assertEqual(load_language(folder), 'pt-BR')
            with self.assertRaises(ValueError): save_language(folder, 'fr')

    def test_preference_write_failure_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocked = Path(tmp)/'file'
            blocked.write_text('not a folder')
            with self.assertRaises(OSError): save_language(blocked, 'en')

    def test_flags_render_as_different_local_images(self):
        brazil, usa = flag_image('pt-BR'), flag_image('en')
        self.assertEqual(brazil.size, (30,20))
        self.assertEqual(usa.size, brazil.size)
        self.assertNotEqual(brazil.tobytes(), usa.tobytes())


if __name__ == '__main__': unittest.main()
