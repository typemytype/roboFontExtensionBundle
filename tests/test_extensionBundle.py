import os

from Lib._extensionBundle import ExtensionBundle


def test_bundleInfo():
    bundle = ExtensionBundle()
    assert not bundle.validate()

    bundle.name = "test"
    assert bundle.infoDictionary == {'name': 'test'}

    bundle.developer = "me"
    assert bundle.infoDictionary == {
        'name': 'test',
        'developer': 'me'
    }

    bundle.developerURL = "http://robofont.com"
    assert bundle.infoDictionary == {
        'name': 'test',
        'developer': 'me',
        'developerURL':
        'http://robofont.com'
    }

    bundle.version = "1.0"
    assert bundle.infoDictionary == {
        'name': 'test',
        'developer': 'me',
        'developerURL': 'http://robofont.com',
        'version': '1.0'
    }

    bundle.timeStamp = 123456789
    assert bundle.infoDictionary == {
        'name': 'test',
        'developer': 'me',
        'developerURL': 'http://robofont.com',
        'version': '1.0',
        'timeStamp': 123456789
    }

    bundle.requiresVersionMajor = "1"
    assert bundle.infoDictionary == {
        'name': 'test',
        'developer': 'me',
        'developerURL': 'http://robofont.com',
        'version': '1.0',
        'timeStamp': 123456789,
        'requiresVersionMajor': '1',
    }

    bundle.requiresVersionMinor = "0"
    assert bundle.infoDictionary == {
        'name': 'test',
        'developer': 'me',
        'developerURL': 'http://robofont.com',
        'version': '1.0',
        'timeStamp': 123456789,
        'requiresVersionMajor': '1',
        'requiresVersionMinor': '0'
    }

    bundle.expireDate = "2019-01-01"
    assert bundle.infoDictionary == {
        'name': 'test',
        'developer': 'me',
        'developerURL': 'http://robofont.com',
        'version': '1.0',
        'timeStamp': 123456789,
        'requiresVersionMajor': '1',
        'requiresVersionMinor': '0',
        'expireDate': '2019-01-01'
    }

    bundle.documentationURL = 'http://robofont.com'
    assert bundle.infoDictionary == {
        'name': 'test',
        'developer': 'me',
        'developerURL': 'http://robofont.com',
        'version': '1.0',
        'timeStamp': 123456789,
        'requiresVersionMajor': '1',
        'requiresVersionMinor': '0',
        'expireDate': '2019-01-01',
        'documentationURL': 'http://robofont.com',
    }


def test_bundleDefaultPaths():
    bundle = ExtensionBundle(path="root/fileName")
    assert bundle.bundlePath() == os.path.realpath("root/fileName")
    assert bundle.fileName() == "fileName"
    assert bundle.libPath() == os.path.realpath("root/fileName/lib")
    assert bundle.HTMLPath() == os.path.realpath("root/fileName/html")
    assert bundle.resourcesPath() == os.path.realpath("root/fileName/resources")
    assert bundle.infoDictionaryPath() == os.path.realpath("root/fileName/info.plist")
    assert bundle.licensePath() == os.path.realpath("root/fileName/license")
    assert bundle.requirementsPath() == os.path.realpath("root/fileName/requirements.txt")


def test_bundleCustomPaths():
    bundle = ExtensionBundle(path="root/fileName", libName="myLibName", htmlName="myHTMLName", resourcesName="myResourcesName")
    assert bundle.bundlePath() == os.path.realpath("root/fileName")
    assert bundle.fileName() == "fileName"
    assert bundle.libPath() == os.path.realpath("root/fileName/myLibName")
    assert bundle.HTMLPath() == os.path.realpath("root/fileName/myHTMLName")
    assert bundle.resourcesPath() == os.path.realpath("root/fileName/myResourcesName")
    assert bundle.infoDictionaryPath() == os.path.realpath("root/fileName/info.plist")
    assert bundle.licensePath() == os.path.realpath("root/fileName/license")
    assert bundle.requirementsPath() == os.path.realpath("root/fileName/requirements.txt")


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
        ("myExtension", (bundle._requirementCompareVersionCompareEqualOrBigger, "3.0", "myExtension >= 3.0")),
        ("myOtherExtension", (bundle._requirementCompareVersionMustBeEqual, "4.5", "myOtherExtension == 4.5"))
    ]


