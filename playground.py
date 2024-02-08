from pathlib import Path

from Lib.extensionBundle import ExtensionBundle

if __name__ == '__main__':
    # from data on disk
    folder = Path("single-window-controller")

    bundle = ExtensionBundle(
        name="myExtension",
        developer="Foo Bar",
        developerURL="www.foobar.com",
        launchAtStartUp=True,
        mainScript="foo.py",
        version="2.0",
        license=(folder / "license.txt").read_text()
    )

    bundle.save(
        destPath=folder / "fromSource.roboFontExt",
        libFolder=folder / "source/code",
        htmlFolder=folder / "source/documentation",
        resourcesFolder=folder / "source/resources",
        )

    # # from extension bundle
    # extensionPath = Path("single-window-controller/build/myExtension.roboFontExt")
    # bundle = ExtensionBundle.load(
    #     bundlePath=extensionPath
    # )
    # bundle.save(extensionPath.with_name("temp.roboFontExt"))
    # # bundle.save(path=extensionPath.with_name("myExtension2.roboFontExt"))
