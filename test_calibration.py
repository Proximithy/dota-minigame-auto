import json
from pathlib import Path
import tempfile
import unittest
import shutil
from calibration import load_calibration

SOURCE=Path(__file__).parent/'default_calibration'


class CalibrationTests(unittest.TestCase):
    def test_fresh_profile_loads_embedded_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile=Path(tmp)/'profile'
            result=load_calibration(profile,SOURCE)
            self.assertEqual(result[3],'embedded')
            self.assertEqual(result[0]['arena']['width'],551)
            self.assertFalse(profile.exists())

    def test_saved_recalibration_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile=Path(tmp)/'profile';shutil.copytree(SOURCE,profile)
            path=profile/'config.json';config=json.loads(path.read_text())
            config['arena']['left']=123
            path.write_text(json.dumps(config))
            result=load_calibration(profile,SOURCE)
            self.assertEqual(result[3],'saved')
            self.assertEqual(result[0]['arena']['left'],123)

    def test_corrupt_saved_falls_back_to_embedded(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile=Path(tmp);(profile/'config.json').write_text('broken')
            self.assertEqual(load_calibration(profile,SOURCE)[3],'embedded')
            self.assertEqual((profile/'config.json').read_text(),'broken')

    def test_missing_both_requires_calibration(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(load_calibration(Path(tmp)/'a',Path(tmp)/'b'))


if __name__=='__main__':unittest.main()
