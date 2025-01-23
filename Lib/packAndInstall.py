"""
A RoboFont script for developers to pack and install extensions from source.
"""
import yaml
from pathlib import Path
import shutil
from mojo.extensions import ExtensionBundle
import ezui


def extensionBundleInstall(root, infoPath=Path("info.yaml"), buildPath=Path("build.yaml"), keepExtension=False):
    root = Path(root)

    with open(root / infoPath) as yamlFile:
        infoData = yaml.safe_load(yamlFile)
    with open(root / buildPath) as yamlFile:
        buildData = yaml.safe_load(yamlFile)

    bundle = ExtensionBundle(
        **infoData,
        license=buildData.get("license", ""),
        requirements=buildData.get("requirements", "") or ""
    )

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
            title="Pack and Install Extension",
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

