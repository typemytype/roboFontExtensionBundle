from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from roboFontExtensionBundle.bundle import ExtensionBundle, isValidURL


@pytest.fixture
def dummyOnePath():
    return Path("tests/dummy1.roboFontExt")


@pytest.fixture
def dummyTwoPath():
    return Path("tests/dummy2.roboFontExt")


@pytest.fixture
def singleWindowControllerPath():
    return Path("tests/single_window_controller_template.roboFontExt")


urlToValid = {
    "http://www.cwi.nl:80/%7Eguido/Python.html": True,
    "/data/Python.html": False,
    532: False,
    "dkakasdkjdjakdjadjfalskdjfalk": False,
    "https://stackoverflow.com": True,
    # no double urls allowed
    "https://stackoverflow.com https://stackoverflow.com": False,
}


@pytest.mark.parametrize("url, valid", urlToValid.items())
def test_isValidURL(url, valid):
    assert isValidURL(url) is valid


def test_bundleInfo():
    bundle = ExtensionBundle()

    bundle.name = "test"
    assert bundle.infoDictionary["name"] == "test"

    bundle.developer = "me"
    assert bundle.infoDictionary["developer"] == "me"

    bundle.developerURL = "http://robofont.com"
    assert bundle.infoDictionary["developerURL"] == "http://robofont.com"

    bundle.version = "1.0"
    assert bundle.infoDictionary["version"] == "1.0"

    bundle.timeStamp = 123456789
    assert bundle.infoDictionary["timeStamp"] == 123456789

    bundle.requiresVersionMajor = "1"
    assert bundle.infoDictionary["requiresVersionMajor"] == "1"

    bundle.requiresVersionMinor = "0"
    assert bundle.infoDictionary["requiresVersionMinor"] == "0"

    bundle.expireDate = "2019-01-01"
    assert bundle.infoDictionary["expireDate"] == "2019-01-01"

    bundle.documentationURL = "http://robofont.com"
    assert bundle.infoDictionary["documentationURL"] == "http://robofont.com"


def test_bundleDefaultPaths():
    bundle = ExtensionBundle(path=Path("root/fileName"))
    assert bundle.bundlePath == Path("root/fileName")
    assert bundle.bundlePath.name == "fileName"
    assert bundle.libFolder == Path("root/fileName/lib")
    assert bundle.htmlFolder == Path("root/fileName/html")
    assert bundle.resourcesFolder == Path("root/fileName/resources")
    assert bundle.infoPlistPath == Path("root/fileName/info.plist")
    assert bundle.licensePath == Path("root/fileName/license")
    assert bundle.requirementsPath == Path("root/fileName/requirements.txt")


def test_folder_existance(dummyOnePath):
    bundle = ExtensionBundle(path=dummyOnePath)
    assert not bundle.hasDocumentation
    assert not bundle.hasHTML


def test_readExtension(dummyOnePath):
    bundle = ExtensionBundle()
    bundle.load(dummyOnePath)
    assert bundle.name == "dummy1"
    assert bundle.developer == "TypeMyType"
    assert bundle.developerURL == "http://typemytype.com"
    assert bundle.version == "1.0"


def test_override(dummyOnePath):
    bundle = ExtensionBundle()
    bundle.load(dummyOnePath)
    with pytest.raises(AssertionError):
        bundle.save(destPath=dummyOnePath)


def test_repr(singleWindowControllerPath):
    bundle = ExtensionBundle()
    bundle.load(bundlePath=singleWindowControllerPath)
    assert str(bundle) == "<ExtensionBundle: myExtension>"


def test_expireDate(dummyOnePath):
    bundle = ExtensionBundle()
    bundle.load(dummyOnePath)
    bundle.name = "dummy"
    bundle.developer = "TypeMyType"
    bundle.developerURL = "http://typemytype.com"
    bundle.version = "1.0"
    bundle.addToMenu = []
    assert bundle.hashPath.exists()

    bundle.validate()
    with TemporaryDirectory() as tmpDir:
        with pytest.raises(AssertionError):
            bundle.save(Path(tmpDir) / "dummy2.roboFontExt")
            assert not bundle.validationErrors()


