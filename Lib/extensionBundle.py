import ast
import hashlib
import plistlib
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from shutil import copytree, rmtree
from urllib.parse import urlparse

import markdown
import yaml
from markdown.extensions.codehilite import \
    CodeHiliteExtension as markdownCodeHiliteExtension
from markdown.extensions.fenced_code import \
    FencedCodeExtension as markdownFencedCodeExtension
from markdown.extensions.tables import TableExtension as markdownTableExtension
from markdown.extensions.toc import TocExtension as markdownTocExtension
from typing_extensions import (Any, NotRequired, Optional, Self, TypedDict,
                               Union)
from yaml.resolver import BaseResolver

"""
Notes:

(outliner on a fork)
- prepare yaml files in the repo that can be used to build the extension
    - info.yaml (should reproduce plist)
    - build.yaml, info necessary to build the extension
- start to work on an existing github action

- test the current state against all mechanic extensions
    - we should have a script to run this from time to time

- work on a script to update an existing extension to this new setup
    --> it should become a method (unwrap/start new) of an instance

"""


class AsLiteral(str):
    pass


def represent_literal(dumper, data):
    data = data.rstrip()
    optimized = []
    for line in data.splitlines():
        line = line.rstrip()
        optimized.append(line)

    optimized.append("")

    return dumper.represent_scalar(
        BaseResolver.DEFAULT_SCALAR_TAG,
        "\n".join(optimized),
        style="|"
    )


yaml.add_representer(AsLiteral, represent_literal)


def isValidURL(url: str) -> bool:
    # from https://stackoverflow.com/a/38020041/1925198
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


class AddToMenuDict(TypedDict):
    path: str
    preferredName: str
    shortKey: Union[str, tuple[int, str]]
    nestInSubmenus: NotRequired[Union[bool, int]]        # v2


