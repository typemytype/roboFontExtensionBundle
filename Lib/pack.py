import os
import shutil
import sys
from argparse import ArgumentParser
from pathlib import Path

import yaml

from .bundle import ExtensionBundle, _loadAddToMenuFromPlist


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

    name = infoData.pop("name")
    destPath = Path(buildData.get("path", f"{name}.roboFontExt"))

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
    bundle = ExtensionBundle()
    bundle.load(bundlePath=destPath)
    errors = bundle.validationErrors()

    if zip_extension:
        archiveName = shutil.make_archive(
            str(destPath), format="zip", base_dir=destPath
        )
        archivePath = destPath.parent / archiveName
        archivePath = archivePath.rename(archiveName.replace(" ", "_"))
        shutil.rmtree(destPath)

        if env := os.getenv("GITHUB_ENV"):
            with open(env, mode="a") as envFile:  # type: ignore
                envFile.write(f"EXTENSION_ZIP_PATH={archivePath}\n")

    if env := os.getenv("GITHUB_ENV"):
        with open(env, mode="a") as envFile:  # type: ignore
            envFile.write(f"EXTENSION_PATH={destPath}\n")

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
