from pathlib import Path
import unittest


MOJIBAKE_MARKERS = (
    "\u00f0",
    "\u00c3",
    "\u00c2",
    "\u00e2\u20ac",
    "\u00e2\u201a",
    "\u00e2\u201e",
    "\u00ef\u00b8",
    "\ufffd",
)

TEXT_EXTENSIONS = {
    ".py",
    ".html",
    ".css",
    ".js",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".json",
    ".ini",
    ".cfg",
    ".ps1",
}

SKIP_DIRS = {".git", ".venv", "__pycache__", "deploy"}


class NoMojibakeTest(unittest.TestCase):
    def test_source_files_do_not_contain_mojibake(self):
        repo_root = Path(__file__).resolve().parents[1]
        failures = []

        for path in repo_root.rglob("*"):
            if (
                not path.is_file()
                or path.suffix.lower() not in TEXT_EXTENSIONS
                or any(part in SKIP_DIRS for part in path.parts)
            ):
                continue

            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            for line_number, line in enumerate(text.splitlines(), start=1):
                if any(marker in line for marker in MOJIBAKE_MARKERS):
                    failures.append(f"{path.relative_to(repo_root)}:{line_number}: {line[:120]}")

        self.assertFalse(failures, "Mojibake markers found:\n" + "\n".join(failures[:50]))


if __name__ == "__main__":
    unittest.main()
