"""Regression checks for the boundary between the private art queue and the site."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from art_site import attach_art


class ArtSiteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'art' / 'state').mkdir(parents=True)
        (self.root / 'art' / 'generated').mkdir()
        self.output = self.root / 'preview'
        self.moments = [{'id': 'S1-10', 's': 1, 'title': 'Fixture moment'}]

    def receipt(self, job='fixture-art', **changes):
        image = b'\x89PNG\r\n\x1a\nfixture bytes for integrity checks'
        source = self.root / 'art' / 'generated' / f'{job}.png'
        source.write_bytes(image)
        receipt = {
            'schema_version': 1, 'id': job, 'status': 'completed',
            'request': {
                'schema_version': 1, 'id': job, 'kind': 'moment',
                'moment_id': 'S1-10', 'title': 'Private job title',
                'prompt': 'Private generation instructions',
                'references': [{'path': 'PCs/private-reference.png', 'role': 'character'}],
                'alt': 'An illustrated fixture moment',
            },
            'token': 'private-claim-token', 'request_sha256': 'private-request-hash',
            'output': f'art/generated/{job}.png',
            'sha256': hashlib.sha256(image).hexdigest(),
            'completed_at': '2026-09-28T12:00:00Z',
        }
        receipt.update(changes)
        return receipt

    def save(self, receipt, filename=None):
        path = self.root / 'art' / 'state' / f"{filename or receipt['id']}.json"
        path.write_text(json.dumps(receipt), encoding='utf-8')

    def test_completed_art_attaches_without_private_fields_or_source_mutation(self):
        receipt = self.receipt()
        self.save(receipt)
        result = attach_art(self.moments, self.root, self.output)
        art = result[0]['art']
        self.assertEqual(set(art), {'src', 'alt', 'request_id'})
        self.assertEqual(art['alt'], receipt['request']['alt'])
        self.assertEqual(hashlib.sha256((self.output / art['src']).read_bytes()).hexdigest(), receipt['sha256'])
        self.assertNotIn('art', self.moments[0])
        self.assertNotIn('private', json.dumps(result).lower())

    def test_readable_images_also_publish_smaller_web_copies(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow is not installed')
        import io
        buffer = io.BytesIO()
        Image.new('RGB', (2000, 1125), (200, 90, 40)).save(buffer, 'PNG')
        receipt = self.receipt()
        (self.root / receipt['output']).write_bytes(buffer.getvalue())
        receipt['sha256'] = hashlib.sha256(buffer.getvalue()).hexdigest()
        self.save(receipt)
        art = attach_art(self.moments, self.root, self.output)[0]['art']
        self.assertEqual(set(art), {'src', 'alt', 'request_id', 'w', 'h', 'web', 'thumb'})
        self.assertEqual((art['w'], art['h']), (2000, 1125))
        self.assertEqual(hashlib.sha256((self.output / art['src']).read_bytes()).hexdigest(), receipt['sha256'])
        for key, longest in (('web', 1600), ('thumb', 640)):
            with Image.open(self.output / art[key]) as copy:
                self.assertEqual((copy.format, copy.width), ('WEBP', longest))
        self.assertNotIn('private', json.dumps(art).lower())

    def test_test_jobs_and_incomplete_jobs_never_publish(self):
        receipt = self.receipt()
        receipt['request']['kind'] = 'test'
        self.save(receipt)
        self.save(self.receipt('unfinished-art', status='processing'))
        self.assertEqual(attach_art(self.moments, self.root, self.output), self.moments)
        self.assertFalse(self.output.exists())

    def test_unknown_moments_mismatched_ids_and_bad_hashes_never_publish(self):
        unknown = self.receipt('unknown-art')
        unknown['request']['moment_id'] = 'S999-0'
        self.save(unknown)
        self.save(self.receipt('bad-hash', sha256='0' * 64))
        self.save(self.receipt('wrong-receipt'), filename='different-id')
        self.assertEqual(attach_art(self.moments, self.root, self.output), self.moments)
        self.assertFalse(self.output.exists())

    def test_paths_outside_generated_directory_never_publish(self):
        receipt = self.receipt()
        outside = self.root / 'outside.png'
        outside.write_bytes((self.root / receipt['output']).read_bytes())
        for output in ['art/generated/../../outside.png', str(outside), 'outside.png']:
            with self.subTest(output=output):
                receipt['output'] = output
                self.save(receipt)
                self.assertEqual(attach_art(self.moments, self.root, self.output), self.moments)
                self.assertFalse(self.output.exists())

    def test_newest_revision_wins_with_id_tiebreak(self):
        self.save(self.receipt('older', completed_at='2026-09-27T12:00:00Z'))
        self.save(self.receipt('newer-a'))
        self.save(self.receipt('newer-b'))
        result = attach_art(self.moments, self.root, self.output)
        self.assertEqual(result[0]['art']['request_id'], 'newer-b')
        self.assertEqual(len(list((self.output / 'media' / 'art').iterdir())), 1)

    def test_malformed_receipts_do_not_break_the_build(self):
        folder = self.root / 'art' / 'state'
        (folder / 'broken.json').write_text('{', encoding='utf-8')
        (folder / 'array.json').write_text('[]', encoding='utf-8')
        self.save(self.receipt('bad-snapshot', request=None))
        self.assertEqual(attach_art(self.moments, self.root, self.output), self.moments)


if __name__ == '__main__':
    unittest.main()
