from pathlib import Path

from Lib.robofontExtensionBundle import ExtensionBundle

if __name__ == '__main__':
    bundle = ExtensionBundle.load(bundlePath=Path("tests/single_window_controller_template.roboFontExt"))
    bundle.unpack(destFolder=Path("unpack"))