def test_save_dummy(dummyTwoPath):
    bundle = ExtensionBundle()
    bundle.load(dummyTwoPath)
    bundle.name = "dummy3"
    bundle.validate()
    with TemporaryDirectory() as tmpDir:
        bundle.save(Path(tmpDir) / "dummy3.roboFontExt")


def test_save_template(singleWindowControllerPath):
    bundle = ExtensionBundle()
    bundle.load(singleWindowControllerPath)
    bundle.name = "dummy3"
    bundle.validate()
    with TemporaryDirectory() as tmpDir:
        bundle.save(Path(tmpDir) / "foobar.roboFontExt")


def test_extensionHash(dummyOnePath, dummyTwoPath):
    bundleOne = ExtensionBundle()
    bundleOne.load(dummyOnePath)
    h = bundleOne.extensionHash()
    bundleTwo = ExtensionBundle()
    bundleTwo.load(dummyTwoPath)
    assert h != bundleTwo.extensionHash()

    bundleOne = ExtensionBundle()
    bundleOne.load(dummyOnePath)
    assert h == bundleOne.extensionHash()


def test_invalid_plist():
    with pytest.raises(AssertionError):
        bundle = ExtensionBundle()
        bundle.load(bundlePath=Path("tests/missing_plist.roboFontExt"))
    with pytest.raises(Exception):
        bundle = ExtensionBundle()
        bundle.load(bundlePath=Path("tests/corrupted_plist.roboFontExt"))


def test_validation():
    bundle = ExtensionBundle(name="myExtension")
    # if not self.bundlePath.exists():
    assert not bundle.validate()

    # missing lib folder
    with TemporaryDirectory() as tmpDir:
        with pytest.raises(AssertionError):
            assert not bundle.save(Path(tmpDir) / "foobar.roboFontExt")

    # if self.bundlePath.suffix != self.fileExtension:
    with TemporaryDirectory() as tmpDir:
        with pytest.raises(AssertionError):
            bundle.save(Path(tmpDir) / "foobar.robo")

    bundle = ExtensionBundle(name=False)  # type: ignore
    assert not bundle.validate()

    bundle = ExtensionBundle(developer=False)  # type: ignore
    assert not bundle.validate()

    bundle = ExtensionBundle(developerURL=False)  # type: ignore
    assert not bundle.validate()

    bundle = ExtensionBundle(version=False)  # type: ignore
    assert not bundle.validate()

    bundle = ExtensionBundle(addToMenu=set())  # type: ignore
    assert not bundle.validate()

    bundle = ExtensionBundle(addToMenu=[{"path": False}])  # type: ignore
    assert not bundle.validate()

    bundle = ExtensionBundle()
    bundle.load(bundlePath=Path("tests/dummy1.roboFontExt"))
    bundle.addToMenu = [{"path": Path("hello.py")}]  # type: ignore
    assert not bundle.validate()

    bundle.addToMenu = [{"path": "hello.py", "preferredName": "Hello", "shortKey": "H"}]
    assert bundle.validate()

    bundle.addToMenu = [{"path": "hello.py", "preferredName": "Hello", "shortKey": "H", "nestInSubmenus": "yes"}]  # type: ignore
    assert not bundle.validate()

    bundle.addToMenu = [
        {
            "path": "hello.py",
            "preferredName": "Hello",
            "shortKey": "H",
            "nestInSubmenus": False,
        }
    ]
    assert bundle.validate()

    bundle.html = 123  # type: ignore
    assert not bundle.validate()

    bundle.documentationURL = 123  # type: ignore
    assert not bundle.validate()

    bundle.launchAtStartUp = 123  # type: ignore
    assert not bundle.validate()

    bundle.mainScript = False  # type: ignore
    assert not bundle.validate()

    bundle.requiresVersionMajor = 4  # type: ignore
    assert not bundle.validate()

    bundle.requiresVersionMinor = 5  # type: ignore
    assert not bundle.validate()

    bundle.uninstallScript = False  # type: ignore
    assert not bundle.validate()


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
