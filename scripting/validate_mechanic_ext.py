from pathlib import Path

from Lib.extensionBundle import ExtensionBundle

folder = Path(".extensions_cache")

if __name__ == "__main__":
    errorsLog = []
    for eachPath in folder.glob("**/*.roboFontExt"):
        bundle = ExtensionBundle.load(bundlePath=eachPath)
        errors = bundle.validationErrors()

        if errors:
            errorsLog.append(eachPath.name)
            for eachError in errors.splitlines():
                errorsLog.append(f"\t{eachError}")
            errorsLog.append("")

    (folder / "_errors.txt").write_text("\n".join(errorsLog))
