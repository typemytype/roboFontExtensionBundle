import json
from pathlib import Path
from shutil import unpack_archive
from time import sleep
from typing import cast
from urllib.parse import urlparse
from urllib.request import urlretrieve

from Lib.extensionBundle import ExtensionBundle

jsonURL = "http://robofontmechanic.com/api/v2/registry.json"


urlFormatters = dict(
    github=dict(
        zipPath="https://api.github.com/repos{repositoryPath}/zipball",
        infoPlistPath="https://raw.githubusercontent.com{repositoryPath}/master/{extensionPath}/info.plist",
        releasesPath="https://github.com{repositoryPath}/releases"
    ),
    gitlab=dict(
        zipPath="https://gitlab.com{repositoryPath}/-/archive/master/{repositoryName}-master.zip",
        infoPlistPath="https://gitlab.com{repositoryPath}/raw/master/{extensionPath}/info.plist",
        releasesPath="https://gitlab.com{repositoryPath}/-/releases"
    ),
    bitbucket=dict(
        zipPath="https://bitbucket.org{repositoryPath}/get/master.zip",
        infoPlistPath="https://bitbucket.org{repositoryPath}/src/master/{extensionPath}/info.plist",
        releasesPath="https://bitbucket.org{repositoryPath}/downloads/?tab=tags"
    )
)

folder = Path(".extensions_cache")

if __name__ == '__main__':
    jsonPath = folder / "registry.json"
    urlretrieve(jsonURL, jsonPath)
    data = json.loads(jsonPath.read_text())

    for extension in cast(list[dict[str, str]], data["extensions"]):
        extensionFolder  = folder / cast(str, extension["extensionName"])
        if not extensionFolder.exists():
            extensionFolder.mkdir(exist_ok=True)

            repoURL = extension["repository"]
            if "gitlab" in repoURL:
                key = "gitlab"
            elif "github" in repoURL:
                key = "github"
            elif "bitbucket" in repoURL:
                key = "bitbucket"
            else:
                raise ValueError("Something wrong in mechanic json")
            
            remoteZipURL = extension.get("zipPath")
            if remoteZipURL is None:
                remoteZipURL = urlFormatters[key]["zipPath"].format(
                    repositoryPath=urlparse(extension["repository"]).path,
                    extensionPath=extension["extensionPath"],
                    repositoryName=extension["extensionName"]
                )

            print(remoteZipURL)
            archivePath = extensionFolder / "archive.zip"
            urlretrieve(remoteZipURL, filename=archivePath)
            sleep(1)
            unpack_archive(archivePath, extensionFolder)
            # archivePath.unlink()

        extensionPath = extensionFolder / extension["extensionPath"]

    for eachPath in folder.glob("**/*.roboFontExt"):
        bundle = ExtensionBundle.load(bundlePath=eachPath)
        errors = bundle.validationErrors()
        eachPath.with_suffix(".txt").write_text(errors)