@dataclass
class ExtensionBundle:

    extensionName: Optional[str] = None
    developer: Optional[str] = None
    developerURL: Optional[str] = None
    launchAtStartUp: Optional[bool] = None
    mainScript: Optional[str] = None
    version: Optional[str] = None
    addToMenu: list[AddToMenuDict] = field(default_factory=list)

    path: Optional[Path] = None
    html: Optional[bool] = None                # to be deprecated, DOCS
    documentationURL: Optional[str] = None     # if provided it must start with 'http(s)://' v4
    uninstallScript: Optional[str] = None      # v2

    timeStamp: Optional[float] = None
    hash: str = ""

    requiresVersionMajor: Optional[str] = None
    requiresVersionMinor: Optional[str] = None

    expireDate: Optional[str] = None                  # if set use the format YYYY-MM-DD
    license: str = ""
    requirements: str = ""

    # Constants
    indexHTMLName = "index.html"
    fileExtension = ".roboFontExt"
    expireDateFormat = "%Y-%m-%d"
    infoPlistFilename = "info.plist"

    # Private
    _errors: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        if self.extensionName:
            return f"<ExtensionBundle: {self.extensionName}>"
        else:
            name = "None" if not self.bundlePath else self.bundlePath.name
            return f"<ExtensionBundle: {name}>"

    # =========
    # = paths =
    # =========

    @property
    def bundlePath(self) -> Path:
        if not self.path:
            return Path(self.extensionName or "extension")
        return self.path

    @property
    def licensePath(self) -> Path:
        return self.bundlePath / "license"

    @property
    def requirementsPath(self) -> Path:
        return self.bundlePath / "requirements.txt"

    @property
    def libFolder(self) -> Path:
        return self.bundlePath / "lib"

    @property
    def htmlFolder(self) -> Path:
        return self.bundlePath / "html"

    @property
    def hashPath(self) -> Path:
        return self.bundlePath / ".hash"

    @property
    def resourcesFolder(self) -> Path:
        return self.bundlePath / "resources"

    @property
    def infoPlistPath(self) -> Path:
        return self.bundlePath / "info.plist"

    @property
    def hasHTML(self) -> bool:
        return (self.htmlFolder / self.indexHTMLName).exists()

    @property
    def hasDocumentation(self) -> bool:
        return (self.htmlFolder / self.indexHTMLName).exists() or bool(self.documentationURL)

    @property
    def infoDictionary(self) -> dict[str, Any]:
        mapping = dict(
            name=self.extensionName,
            developer=self.developer,
            developerURL=self.developerURL,
            launchAtStartUp=self.launchAtStartUp,
            mainScript=self.mainScript,
            version=self.version,
            addToMenu=self.addToMenu,
            html=self.html,
            documentationURL=self.documentationURL,
            uninstallScript=self.uninstallScript,
            timeStamp=self.timeStamp,
            requiresVersionMajor=self.requiresVersionMajor,
            requiresVersionMinor=self.requiresVersionMinor,
            expireDate=self.expireDate,
        )
        return {k: v for k, v in mapping.items() if v is not None}

    # ================
    # = classmethods =
    # ================

    @classmethod
    def load(cls, bundlePath: Path) -> Self:
        """
        From an existing bundle
        """
        plistLibPath = bundlePath / cls.infoPlistFilename
        assert plistLibPath.exists(), "info.plist file is missing, required to load the extension"
        plist = plistlib.loads(plistLibPath.read_bytes())

        licensePath = bundlePath / "license"
        requirementsPath = bundlePath / "requirements.txt"
        hashPath = bundlePath / ".hash"

        return cls(
            extensionName=plist.get("name") or plist.get("extensionName"),
            path=bundlePath,
            developer=plist["developer"],
            developerURL=plist["developerURL"],
            launchAtStartUp=plist["launchAtStartUp"],
            mainScript=plist["mainScript"],
            version=plist["version"],
            addToMenu=[AddToMenuDict(i) for i in plist.get("addToMenu", [])],
            html=plist["html"],
            hash=hashPath.read_text() if hashPath.exists() else "",
            documentationURL=plist.get("documentationURL"),
            uninstallScript=plist.get("uninstallScript"),
            timeStamp=plist.get("timeStamp"),
            requiresVersionMajor=plist.get("requiresVersionMajor"),
            requiresVersionMinor=plist.get("requiresVersionMinor"),
            expireDate=plist.get("expireDate"),
            license=licensePath.read_text() if licensePath.exists() else "",
            requirements=requirementsPath.read_text() if requirementsPath.exists() else "",
        )

    def save(self, destPath: Path, libFolder: Optional[Path] = None, htmlFolder: Optional[Path] = None, resourcesFolder: Optional[Path] = None):
        """
        Save the bundle to disk
        """
        assert self.hash == "", "Cannot save this extension"
        assert destPath.suffix == self.fileExtension, "Wrong file extension"
        assert destPath != self.bundlePath, "You cannot override the same file"
        if unwrappedLibPath := libFolder or self.libFolder:
            assert unwrappedLibPath.exists(), "Lib folder is required to save"
        else:
            assert False, "Lib folder is required to save"

        self.timeStamp = time.time()
        tempDir = Path(tempfile.mkdtemp())

        copytree(libFolder or self.libFolder, tempDir / self.libFolder.name)

        if (htmlFolder and htmlFolder.exists()) or self.htmlFolder.exists():
            copytree(htmlFolder or self.htmlFolder, tempDir / self.htmlFolder.name)
            self.convertMarkdown(tempDir / self.htmlFolder.name)

        if (resourcesFolder and resourcesFolder.exists()) or self.resourcesFolder.exists():
            copytree(resourcesFolder or self.resourcesFolder, tempDir / self.resourcesFolder.name)

        plist = self.infoDictionary
        (tempDir / "info.plist").write_bytes(plistlib.dumps({k: v for k, v in plist.items() if v}))

        if self.license:
            (tempDir / self.licensePath.name).write_text(self.license)

        if self.requirements:
            (tempDir / self.requirementsPath.name).write_text(self.requirements)

        if destPath.exists():
            rmtree(destPath)

        copytree(tempDir, destPath)
        rmtree(tempDir)
        return self.validate()

    def extensionHash(self, passphrase="") -> str:
        from os import walk

        digest = hashlib.sha1()
        # add private key
        digest.update(passphrase.encode("utf-8"))
        pathToDigest: list[Path] = []
        for root, dirs, files in walk(self.bundlePath):
            for name in files:
                # ignore
                if name in [f"Icon{chr(0x0D)}", self.hashPath.name]:
                    continue
                elif name.endswith(".DS_Store"):
                    continue
                filePath = Path(root) / name
                pathToDigest.append(filePath)
        for filePath in sorted(pathToDigest):
            digest.update(hashlib.sha1(filePath.name.encode()).digest())
            if filePath.is_file():
                with open(filePath, "rb") as f:
                    while True:
                        buf = f.read(1024 * 1024)
                        if not buf:
                            break
                        digest.update(buf)
        return digest.hexdigest()

    def unpack(self, destFolder: Path):
        """
        Save data on disk as unpacked source data
        Helpful for converting existing bundles into repositories
        """
        if destFolder.exists():
            rmtree(destFolder)
        destFolder.mkdir(parents=True, exist_ok=True)

        with open(destFolder / "info.yaml", mode='w') as yamlFile:
            yaml.dump(self.infoDictionary, yamlFile, sort_keys=False)

        data = {
            "libFolder": "source/lib",
            "resourcesFolder": "source/resources",
            "htmlFolder": "source/html",
            "requirements": AsLiteral(self.requirements),
            "license": AsLiteral(self.license),
        }

        with open(destFolder / "build.yaml", mode='w') as yamlFile:
            yaml.dump(
                {k: v for k, v in data.items() if v},
                yamlFile,
                sort_keys=False,
                allow_unicode=True
            )

        copytree(self.libFolder, destFolder / data["libFolder"])
        if htmlFolder := self.htmlFolder:
            copytree(htmlFolder, destFolder / data["htmlFolder"])
        if self.resourcesFolder.exists():
            copytree(self.resourcesFolder, destFolder / data["resourcesFolder"])

    # ========
    # = docs =
    # ========

    def convertMarkdown(self, htmlFolder: Path):
        """
        Convert documentation sources from Markdown to HTML.
        """
        # github-like css from https://github.com/sindresorhus/github-markdown-css
        styleData = """<style>
            @font-face{font-family:octicons-link;src:url(data:font/woff;charset=utf-8;base64,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) format('woff')}
            html{max-width:800px;padding:15px;margin-left:auto;margin-right:auto;}body{-ms-text-size-adjust:100%;-webkit-text-size-adjust:100%;line-height:1.5;color:#333;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif,"Apple Color Emoji","Segoe UI Emoji","Segoe UI Symbol";font-size:16px;line-height:1.5;word-wrap:break-word}body .pl-c{color:#969896}body .pl-c1,body .pl-s .pl-v{color:#0086b3}body .pl-e,body .pl-en{color:#795da3}body .pl-s .pl-s1,body .pl-smi{color:#333}body .pl-ent{color:#63a35c}body .pl-k{color:#a71d5d}body .pl-pds,body .pl-s,body .pl-s .pl-pse .pl-s1,body .pl-sr,body .pl-sr .pl-cce,body .pl-sr .pl-sra,body .pl-sr .pl-sre{color:#183691}body .pl-v{color:#ed6a43}body .pl-id{color:#b52a1d}body .pl-ii{color:#f8f8f8;background-color:#b52a1d}body .pl-sr .pl-cce{font-weight:700;color:#63a35c}body .pl-ml{color:#693a17}body .pl-mh,body .pl-mh .pl-en,body .pl-ms{font-weight:700;color:#1d3e81}body .pl-mq{color:teal}body .pl-mi{font-style:italic;color:#333}body .pl-mb{font-weight:700;color:#333}body .pl-md{color:#bd2c00;background-color:#ffecec}body .pl-mi1{color:#55a532;background-color:#eaffea}body .pl-mdr{font-weight:700;color:#795da3}body .pl-mo{color:#1d3e81}body .octicon{display:inline-block;vertical-align:text-top;fill:currentColor}body a{background-color:transparent;-webkit-text-decoration-skip:objects}body a:active,body a:hover{outline-width:0}body strong{font-weight:inherit}body strong{font-weight:bolder}body h1{font-size:2em;margin:.67em 0}body img{border-style:none}body svg:not(:root){overflow:hidden}body code,body kbd,body pre{font-family:monospace,monospace;font-size:1em}body hr{box-sizing:content-box;height:0;overflow:visible}body input{font:inherit;margin:0}body input{overflow:visible}body [type=checkbox]{box-sizing:border-box;padding:0}body *{box-sizing:border-box}body input{font-family:inherit;font-size:inherit;line-height:inherit}body a{color:#4078c0;text-decoration:none}body a:active,body a:hover{text-decoration:underline}body strong{font-weight:600}body hr{height:0;margin:15px 0;overflow:hidden;background:0 0;border:0;border-bottom:1px solid #ddd}body hr::before{display:table;content:""}body hr::after{display:table;clear:both;content:""}body table{border-spacing:0;border-collapse:collapse}body td,body th{padding:0}body h1,body h2,body h3,body h4,body h5,body h6{margin-top:0;margin-bottom:0}body h1{font-size:32px;font-weight:600}body h2{font-size:24px;font-weight:600}body h3{font-size:20px;font-weight:600}body h4{font-size:16px;font-weight:600}body h5{font-size:14px;font-weight:600}body h6{font-size:12px;font-weight:600}body p{margin-top:0;margin-bottom:10px}body blockquote{margin:0}body ol,body ul{padding-left:0;margin-top:0;margin-bottom:0}body ol ol,body ul ol{list-style-type:lower-roman}body ol ol ol,body ol ul ol,body ul ol ol,body ul ul ol{list-style-type:lower-alpha}body dd{margin-left:0}body code{font-family:Consolas,"Liberation Mono",Menlo,Courier,monospace;font-size:12px}body pre{margin-top:0;margin-bottom:0;font:12px Consolas,"Liberation Mono",Menlo,Courier,monospace}body .octicon{vertical-align:text-bottom}body input{-webkit-font-feature-settings:"liga" 0;font-feature-settings:"liga" 0}body::before{display:table;content:""}body::after{display:table;clear:both;content:""}body>:first-child{margin-top:0!important}body>:last-child{margin-bottom:0!important}body a:not([href]){color:inherit;text-decoration:none}body .anchor{float:left;padding-right:4px;margin-left:-20px;line-height:1}body .anchor:focus{outline:0}body blockquote,body dl,body ol,body p,body pre,body table,body ul{margin-top:0;margin-bottom:16px}body hr{height:.25em;padding:0;margin:24px 0;background-color:#e7e7e7;border:0}body blockquote{padding:0 1em;color:#777;border-left:.25em solid #ddd}body blockquote>:first-child{margin-top:0}body blockquote>:last-child{margin-bottom:0}body kbd{display:inline-block;padding:3px 5px;font-size:11px;line-height:10px;color:#555;vertical-align:middle;background-color:#fcfcfc;border:solid 1px #ccc;border-bottom-color:#bbb;border-radius:3px;box-shadow:inset 0 -1px 0 #bbb}body h1,body h2,body h3,body h4,body h5,body h6{margin-top:24px;margin-bottom:16px;font-weight:600;line-height:1.25}body h1 .octicon-link,body h2 .octicon-link,body h3 .octicon-link,body h4 .octicon-link,body h5 .octicon-link,body h6 .octicon-link{color:#000;vertical-align:middle;visibility:hidden}body h1:hover .anchor,body h2:hover .anchor,body h3:hover .anchor,body h4:hover .anchor,body h5:hover .anchor,body h6:hover .anchor{text-decoration:none}body h1:hover .anchor .octicon-link,body h2:hover .anchor .octicon-link,body h3:hover .anchor .octicon-link,body h4:hover .anchor .octicon-link,body h5:hover .anchor .octicon-link,body h6:hover .anchor .octicon-link{visibility:visible}body h1{padding-bottom:.3em;font-size:2em;border-bottom:1px solid #eee}body h2{padding-bottom:.3em;font-size:1.5em;border-bottom:1px solid #eee}body h3{font-size:1.25em}body h4{font-size:1em}body h5{font-size:.875em}body h6{font-size:.85em;color:#777}body ol,body ul{padding-left:2em}body ol ol,body ol ul,body ul ol,body ul ul{margin-top:0;margin-bottom:0}body li>p{margin-top:16px}body li+li{margin-top:.25em}body dl{padding:0}body dl dt{padding:0;margin-top:16px;font-size:1em;font-style:italic;font-weight:700}body dl dd{padding:0 16px;margin-bottom:16px}body table{display:block;width:100%;overflow:auto}body table th{font-weight:700}body table td,body table th{padding:6px 13px;border:1px solid #ddd}body table tr{background-color:#fff;border-top:1px solid #ccc}body table tr:nth-child(2n){background-color:#f8f8f8}body img{max-width:100%;box-sizing:content-box;background-color:#fff}body code{padding:0;padding-top:.2em;padding-bottom:.2em;margin:0;font-size:85%;background-color:rgba(0,0,0,.04);border-radius:3px}body code::after,body code::before{letter-spacing:-.2em;content:"\u00a0"}body pre{word-wrap:normal}body pre>code{padding:0;margin:0;font-size:100%;word-break:normal;white-space:pre;background:0 0;border:0}body .highlight{margin-bottom:16px}body .highlight pre{margin-bottom:0;word-break:normal}body .highlight pre,body pre{padding:16px;overflow:auto;font-size:85%;line-height:1.45;background-color:#f7f7f7;border-radius:3px}body pre code{display:inline;max-width:auto;padding:0;margin:0;overflow:visible;line-height:inherit;word-wrap:normal;background-color:transparent;border:0}body pre code::after,body pre code::before{content:normal}body .pl-0{padding-left:0!important}body .pl-1{padding-left:3px!important}body .pl-2{padding-left:6px!important}body .pl-3{padding-left:12px!important}body .pl-4{padding-left:24px!important}body .pl-5{padding-left:36px!important}body .pl-6{padding-left:48px!important}body .full-commit .btn-outline:not(:disabled):hover{color:#4078c0;border:1px solid #4078c0}body kbd{display:inline-block;padding:3px 5px;font:11px Consolas,"Liberation Mono",Menlo,Courier,monospace;line-height:10px;color:#555;vertical-align:middle;background-color:#fcfcfc;border:solid 1px #ccc;border-bottom-color:#bbb;border-radius:3px;box-shadow:inset 0 -1px 0 #bbb}body :checked+.radio-label{position:relative;z-index:1;border-color:#4078c0}body .task-list-item{list-style-type:none}body .task-list-item+.task-list-item{margin-top:3px}body .task-list-item input{margin:0 .2em .25em -1.6em;vertical-align:middle}body hr{border-bottom-color:#eee}.codehilite .c{color:#999}.codehilite .err{color:red}.codehilite .g{color:#363636}.codehilite .k{color:#4998ff}.codehilite .l{color:#93a1a1}.codehilite .n{color:#363636}.codehilite .o{color:#aa25ff}.codehilite .x{color:#cb4b16}.codehilite .p{color:#93a1a1}.codehilite .cm{color:#586e75}.codehilite .cp{color:#aa25ff}.codehilite .c1{color:#586e75}.codehilite .cs{color:#aa25ff}.codehilite .gd{color:#2aa198}.codehilite .ge{color:#93a1a1;font-style:italic}.codehilite .gr{color:#dc322f}.codehilite .gh{color:#cb4b16}.codehilite .gi{color:#aa25ff}.codehilite .go{color:#93a1a1}.codehilite .gp{color:#93a1a1}.codehilite .gs{color:#93a1a1;font-weight:700}.codehilite .gu{color:#cb4b16}.codehilite .gt{color:#93a1a1}.codehilite .kc{color:#cb4b16}.codehilite .kd{color:#268bd2}.codehilite .kn{color:#4998ff}.codehilite .kp{color:#aa25ff}.codehilite .kr{color:#268bd2}.codehilite .kt{color:#dc322f}.codehilite .ld{color:#c42f07}.codehilite .m{color:#c42f07}.codehilite .s{color:#ff05da}.codehilite .na{color:#93a1a1}.codehilite .nb{color:#0bd51e}.codehilite .nc{color:#ff3ca8}.codehilite .no{color:#ff3ca8}.codehilite .nd{color:#ff3ca8}.codehilite .ni{color:#ff3ca8}.codehilite .ne{color:#ff3ca8}.codehilite .nf{color:#ff3ca8}.codehilite .nl{color:#ff3ca8}.codehilite .nn{color:#354980}.codehilite .nx{color:#555}.codehilite .py{color:#93a1a1}.codehilite .nt{color:#268bd2}.codehilite .nv{color:#268bd2}.codehilite .ow{color:#aa25ff}.codehilite .w{color:#93a1a1}.codehilite .mf{color:#c42f07}.codehilite .mh{color:#c42f07}.codehilite .mi{color:#c42f07}.codehilite .mo{color:#c42f07}.codehilite .sb{color:#ff05da}.codehilite .sc{color:#ff05da}.codehilite .sd{color:#ff05da}.codehilite .s2{color:#ff05da}.codehilite .se{color:#ff05da}.codehilite .sh{color:#ff05da}.codehilite .si{color:#ff05da}.codehilite .sx{color:#ff05da}.codehilite .sr{color:#ff05da}.codehilite .s1{color:#ff05da}.codehilite .ss{color:#ff05da}.codehilite .bp{color:#f29108}.codehilite .vc{color:#268bd2}.codehilite .vg{color:#268bd2}.codehilite .vi{color:#268bd2}.codehilite .il{color:#c42f07}
        </style>
        """
        cssPath = htmlFolder / "style.css"
        if cssPath.exists():
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

        for eachPath in htmlFolder.glob("**/*.md"):
            with open(eachPath, "r", encoding="utf-8") as f:
                htmlData = markdown.markdown(
                    f.read(),
                    extensions=[
                        markdownTableExtension(),
                        markdownTocExtension(permalink=False, toc_depth="2-3"),
                        markdownFencedCodeExtension(),
                        markdownCodeHiliteExtension(),
                    ],
                )
                destPath = eachPath.with_suffix(".html")

                html = htmlTemplate % (styleData, htmlData)
                with open(destPath, "w", encoding="utf-8") as f:
                    f.write(html)

    def validate(self) -> bool:
        self._errors = []

        if not self.bundlePath.exists():
            msg = "Extension bundle must be saved on disk before it can be validated."
            self._errors.append(msg)
            return False

        if self.bundlePath.suffix != self.fileExtension:
            msg = f"Extension bundle must be saved with `{self.fileExtension}` suffix."
            self._errors.append(msg)

        if not self.infoPlistPath.exists():
            msg = "info.plist does not exist, this is required."
            self._errors.append(msg)
            return False

        try:
            plistlib.loads(self.infoPlistPath.read_bytes())
        except Exception:
            msg = "info.plist is not formatted as a *.plist file and unreadable."
            self._errors.append(msg)
            return False

        reprToAttribute = {
            "Extension name": self.extensionName,
            "Developer name": self.developer,
            "Developer URL": self.developerURL,
            "Extension version": self.version
        }
        for name, attribute in reprToAttribute.items():
            if not isinstance(attribute, str):
                msg = f"{name} should be a string: {attribute}"
                self._errors.append(msg)
            elif len(attribute) == 0:
                msg = f"{name} cannot be an empty string"
                self._errors.append(msg)

        if not isinstance(self.addToMenu, list):
            msg = f"Add to Menu should be a list, instead it is a {type(self.addToMenu)}"
            self._errors.append(msg)
        else:
            for add in self.addToMenu:
                for key in ["path", "preferredName"]:
                    if key not in add:
                        msg = f"`{key}` missing from Add to Menu dictionary"
                        self._errors.append(msg)
                    elif not isinstance(add[key], str):
                        msg = f"Add to Menu `{key}` should be a `str`, instead it is a {type(add[key])}"
                        self._errors.append(msg)

                if "shortKey" not in add:
                    msg = f"`shortKey` missing from Add to Menu dictionary"
                    self._errors.append(msg)
                elif not (isinstance(add["shortKey"], str) or isinstance(add["shortKey"], tuple)):
                    msg = f"Add to Menu `shortKey` should be a `str` or a `tuple`, instead it is a {type(add['shortKey'])}"
                    self._errors.append(msg)

                if nest := add.get("nestInSubmenus"):
                    if not (isinstance(nest, bool) or isinstance(nest, int)):
                        msg = f"Add to Menu `nestInSubmenus` should be a `bool` or a `int`, instead it is a {type(nest)}"
                        self._errors.append(msg)

        # check the unwrapped type is not None
        additionalKeys = {
            "html": (bool, int),
            "documentationURL": str,
            "launchAtStartUp": (bool, int),
            "mainScript": str,
            "requiresVersionMajor": str,
            "requiresVersionMinor": str,
            "uninstallScript": str,
        }
        attributeNameToRepr = {
            "html": "html",
            "documentationURL": "Documentation URL",
            "launchAtStartUp": "Launch at startup",
            "mainScript": "Main script",
            "requiresVersionMajor": "Requires version major",
            "requiresVersionMinor": "Requires version minor",
            "uninstallScript": "Uninstall Script",
        }
        for attributeName, types in additionalKeys.items():
            if attribute := getattr(self, attributeName):
                if not isinstance(attribute, types):
                    msg = f"{attributeNameToRepr[attributeName]} should be a {types}"
                    self._errors.append(msg)

        if isinstance(self.html, int) and self.html not in {0, 1}:
            msg = "`html` can be an int, but it should be either 0 or 1"
            self._errors.append(msg)

        if isinstance(self.launchAtStartUp, int) and self.launchAtStartUp not in {0, 1}:
            msg = "`launchAtStartUp` can be an int, but it should be either 0 or 1"
            self._errors.append(msg)

        if not self.libFolder.exists():
            msg = "Lib folder does not exist, this is required."
            self._errors.append(msg)

        if mainScript := self.mainScript:
            if not (self.libFolder / mainScript).exists():
                msg = "Main .py script does not exist, this is required."
                self._errors.append(msg)

        if uninstallScript := self.uninstallScript:
            if not (self.libFolder / uninstallScript).exists():
                msg = "Uninstall script does not exist, since it is defined, it is required"
                self._errors.append(msg)

        for pyPath in self.libFolder.glob("**/*.py"):
            try:
                compile(pyPath.read_text(), "tool.py", 'exec', ast.PyCF_ONLY_AST)
            except SyntaxError as error:
                self._errors.append(error.msg)

        if url := self.documentationURL:
            if not isValidURL(url):
                msg = "Documentation URL is not valid"
                self._errors.append(msg)

        if url := self.developerURL:
            if not isValidURL(url):
                msg = "Developer URL is not valid"
                self._errors.append(msg)

        if self.expireDate:
            try:
                datetime.strptime(self.expireDate, self.expireDateFormat)
            except ValueError:
                msg = "expire date is not set in the correct format: 'YYYY-MM-DD'. "
                self._errors.append(msg)

        return not bool(self._errors)

    def validationErrors(self):
        """
        Returns the validation errors as a string.
        """
        self.validate()
        return "\n".join(self._errors)
