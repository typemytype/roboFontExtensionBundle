from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from Lib.extensionBundle import (ExtensionBundle,
                                 requirementCompareVersionCompareEqualOrBigger,
                                 requirementCompareVersionMustBeEqual)


@pytest.fixture
def dummyPath():
    return Path("tests/dummy.roboFontExt")

def test_bundleInfo():
    bundle = ExtensionBundle()
    assert not bundle.validate()

    bundle.name = "test"
    assert bundle.infoDictionary["name"] == 'test'

    bundle.developer = "me"
    assert bundle.infoDictionary["developer"] == 'me'

    bundle.developerURL = "http://robofont.com"
    assert bundle.infoDictionary["developerURL"] == 'http://robofont.com'

    bundle.version = "1.0"
    assert bundle.infoDictionary["version"] == '1.0'

    bundle.timeStamp = 123456789
    assert bundle.infoDictionary['timeStamp'] == 123456789

    bundle.requiresVersionMajor = "1"
    assert bundle.infoDictionary['requiresVersionMajor'] == '1'

    bundle.requiresVersionMinor = "0"
    assert bundle.infoDictionary['requiresVersionMinor'] == "0"

    bundle.expireDate = "2019-01-01"
    assert bundle.infoDictionary['expireDate'] == '2019-01-01'

    bundle.documentationURL = 'http://robofont.com'
    assert bundle.infoDictionary['documentationURL'] == 'http://robofont.com'


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

# FIXME does not apply anymore
# def test_bundleCustomPaths():
#     bundle = ExtensionBundle(path="root/fileName", libName="myLibName", htmlName="myHTMLName", resourcesName="myResourcesName")
#     assert bundle.bundlePath() == os.path.realpath("root/fileName")
#     assert bundle.fileName() == "fileName"
#     assert bundle.libPath() == os.path.realpath("root/fileName/myLibName")
#     assert bundle.HTMLPath() == os.path.realpath("root/fileName/myHTMLName")
#     assert bundle.resourcesPath() == os.path.realpath("root/fileName/myResourcesName")
#     assert bundle.infoDictionaryPath() == os.path.realpath("root/fileName/info.plist")
#     assert bundle.licensePath() == os.path.realpath("root/fileName/license")
#     assert bundle.requirementsPath() == os.path.realpath("root/fileName/requirements.txt")


def test_requirementsLoop():
    bundle = ExtensionBundle()
    requirements = """
    drawBot
    Batch
    myExtension >= 3.0
    myOtherExtension == 4.5
    """
    result = list(bundle.iterParseRequirements(requirements))
    assert result == [
        ("drawBot", None),
        ("Batch", None),
        ("myExtension", (requirementCompareVersionCompareEqualOrBigger, "3.0", "myExtension >= 3.0")),
        ("myOtherExtension", (requirementCompareVersionMustBeEqual, "4.5", "myOtherExtension == 4.5"))
    ]


def test_readExtension(dummyPath):
    bundle = ExtensionBundle.load(dummyPath)
    assert bundle.name == "dummy"
    assert bundle.developer == "TypeMyType"
    assert bundle.developerURL == "http://typemytype.com"
    assert bundle.version == "1.0"

def test_override(dummyPath):
    bundle = ExtensionBundle.load(dummyPath)
    with pytest.raises(AssertionError):
        bundle.save(destPath=dummyPath)

def test_expireDate(dummyPath):
    bundle = ExtensionBundle.load(dummyPath)
    bundle.name = "dummy"
    bundle.developer = "TypeMyType"
    bundle.developerURL = "http://typemytype.com"
    bundle.version = "1.0"
    bundle.addToMenu = []

    with TemporaryDirectory() as tmpDir:
        assert bundle.save(Path(tmpDir) / dummyPath.with_name("dummy2.roboFontExt").name)
        assert not bundle.validationErrors()

        bundle.expireDate = "2019-01-01"
        bundle.save(Path(tmpDir) / dummyPath.with_name("dummy3.roboFontExt").name)
        assert bundle.hashPath.exists()


# def test_hash(tmpdir):
#     path = os.path.join(tmpdir, "test.roboFontExt")
#     bundle = ExtensionBundle()
#     bundle.name = "dummy"
#     bundle.developer = "TypeMyType"
#     bundle.developerURL = "http://typemytype.com"
#     bundle.version = "1.0"
#     bundle.addToMenu = []

#     # bundle.icon = AppKit.NSImage.alloc().initWithSize_((10, 10))
#     bundle.expireDate = "3000-01-01"

#     # add ignored files
#     os.mkdir(os.path.join(tmpdir, "subModule"))

#     open(os.path.join(tmpdir, ".DS_Store"), "w").close()
#     open(os.path.join(tmpdir, f"Icon{chr(0x0D)}"), "w").close()
#     open(os.path.join(tmpdir, "subModule", ".DS_Store"), "w").close()

#     assert sorted(os.listdir(tmpdir)) == sorted([".DS_Store", "subModule", f"Icon{chr(0x0D)}"])

#     assert bundle.save(path, libPath=tmpdir)
#     assert not bundle.validationErrors()

#     hashPath = os.path.join(bundle.bundlePath(), ".hash")
#     assert os.path.exists(hashPath)

#     with open(hashPath, "r") as f:
#         extenstionHash = f.read()
#     assert extenstionHash == bundle.extensionHash("roboFont.extension.hash")

#     succes, message = bundle._installHelper()
#     assert succes

#     # add a file
#     addedPath = os.path.join(path, "lib", "fileAdded.py")
#     open(addedPath, "w").close()
#     with StdOutCollector() as out:
#         succes, message = bundle._installHelper()
#     assert not succes
#     assert message == "Not a valid extension (test.roboFontExt)"
#     assert out.lines() == ['Hash does not match.']
#     # restore added file
#     os.remove(addedPath)
#     succes, message = bundle._installHelper()
#     assert succes

#     # remove .hash
#     hashPath = os.path.join(path, ".hash")
#     os.remove(hashPath)
#     with StdOutCollector() as out:
#         succes, message = bundle._installHelper()
#     assert not succes
#     assert message == "Not a valid extension (test.roboFontExt)"
#     assert out.lines() == ['Missing hash.']
#     # restore removed hash
#     with open(hashPath, "w") as f:
#         f.write(extenstionHash)

#     # missing expire date
#     bundle.expireDate = None
#     with StdOutCollector() as out:
#         succes, message = bundle._installHelper()
#     assert not succes
#     assert message == "Not a valid extension (test.roboFontExt)"
#     assert out.lines() == ['Missing expireDate.']
#     # restore expire date
#     bundle.expireDate = "2022-01-01"

#     # expire date expired
#     bundle.expireDate = "2015-01-01"
#     with StdOutCollector() as out:
#         succes, message = bundle._installHelper()
#     assert not succes
#     assert message == "Extension is expired (test.roboFontExt)"
#     assert out.lines() == ['Extension is expired.']


if __name__ == '__main__':
    import pytest
    pytest.main([__file__])
