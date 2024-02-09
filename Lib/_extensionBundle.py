import datetime
import hashlib
import inspect
import os
import plistlib
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import markdown
from markdown.extensions.codehilite import \
    CodeHiliteExtension as markdownCodeHiliteExtension
from markdown.extensions.fenced_code import \
    FencedCodeExtension as markdownFencedCodeExtension
from markdown.extensions.tables import TableExtension as markdownTableExtension
from markdown.extensions.toc import TocExtension as markdownTocExtension
from packaging import version
from typing_extensions import Self

"""
Agenda:
- rf-extension-boilerplate
    - remove extension from git
    - build.py should be github action
    - built extension should go into releases
- we need a command line interface once it's pip installed, github action should use it
    $ roboFontExtension ... (validation or building)

Notes:
- public bundle should validate an existing bundle and create new ones from scratch
- robofont should subclass the public object to do all the specific operations for the app
- the public one should only support a full path to load an existing bundle
- pycOnly should be gone, the flag can be there with a warning but the code should be gone

10/01/2024
- all the icon stuff can go to RF subclass

Completed:
- separate public from private in two separate modules
- expireDate should be a RF specific thing
- move test_extensionBundle into here from RF app, based on a dummy.roboFontExtension
- public bundle could validate the .py syntax
- pure python package, should run on linux machine
- switch to plist pip package instead of a NSDictionary
- there's a public extension from Gustavo that I can use to test

"""