def test_readExtension():
    path = os.path.join(testDataDir, "dummy.roboFontExt")
    bundle = ExtensionBundle(path)
    assert bundle.name == "dummy"
    assert bundle.developer == "TypeMyType"
    assert bundle.developerURL == "http://typemytype.com"
    assert bundle.version == "1.0"


def test_expireDate(tmpdir):
    path = os.path.join(tmpdir, "test.roboFontExt")
    bundle = ExtensionBundle()
    bundle.name = "dummy"
    bundle.developer = "TypeMyType"
    bundle.developerURL = "http://typemytype.com"
    bundle.version = "1.0"
    bundle.addToMenu = []

    assert bundle.save(path, libPath=tmpdir)
    assert not bundle.validationErrors()

    bundle.expireDate = "2019-01-01"
    assert bundle.save(path, libPath=tmpdir)

    hashPath = os.path.join(bundle.bundlePath(), ".hash")
    assert os.path.exists(hashPath)


def test_hash(tmpdir):
    path = os.path.join(tmpdir, "test.roboFontExt")
    bundle = ExtensionBundle()
    bundle.name = "dummy"
    bundle.developer = "TypeMyType"
    bundle.developerURL = "http://typemytype.com"
    bundle.version = "1.0"
    bundle.addToMenu = []

    bundle.icon = AppKit.NSImage.alloc().initWithSize_((10, 10))
    bundle.expireDate = "3000-01-01"

    # add ignored files
    os.mkdir(os.path.join(tmpdir, "subModule"))

    open(os.path.join(tmpdir, ".DS_Store"), "w").close()
    open(os.path.join(tmpdir, f"Icon{chr(0x0D)}"), "w").close()
    open(os.path.join(tmpdir, "subModule", ".DS_Store"), "w").close()

    assert sorted(os.listdir(tmpdir)) == sorted([".DS_Store", "subModule", f"Icon{chr(0x0D)}"])

    assert bundle.save(path, libPath=tmpdir)
    assert not bundle.validationErrors()

    hashPath = os.path.join(bundle.bundlePath(), ".hash")
    assert os.path.exists(hashPath)

    with open(hashPath, "r") as f:
        extenstionHash = f.read()
    assert extenstionHash == bundle.extensionHash("roboFont.extension.hash")

    succes, message = bundle._installHelper()
    assert succes

    # add a file
    addedPath = os.path.join(path, "lib", "fileAdded.py")
    open(addedPath, "w").close()
    with StdOutCollector() as out:
        succes, message = bundle._installHelper()
    assert not succes
    assert message == "Not a valid extension (test.roboFontExt)"
    assert out.lines() == ['Hash does not match.']
    # restore added file
    os.remove(addedPath)
    succes, message = bundle._installHelper()
    assert succes

    # remove .hash
    hashPath = os.path.join(path, ".hash")
    os.remove(hashPath)
    with StdOutCollector() as out:
        succes, message = bundle._installHelper()
    assert not succes
    assert message == "Not a valid extension (test.roboFontExt)"
    assert out.lines() == ['Missing hash.']
    # restore removed hash
    with open(hashPath, "w") as f:
        f.write(extenstionHash)

    # missing expire date
    bundle.expireDate = None
    with StdOutCollector() as out:
        succes, message = bundle._installHelper()
    assert not succes
    assert message == "Not a valid extension (test.roboFontExt)"
    assert out.lines() == ['Missing expireDate.']
    # restore expire date
    bundle.expireDate = "2022-01-01"

    # expire date expired
    bundle.expireDate = "2015-01-01"
    with StdOutCollector() as out:
        succes, message = bundle._installHelper()
    assert not succes
    assert message == "Extension is expired (test.roboFontExt)"
    assert out.lines() == ['Extension is expired.']


if __name__ == '__main__':
    import pytest
    pytest.main([__file__])
