import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as Record
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/qds'))
from qbs_source import SourceError, filename_period, inspect_book, select_source
from refresh_qbs import inspect_release


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def file(self, name, data=b'QBS test data'):
        p = self.root / name
        p.write_bytes(data)
        os.utime(p, (time.time()-120, time.time()-120))
        return p

    def test_only_qbs_files_and_no_subdirectories(self):
        self.file('bermuda-core-database.xlsx')
        self.file('QBS notes.xlsx')
        self.file('~$QBS Q4 2027 Final.xls')
        self.file('QBS Q4 2027 Draft.xls')
        (self.root / 'archive').mkdir()
        (self.root / 'archive/QBS Q4 2028 Final.xls').write_bytes(b'ignore')
        expected = self.file('QBS Q1 2026 Final.xls')
        self.assertEqual(select_source(self.root), (expected, (2026, 1)))

    def test_latest_publication_not_latest_file_timestamp(self):
        latest = self.file('QBS Q1 2027 Final.xls')
        older = self.file('QBS Q4 2026 Final.xls')
        os.utime(older, (time.time()-70, time.time()-70))
        self.assertEqual(select_source(self.root)[0], latest)

    def test_conflicting_same_quarter_needs_review(self):
        self.file('QBS Q1 2026 Final.xls', b'one')
        self.file('QBS Q1 2026 Revised.xls', b'two')
        with self.assertRaisesRegex(SourceError, 'Several different'):
            select_source(self.root)

    def test_identical_duplicates_are_safe(self):
        self.file('QBS Q1 2026 Final.xls')
        self.file('QBS Q1 2026 Final (1).xls')
        self.assertEqual(select_source(self.root)[1], (2026, 1))

    def test_copy_in_progress_is_not_imported(self):
        self.file('QBS Q1 2026 Final.xls')
        p = self.file('QBS Q2 2026 Final.xls')
        os.utime(p, None)
        with self.assertRaisesRegex(SourceError, 'just written'):
            select_source(self.root)

    def test_symlinks_are_not_followed(self):
        original = self.file('other.xlsx')
        (self.root / 'QBS Q1 2026 Final.xls').symlink_to(original)
        with self.assertRaisesRegex(SourceError, 'No QBS release'):
            select_source(self.root)

    def test_xlsx_name_supported(self):
        self.assertEqual(filename_period('QBS Q2 2028 Final.xlsx'), (2028, 2))
        self.assertIsNone(filename_period('QBS Q5 2028 Final.xlsx'))

    def test_older_release_does_not_roll_back_site(self):
        self.file('QBS Q1 2026 Final.xls')
        with patch('refresh_qbs.latest_published', return_value=((2026, 2), {'edition': 'Q2 2026'})):
            with self.assertRaisesRegex(SourceError, 'older QBS'):
                inspect_release(self.root, {'source_directory': str(self.root)})

    def test_resave_without_table_changes_is_unchanged(self):
        self.file('QBS Q1 2026 Final.xls')
        published = {'edition': 'Q1 2026', 'sourceSha256': 'old-file', 'dataSha256': 'same-tables'}
        def extract(site, config, source, target):
            target.write_text(json.dumps({'dataSha256': 'same-tables'}))
        with patch('refresh_qbs.latest_published', return_value=((2026, 1), published)), patch('refresh_qbs.extract_source', side_effect=extract):
            self.assertEqual(inspect_release(self.root, {'source_directory': str(self.root)})['status'], 'unchanged')

    def test_revised_values_are_detected(self):
        self.file('QBS Q1 2026 Final.xls')
        published = {'edition': 'Q1 2026', 'sourceSha256': 'old-file', 'dataSha256': 'old-tables'}
        def extract(site, config, source, target):
            target.write_text(json.dumps({'dataSha256': 'revised-tables'}))
        with patch('refresh_qbs.latest_published', return_value=((2026, 1), published)), patch('refresh_qbs.extract_source', side_effect=extract):
            self.assertEqual(inspect_release(self.root, {'source_directory': str(self.root)})['status'], 'available')

    def test_filename_cover_mismatch_is_rejected(self):
        rows = [['QUARTERLY BULLETIN OF STATISTICS', 'ANNEX I'], ['1st Qtr 2026'], ['TABLE OF CONTENTS']]
        cover = Record(nrows=len(rows), row=lambda r: [Record(value=v) for v in rows[r]])
        book = Record(sheet_by_index=lambda _: cover)
        with self.assertRaisesRegex(SourceError, 'does not match'):
            inspect_book(book, 'QBS Q2 2026 Final.xls', {'tables': []})


if __name__ == '__main__':
    unittest.main()