@dataclass
class ExtensionBundle:

    """
    An object to read, write and install extensions.

    **Extension Bundle Specification, version 4**

    ```text
    .roboFontExt

        lib                                 folder name
        html                                folder name    (not required, unless html is True in the info.plist, must contain index.html or index.md, optionally style.css)
        resources                           folder name    (not required)
        info.plist                          plist xml
            {
            name                            str
            developer                       str
            developerURL                    str
            html                            bool           (not required, if True html folder is required)
            documentationURL                str            (not required, if provided it must start with 'http(s)://' v4)
            launchAtStartUp                 bool
            mainScript                      str
            uninstallScript                 str            (not required, v2)
            addToMenu                       list of dicts
                [
                    * {
                    path                    str
                    preferredName           str
                    shortKey                str or tuple
                    nestInSubmenus          bool           (not required, v2)
                    }
                ]
            timeStamp                       float
            version                         str
            requiresVersionMajor            str            (not required)
            requiresVersionMinor            str            (not required)
            expireDate                      str            (not required, if set use the format YYYY-MM-DD)
            }
        license                             txt / html     (not required)
        requirements.txt                    txt            (not required)
    ```
    """

    # just the name of the extension
    name: Union[str, None] = None

    # path has higher priority than a name
    path: Union[Path, None] = None

    libName: str = "lib"
    htmlName: str = "html"
    resourcesName: str ="resources"

    indexHTMLName = "index.html"
    fileExtension = ".roboFontExt"

    def __post_init__(self):
        self._infoDictCache = None
        self._resourcesNamesMapCache = None

        self._libName = self.libName
        self._resourcesName = self.resourcesName
        self._infoName = "info.plist"
        self._licenseName = "license"
        self._license = None
        self._requirementsName = "requirements.txt"
        self._requirements = None
        self._HTMLName = self.htmlName
        self._indexHTMLName = self.indexHTMLName
        self._icon = None

        self._validationErrors = []

        # TODO RF specific
        # maybe the load bundle method should take care of it
        # load the path or name
        
        self._bundlePath = self.path

        if self.path is not None:
            # check specific python versions and swap the lib path
            currentPythonLibName = (
                f"{self.libName}.{sys.version_info.major}.{sys.version_info.minor}"
            )
            currentPythonLibPath = os.path.join(self.path, currentPythonLibName)
            if os.path.exists(currentPythonLibPath):
                self._libName = currentPythonLibName

    @classmethod
    def readBundle(cls, name=None, path=None):
        if name is not None and path is None:
            if not name.lower().endswith(cls.fileExtension.lower()):
                name += cls.fileExtension
            path = os.path.join(applicationPluginRootPath, name)

        if path is not None:
            path = os.path.realpath(path)
        return cls(path=path)

    @classmethod
    def currentBundle(cls, filePath=None) -> Self:
        """
        Return the current bundle.

        Optionally provide a `filePath` inside the host extension bundle.
        """
        if filePath is None:
            frame = inspect.currentframe().f_back
            filePath = os.path.abspath(inspect.getfile(frame))

        if filePath is not None and ".robofontext" in filePath.lower():
            pathElements = filePath.split(os.path.sep)
            while pathElements:
                pathElement = pathElements.pop()
                _, ext = os.path.splitext(pathElement)
                if ext.lower() == ".robofontext":
                    pathElements.append(pathElement)
                    break
            if pathElements:
                path = os.path.sep.join(pathElements)
                return ExtensionBundle(path=path)
        return None

    def __repr__(self) -> str:
        if self._bundlePath is None:
            name = "None"
        else:
            name = self.fileName()
        return "<ExtensionBundle: %s>" % name

    def bundleExists(self) -> bool:
        """
        Returns a bool indicating if the extension bundle exists.
        """
        return os.path.exists(self.bundlePath())

    def save(
        self,
        path,
        libPath,
        htmlPath=None,
        resourcesPath=None,
    ):
        """
        Save the extension to a path, with a given `libPath`.
        Optionally a `htmlPath`, `resourcesPath` can be provided.

        """
        self.timeStamp = time.time()

        infoDict = NSDictionary.dictionaryWithDictionary_(self.infoDictionary)

        tempDir = tempfile.mkdtemp()
        self._bundlePath = tempDir

        infoDict.writeToFile_atomically_(self.infoDictionaryPath(), True)

        shutil.copytree(libPath, self.libPath())

        if htmlPath:
            shutil.copytree(htmlPath, self.HTMLPath())
            self.convertMarkdown()

        if resourcesPath:
            shutil.copytree(resourcesPath, self.resourcesPath())

        if self.license:
            # found license
            # try to write it into the ext bundle
            lf = open(self.licensePath(), "w")
            try:
                lf.write(self.license)
            except Exception:
                import traceback

                print("Writing license file %s failed:" % self.name)
                print(traceback.format_exc(5))
                print("*" * 20)
            lf.close()
        elif os.path.exists(self.licensePath()):
            # no license found
            # but there is a file --> remove it
            os.remove(self.licensePath())

        if self.requirements:
            # found requirements
            # try to write it into the ext bundle
            rf = open(self.requirementsPath(), "w")
            try:
                rf.write(self.requirements)
            except Exception:
                import traceback

                print("Writing requirements file %s failed:" % self.name)
                print(traceback.format_exc(5))
                print("*" * 20)
            rf.close()
        elif os.path.exists(self.requirementsPath()):
            # no requirements found
            # but there is a file --> remove it
            os.remove(self.requirementsPath())

        if os.path.exists(path):
            shutil.rmtree(path)

        shutil.copytree(tempDir, path)
        shutil.rmtree(tempDir)

        if isinstance(self.icon, NSImage):
            workspace = NSWorkspace.sharedWorkspace()
            workspace.setIcon_forFile_options_(self.icon, path, 0)

        self._bundlePath = path
        if self.expireDate:
            # write a .hash file if expireDate key is present
            hashPath = os.path.join(self.bundlePath(), ".hash")
            hashData = self.extensionHash("roboFont.extension.hash")
            with open(hashPath, "w") as f:
                f.write(hashData)
        return self.validate()

    # =========
    # = paths =
    # =========

    def bundlePath(self) -> Path:
        """
        Get the path of the extension bundle.
        """
        return self._bundlePath

    def fileName(self) -> str:
        """
        Get the file name of the extension bundle.
        """
        return os.path.basename(self.bundlePath())

    def libPath(self) -> Path:
        """
        Get the path to the lib folder.
        """
        return os.path.join(self.bundlePath(), self._libName)

    def HTMLPath(self) -> Path:
        """
        Get the path to the HTML folder.
        """
        return os.path.join(self.bundlePath(), self._HTMLName)

    def resourcesPath(self) -> Path:
        """
        Get the path to the resources folder.
        """
        return os.path.join(self.bundlePath(), self._resourcesName)

    def infoDictionaryPath(self) -> Path:
        """
        Get the path of the `info.plist` file.
        """
        return os.path.join(self.bundlePath(), self._infoName)

    def licensePath(self) -> Path:
        """
        Get the path of license file.
        """
        return os.path.join(self.bundlePath(), self._licenseName)

    def requirementsPath(self) -> Path:
        """
        Get the path of the requirements file.
        """
        return os.path.join(self.bundlePath(), self._requirementsName)

    # ===================
    # = info attributes =
    # ===================

    def _get_infoDictionary(self):
        if self._infoDictCache is None:
            if self.bundlePath() and os.path.exists(self.infoDictionaryPath()):
                try:
                    with open(self.infoDictionaryPath(), "rb") as f:
                        self._infoDictCache = plistlib.load(f)
                except Exception:
                    self._infoDictCache = dict()
            else:
                self._infoDictCache = dict()
        return self._infoDictCache

    infoDictionary = property(
        _get_infoDictionary, doc="Returns the `info.plist` as a dictionary."
    )

    def setInfo(self, key, value):
        """
        Set info with a `key` and `value`.
        """
        self.infoDictionary[key] = value

    def getInfo(self, key, fallback=None):
        """
        Get info with a `key`.

        Optionally a `fallback` value can be provided.
        """
        return self.infoDictionary.get(key, fallback)

    def _get_name(self):
        return self.infoDictionary.get("name")

    def _set_name(self, value):
        self.infoDictionary["name"] = value

    name = property(_get_name, _set_name, doc="Get and set the name of the extension.")

    def _get_developer(self):
        return self.infoDictionary.get("developer")

    def _set_developer(self, value):
        self.infoDictionary["developer"] = value

    developer = property(
        _get_developer,
        _set_developer,
        doc="Get and set the name of the extension developer.",
    )

    def _get_developerURL(self):
        return self.infoDictionary.get("developerURL")

    def _set_developerURL(self, value):
        self.infoDictionary["developerURL"] = value

    developerURL = property(
        _get_developerURL, _set_developerURL, doc="Get and set the developer URL."
    )

    def _get_version(self):
        return self.infoDictionary.get("version")

    def _set_version(self, value):
        self.infoDictionary["version"] = value

    version = property(
        _get_version, _set_version, doc="Get and set the extension version."
    )

    def _get_timeStamp(self):
        return self.infoDictionary.get("timeStamp")

    def _set_timeStamp(self, value):
        self.infoDictionary["timeStamp"] = value

    timeStamp = property(
        _get_timeStamp, _set_timeStamp, doc="Get and set the extension time stamp."
    )

    def _get_requiresVersionMajor(self):
        return self.infoDictionary.get("requiresVersionMajor")

    def _set_requiresVersionMajor(self, value):
        if value is None:
            if "requiresVersionMajor" in self.infoDictionary:
                del self.infoDictionary["requiresVersionMajor"]
        else:
            self.infoDictionary["requiresVersionMajor"] = value

    requiresVersionMajor = property(
        _get_requiresVersionMajor,
        _set_requiresVersionMajor,
        doc="Get and set the minor required RoboFont version.",
    )

    def _get_requiresVersionMinor(self):
        return self.infoDictionary.get("requiresVersionMinor")

    def _set_requiresVersionMinor(self, value):
        if value is None:
            if "requiresVersionMinor" in self.infoDictionary:
                del self.infoDictionary["requiresVersionMinor"]
        else:
            self.infoDictionary["requiresVersionMinor"] = value

    requiresVersionMinor = property(
        _get_requiresVersionMinor,
        _set_requiresVersionMinor,
        doc="Get and set the major required RoboFont version.",
    )

    def _get_addToMenu(self):
        return self.infoDictionary.get("addToMenu", [])

    def _set_addToMenu(self, value):
        self.infoDictionary["addToMenu"] = value

    addToMenu = property(
        _get_addToMenu,
        _set_addToMenu,
        doc="Get and set scripts to be added to the extension menu.",
    )

    def addScriptToMenu(self, path, preferredName, shortKey=""):
        """
        Add a script to the extension menu.

        - `path` : path to a Python file
        - `preferredName` : name to be displayed in the menu
        - `shortKey` : shortcut key to access the menu item (optional)
        """
        menu = self.addToMenu
        menu.append(dict(path=path, preferredName=preferredName, shortKey=shortKey))
        self.addToMenu = menu

    def menuScriptPaths(self):
        """
        Returns the scripts which are set in the extension menu.
        """
        return [os.path.join(self.libPath(), menu["path"]) for menu in self.addToMenu]

    def _get_launchAtStartUp(self):
        return self.infoDictionary.get("launchAtStartUp")

    def _set_launchAtStartUp(self, value):
        self.infoDictionary["launchAtStartUp"] = value

    launchAtStartUp = property(
        _get_launchAtStartUp,
        _set_launchAtStartUp,
        doc="Get and set a script to be launched when RoboFont starts up.",
    )

    def _get_mainScript(self):
        return self.infoDictionary.get("mainScript")

    def _set_mainScript(self, value):
        self.infoDictionary["mainScript"] = value

    mainScript = property(
        _get_mainScript, _set_mainScript, doc="Get and set the main script."
    )

    def mainScriptPath(self):
        """
        Get the path of the main script.
        """
        return os.path.join(self._bundlePath, self._libName, self.mainScript)

    def _get_uninstallScript(self):
        return self.infoDictionary.get("uninstallScript")

    def _set_uninstallScript(self, value):
        if value is None:
            if "uninstallScript" in self.infoDictionary:
                del self.infoDictionary["uninstallScript"]
        else:
            self.infoDictionary["uninstallScript"] = value

    uninstallScript = property(
        _get_uninstallScript,
        _set_uninstallScript,
        doc="Get and set the uninstall script.",
    )

    def uninstallScriptPath(self):
        """
        Get the path to the script that uninstalls the extension.
        """
        return os.path.join(self._bundlePath, self._libName, self.uninstallScript)

    def _get_html(self):
        return self.infoDictionary.get("html", False)

    def _set_html(self, value):
        self.infoDictionary["html"] = value

    html = property(
        _get_html,
        _set_html,
        doc="Get and set a bool indicating if the extension has HTML help.",
    )

    def hasHTML(self):
        """
        Returns a bool indicating if the extension has HTML help.
        """
        return bool(self.infoDictionary.get("html", False))

    def hasDocumentation(self):
        """
        Returns a bool indicating if the extension has HTML help or a documentionURL.
        """
        return os.path.exists(self.HTMLIndexPath()) or bool(self.documentationURL)

    def HTMLIndexPath(self):
        """
        Get the path to the `index.html` HTML help file.
        """
        return os.path.join(self._bundlePath, self._HTMLName, self._indexHTMLName)

    def _get_documentationURL(self):
        return self.infoDictionary.get("documentationURL", None)

    def _set_documentationURL(self, value):
        self.infoDictionary["documentationURL"] = value

    documentationURL = property(
        _get_documentationURL,
        _set_documentationURL,
        doc="An external link to the documentation.",
    )

    def _get_expireDate(self):
        return self.infoDictionary.get("expireDate", None)

    def _set_expireDate(self, value):
        self.infoDictionary["expireDate"] = value

    expireDate = property(
        _get_expireDate,
        _set_expireDate,
        doc="Get and set the extension expiration date.",
    )

    expireDateFormat = "%Y-%m-%d"

    # =============
    # = resources =
    # =============

    def _get_resourcesNamesMap(self):
        if self._resourcesNamesMapCache is None:
            self._resourcesNamesMapCache = dict()
            paths = walkDirectoryForFile(self.resourcesPath(), "*")
            for path in paths:
                fileName = os.path.basename(path)
                name, ext = os.path.splitext(fileName)
                if ext and ext[0] == ".":
                    ext = ext[1:]
                self._resourcesNamesMapCache[(name, "*")] = path
                self._resourcesNamesMapCache[(name, ext)] = path
        return self._resourcesNamesMapCache

    resourcesNamesMap = property(
        _get_resourcesNamesMap,
        doc="Get a dictionary mapping resources file names to paths.",
    )

    def get(self, name, ext="*"):
        """
        Get a resources by `name`.

        Optionally an `ext` can be provided.
        """
        image = self.getResourceImage(name, ext)
        if isinstance(image, NSImage) and image.isValid():
            return image
        return self.getResourceFilePath(name, ext)

    def getResourceImage(self, imageName, ext="*"):
        """
        Get an image resource by `imageName`.

        Optionally an extension `ext` can be provided.
        """
        path = self.resourcesNamesMap.get((imageName, ext))
        return NSImage.alloc().initByReferencingFile_(path)

    def getResourceFilePath(self, name, ext="*"):
        """
        Get the path to a resource file by `name`.

        Optionally an extension `ext` can be provided.
        """
        return self.resourcesNamesMap.get((name, ext))

    def _get_icon(self):
        return self._icon

    def _set_icon(self, pathOrImage):
        if isinstance(pathOrImage, str) and os.path.exists(pathOrImage):
            pathOrImage = NSImage.alloc().initWithContentsOfFile_(pathOrImage)
        self._icon = pathOrImage

    icon = property(_get_icon, _set_icon, doc="Get and set the extension icon.")

    # ===========
    # = license =
    # ===========

    def _get_license(self):
        if self._license is None and os.path.exists(self.licensePath()):
            lf = open(self.licensePath(), "r")
            self._license = lf.read()
            lf.close()
        return self._license

    def _set_license(self, value):
        self._license = value

    license = property(
        _get_license, _set_license, doc="Get and set the license for the extension."
    )

    # ================
    # = requirements =
    # ================

    def _get_requirements(self):
        if self._requirements is None and os.path.exists(self.requirementsPath()):
            rf = open(self.requirementsPath(), "r")
            self._requirements = rf.read()
            rf.close()
        return self._requirements

    def _set_requirements(self, txt):
        self._requirements = txt

    requirements = property(
        _get_requirements,
        _set_requirements,
        doc="Get and set the requirements (dependencies) for the bundle.",
    )

    @classmethod
    def _requirementCompareVersionMustBeEqual(cls, v1, v2):
        return version.Version(v1) == version.Version(v2)

    @classmethod
    def _requirementCompareVersionCompareEqualOrBigger(cls, v1, v2):
        return version.Version(v1) >= version.Version(v2)

    def iterParseRequirements(self, requirements):
        requirementMustMatch = "=="
        requirementMinVersion = ">="

        done = set()
        for requirementKey in requirements.split("\n"):
            requirementKey = requirementKey.strip()
            if not requirementKey:
                continue
            if requirementKey.startswith("#"):
                continue
            requirementKey = line = requirementKey.split("#")[0]

            version = None
            if requirementMustMatch in requirementKey:
                requirementKey, versionKey = requirementKey.split(requirementMustMatch)
                version = (
                    self._requirementCompareVersionMustBeEqual,
                    versionKey.strip(),
                    line.strip(),
                )
            elif requirementMinVersion in requirementKey:
                requirementKey, versionKey = requirementKey.split(requirementMinVersion)
                version = (
                    self._requirementCompareVersionCompareEqualOrBigger,
                    versionKey.strip(),
                    line.strip(),
                )

            requirementKey = requirementKey.strip()
            if requirementKey in done:
                continue
            key = requirementKey
            done.add(key)
            yield key, version

    def resolveRequirements(self):
        requirements = self.requirements
        required = set()
        if not requirements:
            return required
        for requirement, version in self.iterParseRequirements(requirements):
            bundle = self.__class__(requirement)
            if not bundle.bundleExists():
                required.add(requirement)
            if version:
                compare, versionNumber, line = version
                if not compare(versionNumber, bundle.version):
                    required.add(line)
        return required

    def loadRequirements(self, done):
        """
        Load the extension requirements (dependencies) from the requirements file.
        """
        requirements = self.requirements
        if not requirements:
            return
        for requirement, version in self.iterParseRequirements(requirements):
            if requirement in done:
                continue
            bundle = self.__class__(requirement)
            self._loadBundle(bundle, done)
            done.append(bundle.fileName())

    # ============
    # = validate =
    # ============

    def validate(self):
        """
        Validate the extension according to the [Extension File Specification].

        [Extension File Specification]: http://robofont.com/documentation/building-tools/extensions/extension-file-spec/
        """
        self._validationErrors = []
        if self.bundlePath() is None:
            self._validationErrors.append(
                "Extension bundle must be saved on disk before it can be validated."
            )
        else:
            self.validateInfo()
            self.validateLib()
            self.validateHTML()
            self.validateResources()
            self.validateLicense()
            self.validateRequirements()
        return not bool(self._validationErrors)

    def validationErrors(self):
        """
        Returns the validation errors as a string.
        """
        return "\n".join(self._validationErrors)

    def _validateDict(
        self, obj, requiredKeys, additionalKeys=dict(), endsWithDotPy=[], niceName=""
    ):
        def strifyTuple(v):
            if isinstance(valueType, tuple):
                return ", ".join(["%s" % i.__name__ for i in v])
            else:
                return "%s" % (v.__name__)

        for requiredKey, valueType in requiredKeys.items():
            value = obj.get(requiredKey)
            if value is None:
                self._validationErrors.append(
                    "%s is a required %s key" % (requiredKey, niceName)
                )
                continue

            if not isinstance(value, valueType):
                niceType = strifyTuple(valueType)
                self._validationErrors.append(
                    "the value of %s is wrong (%s), should be %s."
                    % (requiredKey, type(value).__name__, niceType)
                )
                continue

            if requiredKey in endsWithDotPy:
                if not value.endswith(".py"):
                    self._validationErrors.append(
                        "%s '%s' should be a relative path to a *.py file."
                        % (requiredKey, value)
                    )

        for additionalKey, valueType in additionalKeys.items():
            value = obj.get(additionalKey)
            if value is not None and not isinstance(value, valueType):
                niceType = strifyTuple(valueType)
                self._validationErrors.append(
                    "the value of %s is wrong (%s), should be %s."
                    % (requiredKey, type(value).__name__, niceType)
                )

    def validateInfo(self):
        """
        Validate the `info.plist` file.
        """
        if not os.path.exists(self.infoDictionaryPath()):
            self._validationErrors.append(
                "info.plist does not exist, this is required."
            )
            return

        try:
            with open(self.infoDictionaryPath(), "rb") as f:
                info = plistlib.load(f)
        except Exception:
            self._validationErrors.append(
                "info.plist is not formatted as a *.plist file and unreadable."
            )
            return

        requiredKeys = {
            "addToMenu": list,
            "developer": str,
            "developerURL": str,
            "name": str,
            "timeStamp": (float, int),
            "version": str,
        }
        additionalKeys = {
            "html": (bool, int),
            "validateDocumentationURL": str,
            "launchAtStartUp": (bool, int),
            "mainScript": str,
            "requiresVersionMajor": str,
            "requiresVersionMinor": str,
            "uninstallScript": str,
        }

        endsWithDotPy = ["path"]

        self._validateDict(
            info,
            requiredKeys,
            additionalKeys=additionalKeys,
            endsWithDotPy=endsWithDotPy,
            niceName="info.plist",
        )

        if self.launchAtStartUp:
            mainScript = self.mainScript
            if mainScript is None:
                self._validationErrors.append(
                    "mainscript can not be None when a script is required on start up."
                )
            else:
                if not mainScript.endswith(".py"):
                    self._validationErrors.append(
                        "mainScript '%s' should be a relative path to a *.py file."
                        % (mainScript)
                    )

                mainScriptPath = self.mainScriptPath()
                if not os.path.exists(mainScriptPath):
                    self._validationErrors.append(
                        "mainScript '%s' does not exists in '%s/%s'."
                        % (mainScript, self.fileName(), self._libName)
                    )

        uninstallScript = self.uninstallScript
        if uninstallScript:
            if not uninstallScript.endswith(".py"):
                self._validationErrors.append(
                    "uninstallScript '%s' should be a relative path to a *.py file."
                    % (uninstallScript)
                )
            uninstallScriptPath = self.uninstallScriptPath()
            if not os.path.exists(uninstallScriptPath):
                self._validationErrors.append(
                    "uninstallScript '%s' does not exists in '%s/%s'."
                    % (uninstallScript, self.fileName(), self._libName)
                )

        addToMenu = self.addToMenu
        requiredMenuKeys = {
            "path": str,
            "preferredName": str,
            "shortKey": (str, tuple, list),
        }
        additionalKeys = {"nestInSubmenus": (bool, int)}

        for menuItem in addToMenu:
            self._validateDict(
                menuItem,
                requiredMenuKeys,
                additionalKeys=additionalKeys,
                endsWithDotPy=endsWithDotPy,
                niceName="addToMenu item",
            )
            shortKey = menuItem.get("shortKey")
            if shortKey is not None:
                if isinstance(shortKey, (tuple, list)):
                    modifier, shortKey = shortKey
                    if not isinstance(modifier, int):
                        self._validationErrors.append(
                            "Shortkey is formatted wrongly, modifier must a be an int '(modifier, character)'."
                        )
                    if not isinstance(shortKey, str):
                        self._validationErrors.append(
                            "Shortkey is formatted wrongly, character must a be a str '(modifier, character)'"
                        )
            menuItemPathString = menuItem.get("path")
            if menuItemPathString is not None:
                menuItemPath = os.path.join(self.libPath(), menuItemPathString)
                if not os.path.exists(menuItemPath):
                    self._validationErrors.append(
                        "path key in menu item does not exist (%s), this is required."
                        % menuItemPath
                    )

        if self.expireDate:
            try:
                datetime.datetime.strptime(self.expireDate, self.expireDateFormat)
            except Exception:
                self._validationErrors.append(
                    "expire date is not set in the correct format: 'YYYY-MM-DD'. "
                )

    def validateLib(self):
        """
        Validate the lib where all Python files are stored.
        """
        if not os.path.exists(self.libPath()):
            self._validationErrors.append(
                "'%s' does not exist in '%s', this is required."
                % (self._libName, self.fileName())
            )
            return

    def validateHTML(self):
        """
        Validate the HTML files if present.
        """
        if not self.hasHTML():
            return

        if not os.path.exists(self.HTMLPath()):
            self._validationErrors.append(
                "'%s' does not exist in '%s', this is required."
                % (self._HTMLName, self.fileName())
            )
            return

        if not os.path.exists(self.HTMLIndexPath()):
            self._validationErrors.append(
                "'%s' does not exist in '%s', this is required."
                % (self._indexHTMLName, self._HTMLName)
            )
            return

    def validateResources(self):
        """
        Validate all resources.
        """
        pass

    def validateLicense(self):
        """
        Validate the license text or HTML.
        """
        pass

    def validateRequirements(self):
        """
        Validate the requirements text.
        """
        pass

    # ========
    # = hash =
    # ========

    def extensionHash(self, passphrase="") -> str:
        path = self.bundlePath()
        digest = hashlib.sha1()
        # add private key
        digest.update(passphrase.encode("utf-8"))
        pathToDigest = []
        for root, dirs, files in os.walk(path):
            for name in files:
                # ignore
                if name in [f"Icon{chr(0x0D)}", ".hash"]:
                    continue
                elif name.endswith(".DS_Store"):
                    continue
                filePath = os.path.join(root, name)
                pathToDigest.append(filePath)
        for filePath in sorted(pathToDigest):
            digest.update(hashlib.sha1(filePath[len(path) :].encode()).digest())
            if os.path.isfile(filePath):
                with open(filePath, "rb") as f:
                    while True:
                        buf = f.read(1024 * 1024)
                        if not buf:
                            break
                        digest.update(buf)
        return digest.hexdigest()

    # ========
    # = docs =
    # ========

    def convertMarkdown(self):
        """
        Convert documentation sources from Markdown to HTML.
        """

        # github-like css from https://github.com/sindresorhus/github-markdown-css
        styleData = """<style>
            @font-face{font-family:octicons-link;src:url(data:font/woff;charset=utf-8;base64,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) format('woff')}
            html{max-width:800px;padding:15px;margin-left:auto;margin-right:auto;}body{-ms-text-size-adjust:100%;-webkit-text-size-adjust:100%;line-height:1.5;color:#333;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif,"Apple Color Emoji","Segoe UI Emoji","Segoe UI Symbol";font-size:16px;line-height:1.5;word-wrap:break-word}body .pl-c{color:#969896}body .pl-c1,body .pl-s .pl-v{color:#0086b3}body .pl-e,body .pl-en{color:#795da3}body .pl-s .pl-s1,body .pl-smi{color:#333}body .pl-ent{color:#63a35c}body .pl-k{color:#a71d5d}body .pl-pds,body .pl-s,body .pl-s .pl-pse .pl-s1,body .pl-sr,body .pl-sr .pl-cce,body .pl-sr .pl-sra,body .pl-sr .pl-sre{color:#183691}body .pl-v{color:#ed6a43}body .pl-id{color:#b52a1d}body .pl-ii{color:#f8f8f8;background-color:#b52a1d}body .pl-sr .pl-cce{font-weight:700;color:#63a35c}body .pl-ml{color:#693a17}body .pl-mh,body .pl-mh .pl-en,body .pl-ms{font-weight:700;color:#1d3e81}body .pl-mq{color:teal}body .pl-mi{font-style:italic;color:#333}body .pl-mb{font-weight:700;color:#333}body .pl-md{color:#bd2c00;background-color:#ffecec}body .pl-mi1{color:#55a532;background-color:#eaffea}body .pl-mdr{font-weight:700;color:#795da3}body .pl-mo{color:#1d3e81}body .octicon{display:inline-block;vertical-align:text-top;fill:currentColor}body a{background-color:transparent;-webkit-text-decoration-skip:objects}body a:active,body a:hover{outline-width:0}body strong{font-weight:inherit}body strong{font-weight:bolder}body h1{font-size:2em;margin:.67em 0}body img{border-style:none}body svg:not(:root){overflow:hidden}body code,body kbd,body pre{font-family:monospace,monospace;font-size:1em}body hr{box-sizing:content-box;height:0;overflow:visible}body input{font:inherit;margin:0}body input{overflow:visible}body [type=checkbox]{box-sizing:border-box;padding:0}body *{box-sizing:border-box}body input{font-family:inherit;font-size:inherit;line-height:inherit}body a{color:#4078c0;text-decoration:none}body a:active,body a:hover{text-decoration:underline}body strong{font-weight:600}body hr{height:0;margin:15px 0;overflow:hidden;background:0 0;border:0;border-bottom:1px solid #ddd}body hr::before{display:table;content:""}body hr::after{display:table;clear:both;content:""}body table{border-spacing:0;border-collapse:collapse}body td,body th{padding:0}body h1,body h2,body h3,body h4,body h5,body h6{margin-top:0;margin-bottom:0}body h1{font-size:32px;font-weight:600}body h2{font-size:24px;font-weight:600}body h3{font-size:20px;font-weight:600}body h4{font-size:16px;font-weight:600}body h5{font-size:14px;font-weight:600}body h6{font-size:12px;font-weight:600}body p{margin-top:0;margin-bottom:10px}body blockquote{margin:0}body ol,body ul{padding-left:0;margin-top:0;margin-bottom:0}body ol ol,body ul ol{list-style-type:lower-roman}body ol ol ol,body ol ul ol,body ul ol ol,body ul ul ol{list-style-type:lower-alpha}body dd{margin-left:0}body code{font-family:Consolas,"Liberation Mono",Menlo,Courier,monospace;font-size:12px}body pre{margin-top:0;margin-bottom:0;font:12px Consolas,"Liberation Mono",Menlo,Courier,monospace}body .octicon{vertical-align:text-bottom}body input{-webkit-font-feature-settings:"liga" 0;font-feature-settings:"liga" 0}body::before{display:table;content:""}body::after{display:table;clear:both;content:""}body>:first-child{margin-top:0!important}body>:last-child{margin-bottom:0!important}body a:not([href]){color:inherit;text-decoration:none}body .anchor{float:left;padding-right:4px;margin-left:-20px;line-height:1}body .anchor:focus{outline:0}body blockquote,body dl,body ol,body p,body pre,body table,body ul{margin-top:0;margin-bottom:16px}body hr{height:.25em;padding:0;margin:24px 0;background-color:#e7e7e7;border:0}body blockquote{padding:0 1em;color:#777;border-left:.25em solid #ddd}body blockquote>:first-child{margin-top:0}body blockquote>:last-child{margin-bottom:0}body kbd{display:inline-block;padding:3px 5px;font-size:11px;line-height:10px;color:#555;vertical-align:middle;background-color:#fcfcfc;border:solid 1px #ccc;border-bottom-color:#bbb;border-radius:3px;box-shadow:inset 0 -1px 0 #bbb}body h1,body h2,body h3,body h4,body h5,body h6{margin-top:24px;margin-bottom:16px;font-weight:600;line-height:1.25}body h1 .octicon-link,body h2 .octicon-link,body h3 .octicon-link,body h4 .octicon-link,body h5 .octicon-link,body h6 .octicon-link{color:#000;vertical-align:middle;visibility:hidden}body h1:hover .anchor,body h2:hover .anchor,body h3:hover .anchor,body h4:hover .anchor,body h5:hover .anchor,body h6:hover .anchor{text-decoration:none}body h1:hover .anchor .octicon-link,body h2:hover .anchor .octicon-link,body h3:hover .anchor .octicon-link,body h4:hover .anchor .octicon-link,body h5:hover .anchor .octicon-link,body h6:hover .anchor .octicon-link{visibility:visible}body h1{padding-bottom:.3em;font-size:2em;border-bottom:1px solid #eee}body h2{padding-bottom:.3em;font-size:1.5em;border-bottom:1px solid #eee}body h3{font-size:1.25em}body h4{font-size:1em}body h5{font-size:.875em}body h6{font-size:.85em;color:#777}body ol,body ul{padding-left:2em}body ol ol,body ol ul,body ul ol,body ul ul{margin-top:0;margin-bottom:0}body li>p{margin-top:16px}body li+li{margin-top:.25em}body dl{padding:0}body dl dt{padding:0;margin-top:16px;font-size:1em;font-style:italic;font-weight:700}body dl dd{padding:0 16px;margin-bottom:16px}body table{display:block;width:100%;overflow:auto}body table th{font-weight:700}body table td,body table th{padding:6px 13px;border:1px solid #ddd}body table tr{background-color:#fff;border-top:1px solid #ccc}body table tr:nth-child(2n){background-color:#f8f8f8}body img{max-width:100%;box-sizing:content-box;background-color:#fff}body code{padding:0;padding-top:.2em;padding-bottom:.2em;margin:0;font-size:85%;background-color:rgba(0,0,0,.04);border-radius:3px}body code::after,body code::before{letter-spacing:-.2em;content:"\u00a0"}body pre{word-wrap:normal}body pre>code{padding:0;margin:0;font-size:100%;word-break:normal;white-space:pre;background:0 0;border:0}body .highlight{margin-bottom:16px}body .highlight pre{margin-bottom:0;word-break:normal}body .highlight pre,body pre{padding:16px;overflow:auto;font-size:85%;line-height:1.45;background-color:#f7f7f7;border-radius:3px}body pre code{display:inline;max-width:auto;padding:0;margin:0;overflow:visible;line-height:inherit;word-wrap:normal;background-color:transparent;border:0}body pre code::after,body pre code::before{content:normal}body .pl-0{padding-left:0!important}body .pl-1{padding-left:3px!important}body .pl-2{padding-left:6px!important}body .pl-3{padding-left:12px!important}body .pl-4{padding-left:24px!important}body .pl-5{padding-left:36px!important}body .pl-6{padding-left:48px!important}body .full-commit .btn-outline:not(:disabled):hover{color:#4078c0;border:1px solid #4078c0}body kbd{display:inline-block;padding:3px 5px;font:11px Consolas,"Liberation Mono",Menlo,Courier,monospace;line-height:10px;color:#555;vertical-align:middle;background-color:#fcfcfc;border:solid 1px #ccc;border-bottom-color:#bbb;border-radius:3px;box-shadow:inset 0 -1px 0 #bbb}body :checked+.radio-label{position:relative;z-index:1;border-color:#4078c0}body .task-list-item{list-style-type:none}body .task-list-item+.task-list-item{margin-top:3px}body .task-list-item input{margin:0 .2em .25em -1.6em;vertical-align:middle}body hr{border-bottom-color:#eee}.codehilite .c{color:#999}.codehilite .err{color:red}.codehilite .g{color:#363636}.codehilite .k{color:#4998ff}.codehilite .l{color:#93a1a1}.codehilite .n{color:#363636}.codehilite .o{color:#aa25ff}.codehilite .x{color:#cb4b16}.codehilite .p{color:#93a1a1}.codehilite .cm{color:#586e75}.codehilite .cp{color:#aa25ff}.codehilite .c1{color:#586e75}.codehilite .cs{color:#aa25ff}.codehilite .gd{color:#2aa198}.codehilite .ge{color:#93a1a1;font-style:italic}.codehilite .gr{color:#dc322f}.codehilite .gh{color:#cb4b16}.codehilite .gi{color:#aa25ff}.codehilite .go{color:#93a1a1}.codehilite .gp{color:#93a1a1}.codehilite .gs{color:#93a1a1;font-weight:700}.codehilite .gu{color:#cb4b16}.codehilite .gt{color:#93a1a1}.codehilite .kc{color:#cb4b16}.codehilite .kd{color:#268bd2}.codehilite .kn{color:#4998ff}.codehilite .kp{color:#aa25ff}.codehilite .kr{color:#268bd2}.codehilite .kt{color:#dc322f}.codehilite .ld{color:#c42f07}.codehilite .m{color:#c42f07}.codehilite .s{color:#ff05da}.codehilite .na{color:#93a1a1}.codehilite .nb{color:#0bd51e}.codehilite .nc{color:#ff3ca8}.codehilite .no{color:#ff3ca8}.codehilite .nd{color:#ff3ca8}.codehilite .ni{color:#ff3ca8}.codehilite .ne{color:#ff3ca8}.codehilite .nf{color:#ff3ca8}.codehilite .nl{color:#ff3ca8}.codehilite .nn{color:#354980}.codehilite .nx{color:#555}.codehilite .py{color:#93a1a1}.codehilite .nt{color:#268bd2}.codehilite .nv{color:#268bd2}.codehilite .ow{color:#aa25ff}.codehilite .w{color:#93a1a1}.codehilite .mf{color:#c42f07}.codehilite .mh{color:#c42f07}.codehilite .mi{color:#c42f07}.codehilite .mo{color:#c42f07}.codehilite .sb{color:#ff05da}.codehilite .sc{color:#ff05da}.codehilite .sd{color:#ff05da}.codehilite .s2{color:#ff05da}.codehilite .se{color:#ff05da}.codehilite .sh{color:#ff05da}.codehilite .si{color:#ff05da}.codehilite .sx{color:#ff05da}.codehilite .sr{color:#ff05da}.codehilite .s1{color:#ff05da}.codehilite .ss{color:#ff05da}.codehilite .bp{color:#f29108}.codehilite .vc{color:#268bd2}.codehilite .vg{color:#268bd2}.codehilite .vi{color:#268bd2}.codehilite .il{color:#c42f07}
        </style>
        """
        cssPath = os.path.join(self.HTMLPath(), "style.css")
        if os.path.exists(cssPath):
            with open(cssPath, "r") as cssFile:
                styleData = f"<style>{cssFile.read()}</style>"
        htmlTemplate = """<html>
        <head>
            <meta charset="UTF-8">
            %s
        </head>
        <body>
        %s
        </body>
        </html>
        """

        for path in walkDirectoryForFile(self.HTMLPath(), ext=".md"):
            with open(path, "r", encoding="utf-8") as f:
                htmlData = markdown.markdown(
                    f.read(),
                    extensions=[
                        markdownTableExtension(),
                        markdownTocExtension(permalink=False, toc_depth="2-3"),
                        markdownFencedCodeExtension(),
                        markdownCodeHiliteExtension(),
                    ],
                )
                destPath = path[:-3] + ".html"

                html = htmlTemplate % (styleData, htmlData)
                with open(destPath, "w", encoding="utf-8") as f:
                    f.write(html)
