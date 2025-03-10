"""
A RoboFont script for developpers to pack and install extensions from source.
"""
import yaml
from pathlib import Path
import shutil
from roboFontExtensionBundle.bundle import _loadAddToMenuFromPlist
from mojo.extensions import ExtensionBundle
import ezui


def extensionBundleInstall(root, infoPath=Path("info.yaml"), buildPath=Path("build.yaml"), keepExtension=False):
    root = Path(root)

    with open(root / infoPath) as yamlFile:
        infoData = yaml.safe_load(yamlFile)
    with open(root / buildPath) as yamlFile:
        buildData = yaml.safe_load(yamlFile)

    name = infoData.pop("name")

    bundle = ExtensionBundle(
        name=name,
        path=infoData.pop("path", None),
        developer=infoData.pop("developer"),
        developerURL=infoData.pop("developerURL"),
        launchAtStartUp=infoData.pop("launchAtStartUp"),
        mainScript=infoData.pop("mainScript", None),
        version=str(infoData["version"]),
        addToMenu=[_loadAddToMenuFromPlist(i) for i in infoData.pop("addToMenu", [])],
        html=infoData.pop("html", None),
        documentationURL=infoData.pop("documentationURL", None),
        uninstallScript=infoData.pop("uninstallScript", None),
        requiresVersionMajor=infoData.pop("requiresVersionMajor", None),
        requiresVersionMinor=infoData.pop("requiresVersionMinor", None),
        expireDate=infoData.pop("expireDate", None),
        license=buildData.pop("license", ""),
        requirements=buildData.pop("requirements", "") or "",
    )
    bundle.lib.update(infoData)

    destPath = root / buildData.get("path", f"{bundle.name}.roboFontExt")

    htmlFolder = buildData.get("htmlFolder")
    if htmlFolder is not None:
        htmlFolder = root / htmlFolder

    resourcesFolder = buildData.get("resourcesFolder")
    if resourcesFolder is not None:
        resourcesFolder = root / resourcesFolder

    bundle.save(
        destPath=destPath,
        libFolder=root / buildData["libFolder"],
        htmlFolder=htmlFolder,
        resourcesFolder=resourcesFolder,
    )
    errors = bundle.validationErrors()
    if not errors:
        bundle.install()
    else:
        print(errors)

    if not keepExtension:
        shutil.rmtree(destPath)


class PackAndInstallController(ezui.WindowController):

    def build(self, path=None):
        content = """
        = TwoColumnForm
        : Root:
        * PathPopUp               @root

        : Info:
        [_ info.yaml _]           @infoPath

        : Build:
        [_ build.yaml _]          @buildPath

        =---=
        [X] Keep Extension        @keepExtension
        ( Build And Install )     @buildAndInstall

        """
        descriptionData = dict(
            content=dict(
                itemColumnWidth=220
            ),
            root=dict(
                path=path
            )
        )
        self.w = ezui.EZWindow(
            title="Pack and Intall Extension",
            content=content,
            descriptionData=descriptionData,
            size="auto",
            controller=self
        )

    def started(self):
        self.w.open()

    def buildAndInstallCallback(self, sender):
        data = self.w.getItemValues()
        extensionBundleInstall(**data)


if __name__ == "__main__":
    PackAndInstallController()

