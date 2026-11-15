"""Generate the Burp Dastardly root-validation patch from the pinned source.

Writes upstream-proposals/0001-burp-dastardly-root-validation.patch as a valid
unified diff (git-apply and patch(1) compatible) against the pinned 3.5.101
parser. Run: .venv/bin/python upstream-proposals/generate_patch.py
"""
from __future__ import annotations

import difflib
from pathlib import Path

PINNED = Path(
    "/home/sajjad/.hermes/cache/scratch/ddslab-source-clean/3.5.101"
    "/dojo/tools/burp_dastardly/parser.py"
)
OUT = Path(__file__).with_name("0001-burp-dastardly-root-validation.patch")

ANCHOR_IMPORT = "from defusedxml import ElementTree\n"
NEW_IMPORTS = (
    "from defusedxml import ElementTree\n"
)
ANCHOR_ALLOW = '''    def get_findings(self, xml_output, test):
        tree = ElementTree.parse(xml_output, ElementTree.XMLParser())
        return self.get_items(tree, test)
'''
NEW_BLOCK = '''    # JUnit-style report roots produced by Dastardly. The documented format
    # wraps results in <testsuites>; a bare <testsuite> root is also accepted
    # for compatibility with historical exports.
    ALLOWED_ROOTS = {"testsuites", "testsuite"}

    def get_findings(self, xml_output, test):
        tree = ElementTree.parse(xml_output, ElementTree.XMLParser())
        root = tree.getroot()
        if root.tag.rpartition("}")[2] not in self.ALLOWED_ROOTS:
            msg = (
                f"Unexpected root element '{root.tag}' in Burp Dastardly "
                f"report; expected 'testsuites'. Refusing to treat an "
                f"out-of-contract document as an empty scan."
            )
            logger.warning(msg)
            raise ValueError(msg)
        return self.get_items(tree, test)
'''


def main() -> None:
    original = PINNED.read_text()
    assert original.count(ANCHOR_IMPORT) == 1
    assert original.count(ANCHOR_ALLOW) == 1
    fixed = original.replace(ANCHOR_IMPORT, NEW_IMPORTS, 1)
    fixed = fixed.replace(ANCHOR_ALLOW, NEW_BLOCK, 1)
    assert fixed != original
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        fixed.splitlines(keepends=True),
        fromfile="a/dojo/tools/burp_dastardly/parser.py",
        tofile="b/dojo/tools/burp_dastardly/parser.py",
    )
    OUT.write_text("".join(diff))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
