import os
import shutil
import sys
from argparse import ArgumentParser
from pathlib import Path

import yaml

from .bundle import ExtensionBundle, loadFromPlist


def pack(
    info_path=Path("info.yaml"),
    build_path=Path("build.yaml"),
    zip_extension=False,
):
    """
    From unpacked data to extension bundle

    """
    assert info_path.exists(), "info_path does not exist"
    assert build_path.exists(), "build_path does not exist"

    with open(info_path) as yamlFile:
        infoData = yaml.safe_load(yamlFile)
    with open(build_path) as yamlFile:
        buildData = yaml.safe_load(yamlFile)

    name = infoData["name"]
    destPath = Path(buildData.get("extensionPath", f"{name}.roboFontExt"))

    bundle = ExtensionBundle(
        extensionName=infoData.get("name") or infoData.get("extensionName"),
        developer=infoData["developer"],
        developerURL=infoData["developerURL"],
        launchAtStartUp=infoData["launchAtStartUp"],
        mainScript=infoData.get("mainScript"),
        version=infoData["version"],
        addToMenu=[loadFromPlist(i) for i in infoData.get("addToMenu", [])],
        html=infoData.get("html"),
        documentationURL=infoData.get("documentationURL"),
        uninstallScript=infoData.get("uninstallScript"),
        requiresVersionMajor=infoData.get("requiresVersionMajor"),
        requiresVersionMinor=infoData.get("requiresVersionMinor"),
        expireDate=infoData.get("expireDate"),
        license=buildData.get("license", ""),
        requirements=buildData.get("requirements", "") or "",
    )

    htmlFolder = buildData.get("htmlFolder")
    if htmlFolder is not None:
        htmlFolder = Path(htmlFolder)

    resourcesFolder = buildData.get("resourcesFolder")
    if resourcesFolder is not None:
        resourcesFolder = Path(resourcesFolder)

    bundle.save(
        destPath=destPath,
        libFolder=Path(buildData["libFolder"]),
        htmlFolder=htmlFolder,
        resourcesFolder=resourcesFolder,
    )

    bundle = ExtensionBundle.load(bundlePath=destPath)
    errors = bundle.validationErrors()

    if zip_extension:
        shutil.make_archive(str(destPath), format="zip", base_dir=destPath)
        shutil.rmtree(destPath)

    if env := os.getenv("GITHUB_ENV"):
        with open(env, mode="a") as envFile:  # type: ignore
            envFile.write(f"EXTENSION_PATH={destPath}")

    if errors:
        print(errors)
    sys.exit(bool(errors))


def main():
    parser = ArgumentParser(
        prog="Pack Robofont Extensions",
        description="Create a RF extension from info.yaml, build.yaml and sources (code, html, resources)",
    )

    parser.add_argument(
        "--info_path",
        default=Path("info.yaml"),
        type=Path,
        help="info.yaml path",
    )
    parser.add_argument(
        "--build_path",
        default=Path("build.yaml"),
        type=Path,
        help="build.yaml path",
    )
    parser.add_argument(
        "-z",
        "--zip",
        action="store_true",
        help="compress extension",
    )
    args = parser.parse_args()
    pack(
        info_path=args.info_path,
        build_path=args.build_path,
        zip_extension=args.zip,
    )


if __name__ == "__main__":
    main()
