"""Release-boundary, portable configuration and documentation checks."""
from pathlib import Path
import re
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublicLayoutTest(unittest.TestCase):
    def test_only_reviewed_model_groups(self):
        self.assertEqual({p.name for p in (ROOT/'models').iterdir() if p.is_dir()},
                         {'cable_passthrough', 'plate_cleanup', 'tplink_panels'})
        self.assertEqual(len(list((ROOT/'models').rglob('*.3mf'))), 10)
        for project in (ROOT/'models').rglob('*.3mf'):
            self.assertTrue(project.with_suffix('.stl').is_file())

    def test_codex_is_optional_and_portable(self):
        content = (ROOT/'.codex/config.toml').read_text()
        config = tomllib.loads(content)
        self.assertNotIn('/Users/', content)
        self.assertNotIn('/Applications/', content)
        for server in config['mcp_servers'].values():
            self.assertFalse(server['enabled'])
            self.assertFalse(server['required'])
            self.assertFalse(Path(server['command']).is_absolute())
        allowed = config['mcp_servers']['bambu_modeling']['enabled_tools']
        self.assertIn('slice_stl', allowed)
        self.assertFalse(any('print' in name or 'send' in name for name in allowed))

    def test_markdown_local_links_exist(self):
        for document in ROOT.rglob('*.md'):
            if any(part.startswith('.') for part in document.relative_to(ROOT).parts):
                continue
            for link in re.findall(r'\]\(([^)]+)\)', document.read_text()):
                if '://' in link or link.startswith('#'):
                    continue
                self.assertTrue((document.parent/link.split('#')[0]).exists(), (document,link))

    def test_no_personal_paths_in_public_text(self):
        for parent in ('models', 'docs', '.codex'):
            for path in (ROOT/parent).rglob('*'):
                if path.suffix in ('.md', '.toml', '.json'):
                    self.assertNotIn('/Users/', path.read_text(), path)


if __name__ == '__main__':
    unittest.main()
