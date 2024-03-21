# RoboFont Extension Bundle

This repository contains the code used by RoboFont to build plugins. The RoboFont team decided to open-source this package to allow developers to build extensions outside RoboFont, using GitHub actions or other CD/CI tools. The code is OS agnostic and completely type annotated.

## Installation

You can install the package using `pip`:

```
pip install git+https://github.com/typemytype/extensionBundle
```

It is always adviced to use a virtual environment.

## Command line interface

The package has a command line interface `pack` accepting three arguments:
- `--info_path`: info.yaml path on disk
- `--build_path`: build.yaml path on disk
- `--zip`: boolean for archiving the extension or not

## Examples

### Initiate a new plugin

To start a new plugin from scratch you just need to initiate the `ExtensionBundle` class:

```python
from roboFontExtensionBundle.bundle import ExtensionBundle
bundle = ExtensionBundle()

```

You can either pass data to the plugin during the initiation, or setting the attributes after:

```python
from roboFontExtensionBundle.bundle import ExtensionBundle
bundle = ExtensionBundle(
    name="My Plugin",
    developer="Bob Ross",
    version="2.0",
)

```
or

```python
from roboFontExtensionBundle.bundle import ExtensionBundle
bundle = ExtensionBundle()
bundle.name="My Plugin"
bundle.developer="Bob Ross"
bundle.version="2.0"

```

### Load plugin from disk

You can load a plugin from disk with the following code:

```python
from roboFontExtensionBundle.bundle import ExtensionBundle
bundle = ExtensionBundle()
bundle.load("myExtension.roboFontExt")

```

### Unpack from existing `.roboFontExt` extension

It might be convient to unpack an existing `.roboFontExt` into source files and yaml files with metadata. It is as easy as:

```python
from roboFontExtensionBundle.bundle import ExtensionBundle
bundle = ExtensionBundle()
bundle.load("myExtension.roboFontExt")
bundle.unpack("unpacked")

```

It will result in the following folder structure:

```
myExtension.roboFontExt
unpacked/
├─ info.yaml
├─ build.yaml
├─ source/
│  ├─ lib/
│  │  ├─ tool.py
│  ├─ html/
│  │  ├─ index.html
│  ├─ resources/
│  │  ├─ image.png

```


## Use with Github Actions

The RoboFont team prepared a ready-to-use [action](https://github.com/typemytype/roboFont-Extension-action) for Github that you can include in your workflows:

```yaml
name: Validate and Build the Extension
on:
  push

jobs:
  validate_and_build:
    runs-on: ubuntu-latest
    steps:
      - name: Validate and Build
        uses: typemytype/roboFont-Extension-action@v0.1.0
        with:
            autotagging: false # default false

```

### Autotagging

When `autotagging` is set to `true`, the action will automatically generate a release named with the version number set in the `info.yaml` file (if not existing yet). In other words, when you'll edit the extension version number and push to the remote, the action will automatically take care of making a new release. Anytime a letter `b` is contained in the version number (as for `4.0b` or `3.4-beta1`), the action will consider the version as beta and generate a release marked as "pre-release". In this way [Mechanic 2](https://github.com/robofont-mechanic/mechanic-2) will not distribute it as a stable release.

### Naming

GitHub does not allow assets attached to release to contain word spaces. If your extension name is made of multiple words, like `Glyph Nanny`, we suggest to set a `path` in the `build.yaml` with a name not containing any space (`Glyph_Nanny.roboFontExt`).


## Templates

Did you know that there are repository templates to start your new extensions?
Check:
- https://github.com/roboDocs/rf-extension-boilerplate
- https://github.com/roboDocs/single-windowcontroller-with-multiple-subscribers
