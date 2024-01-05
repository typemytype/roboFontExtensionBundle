import datetime
import os
import shutil
import sys
import warnings
from dataclasses import dataclass

from packaging import version

from AppKit import NSURL  # type: ignore
from AppKit import NSApp  # type: ignore
from AppKit import NSArray  # type: ignore
from AppKit import NSBundle  # type: ignore
from AppKit import NSCommandKeyMask  # type: ignore
from AppKit import NSControlKeyMask  # type: ignore
from AppKit import NSDictionary  # type: ignore
from AppKit import NSFileManager  # type: ignore
from AppKit import NSImage  # type: ignore
from AppKit import NSMenu  # type: ignore
from AppKit import NSMenuItem  # type: ignore
from AppKit import NSWorkspace  # type: ignore
from lib.settings import applicationPluginRootPath, appName
from lib.tools.misc import walkDirectoryForFile
from lib.tools.notifications import PostBannerNotification
from lib.tools.shortCutTools import allExistingShortKeys

from .extensionTools import PluginHelpWindow, askReinstallDeinstall
from .scriptTools import Output, ScriptRunner
from .extensionBundle import ExtensionBundle


@dataclass
class RoboFontExtensionBundle(ExtensionBundle):


    def openHelp(self):
        """
        Open a help window for the extension.
        """
        if self.hasDocumentation():
            return PluginHelpWindow(self)

    def getDocumentationNSURL(self):
        """
        Get the documentation URL as a `NSURL` object.
        """
        if self.documentationURL:
            return NSURL.URLWithString_(self.documentationURL)
        return None

    def getDeveloperNSURL(self):
        """
        Get the developer URL as a `NSURL` object.
        """
        if self.developerURL:
            return NSURL.URLWithString_(self.developerURL)
        return None


    # ===========
    # = updates =
    # ===========

    @classmethod
    def updateScriptingMenu(cls):
        """
        Update the scripting menu.
        """
        NSApp().delegate().updateMenu_(None)

    @classmethod
    def updatePreferenceWindow(cls):
        """
        Update the Preferences window.
        """
        preferencesWindow = NSApp().delegate().preferencesWindow()
        if preferencesWindow is not None:
            preferencesWindow.updatePreferences()

    @classmethod
    def _executeScript(cls, path, action="Installing", name="-", libPath=None):
        stdout = Output()
        stderr = Output(isError=True)
        if libPath:
            sys.path.insert(0, libPath)
        ScriptRunner(path=path, stdout=stdout, stderr=stderr)
        if "".join(stderr.data).strip():
            line = "*" * 20
            indent = "  "
            print(line)
            print("%s '%s' report:" % (action, name))
            print(indent + indent.join(stderr.data))
            print(line)
        if libPath:
            sys.path.remove(libPath)


    # ===========
    # = install =
    # ===========

    def install(self, showMessages=True):
        """
        Install the extension.

        Optionally, use `showMessages` to disable messages.
        """
        succes, infoMessage = self._install(showMessages)
        if showMessages and infoMessage:
            infoTitle = "Installing Extension"
            if "uninstalled" in infoMessage:
                infoTitle = "uninstalling Extension"
            PostBannerNotification(infoTitle, infoMessage)
        return succes, infoMessage

    def deinstall(self, update=True):
        """
        Uninstall the extension.
        """
        self._deinstall(update=update)

    # private install

    def _install(self, showMessages=True):
        # create a the application support dir if its not existing
        if not os.path.exists(applicationPluginRootPath):
            os.makedirs(applicationPluginRootPath)

        # validate the extention
        if not self.validate():
            print(self.validationErrors())
            return False, "Not a valid extension (%s)" % self.fileName()

        succes, errorMessage = self._installHelper()
        if not succes:
            return succes, errorMessage

        installPath = os.path.join(applicationPluginRootPath, self.fileName())

        if installPath == self.bundlePath():
            return (
                False,
                "Cannot install the same extension from the same destination. (%s)"
                % self.fileName(),
            )

        if os.path.exists(installPath):
            if showMessages:
                value = askReinstallDeinstall(
                    "Extension '%s' already installed." % self.fileName(),
                    "Do you want to reinstall or uninstall the extension?",
                )
            else:
                value = 0

            if value == 0:  # reinstall
                otherBundle = self.__class__(path=installPath)
                otherBundle.deinstall(update=False)
            elif value == 1:  # unintall
                otherBundle = self.__class__(path=installPath)
                otherBundle.deinstall()
                self.updatePreferenceWindow()
                return True, "Extension '%s' is uninstalled" % self.fileName()
            else:  # cancel
                self.updatePreferenceWindow()
                return (
                    True,
                    "",
                )  # "Installation of '%s' was cancelled." % self.fileName()

        if (
            self.requiresVersionMajor is not None
            and self.requiresVersionMinor is not None
        ):
            requiredVersion = "%s.%s" % (
                self.requiresVersionMajor,
                self.requiresVersionMinor,
            )
            appVersion = NSBundle.mainBundle().infoDictionary()[
                "CFBundleShortVersionString"
            ]
            if version.Version(appVersion) < version.Version(requiredVersion):
                return False, "Extension '%s' requires %s %s" % (
                    self.fileName(),
                    appName,
                    requiredVersion,
                )

        resolvedRequirements = self.resolveRequirements()
        if resolvedRequirements:
            return (
                False,
                "Extension %s requires other extensions to be installed: '%s'\n\nInstall those extensions first."
                % (self.fileName(), ", ".join(sorted(resolvedRequirements))),
            )

        fm = NSFileManager.defaultManager()
        fm.copyItemAtPath_toPath_error_(self.bundlePath(), installPath, None)
        self._bundlePath = installPath

        if self.addToMenu:
            self.updateScriptingMenu()

        if self.launchAtStartUp:
            self._executeScript(
                self.mainScriptPath(), "Installing", self.name, self.libPath()
            )

        self.updatePreferenceWindow()
        return True, "Done installing '%s' (version %s)." % (self.name, self.version)

    def _installHelper(self, verbose=True):
        # expireDate and hash is present
        hashPath = os.path.join(self.bundlePath(), ".hash")
        hasHashPath = os.path.exists(hashPath)
        expireDate = self.expireDate
        if hasHashPath or expireDate:
            if expireDate is None:
                if verbose:
                    print("Missing expireDate.")
                return False, "Not a valid extension (%s)" % self.fileName()
            elif not hasHashPath:
                if verbose:
                    print("Missing hash.")
                return False, "Not a valid extension (%s)" % self.fileName()
            extensionHash = self.extensionHash("roboFont.extension.hash")
            hashData = None
            with open(hashPath, "r") as f:
                hashData = f.read()
                hashData = hashData.strip()
            if hashData != extensionHash:
                if verbose:
                    print("Hash does not match.")
                return False, "Not a valid extension (%s)" % self.fileName()
            expireDate = datetime.datetime.strptime(expireDate, self.expireDateFormat)
            if expireDate < datetime.datetime.now():
                if verbose:
                    print("Extension is expired.")
                return False, "Extension is expired (%s)" % self.fileName()
        return True, ""

    def _deinstall(self, update=True):
        if self.uninstallScript is not None:
            uninstallScriptPath = self.uninstallScriptPath()
            if os.path.exists(uninstallScriptPath) and uninstallScriptPath.endswith(
                ".py"
            ):
                self._executeScript(
                    uninstallScriptPath, "Deinstalling", self.name, self.libPath()
                )

        if os.path.exists(self.bundlePath()):
            shutil.rmtree(self.bundlePath())
        if update:
            self.updateScriptingMenu()
            self.updatePreferenceWindow()


    # ===============
    # = all plugins =
    # ===============

    @classmethod
    def allExtensions(cls):
        """
        Get a list of all installed extensions.
        """
        if not os.path.exists(applicationPluginRootPath):
            return []
        items = os.listdir(applicationPluginRootPath)
        items.sort(key=str.casefold)
        return [
            item for item in items if item.lower().endswith(cls.fileExtension.lower())
        ]

    @classmethod
    def setAllExtensions(cls, value):
        """
        Set all extensions. This does nothing, use `install` instead.
        """
        pass

    @classmethod
    def loadAllExtensions(cls):
        """
        Loads all installed extensions. This is used by RoboFont during startup.
        """
        extentions = cls.allExtensions()
        done = []
        for extension in extentions:
            # dont load the same extension twice
            if extension in done:
                continue
            bundle = cls(extension)
            cls._loadBundle(bundle, done)
            done.append(bundle.fileName())

    @classmethod
    def _loadBundle(cls, bundle, done):
        if not bundle.bundleExists():
            return
        if not os.path.exists(bundle.infoDictionaryPath()):
            return
        succes, message = bundle._installHelper(verbose=False)
        if not succes:
            print(f"Cannot load extension '{bundle.name}': {message}.")
            PostBannerNotification(f"Loading Extension '{bundle.name}'", message)
            return
        if bundle.launchAtStartUp and os.path.exists(bundle.mainScriptPath()):
            # resolve requirements
            bundle.loadRequirements(done)
            bundle._executeScript(
                bundle.mainScriptPath(), "Installing", bundle.name, bundle.libPath()
            )

    @classmethod
    def buildExtensionMenu(cls, menu):
        """
        Build the menu for the extension.
        """
        allExtensions = cls.allExtensions()
        for extensionName in allExtensions:
            bundle = cls(extensionName)
            if not bundle.bundleExists():
                continue
            if not os.path.exists(bundle.infoDictionaryPath()):
                continue
            succes, _ = bundle._installHelper(verbose=False)
            if not succes:
                continue
            if bundle.addToMenu:
                if len(bundle.addToMenu) == 1 and not bundle.hasDocumentation():
                    pluginMenuItem = cls._getMenuItemForBundleAction(
                        bundle, bundle.addToMenu[0], menu
                    )
                else:
                    pluginMenu = NSMenu.alloc().initWithTitle_(bundle.name)

                    for infoMenu in bundle.addToMenu:
                        item = cls._getMenuItemForBundleAction(
                            bundle, infoMenu, pluginMenu
                        )

                    if bundle.hasDocumentation():
                        pluginMenu.addItem_(NSMenuItem.separatorItem())
                        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                            "Help", "helpPlugin:", ""
                        )
                        item.setRepresentedObject_(extensionName)
                        pluginMenu.addItem_(item)

                    pluginMenuItem = (
                        NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                            bundle.name, None, ""
                        )
                    )
                    pluginMenuItem.setSubmenu_(pluginMenu)
                    menu.addItem_(pluginMenuItem)

        if menu.numberOfItems():
            menu.addItem_(NSMenuItem.separatorItem())

    @classmethod
    def _getMenuItemForBundleAction(cls, bundle, infoMenu, mainMenu):
        allShortKeys = allExistingShortKeys()
        preferredName = infoMenu.get("preferredName", infoMenu["path"])
        shortKey = infoMenu.get("shortKey", "")
        currentMenu = mainMenu
        if infoMenu.get("nestInSubmenus", False):
            levels = infoMenu["path"].split(os.sep)
            for level in levels[:-1]:
                item = currentMenu.itemWithTitle_(level)
                if item is None:
                    item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                        level, "", ""
                    )
                    currentMenu.addItem_(item)
                    currentMenu = NSMenu.alloc().initWithTitle_(level)
                    item.setSubmenu_(currentMenu)
                else:
                    currentMenu = item.submenu()

        if isinstance(shortKey, (tuple, list, NSArray)):
            modifier, shortKey = shortKey
        else:
            modifier = NSCommandKeyMask | NSControlKeyMask

        if (modifier, shortKey) in allShortKeys:
            warnings.warn(
                f"Extension '{bundle.name}' short cut is not available: {shortKey} - {modifier}.",
                UserWarning,
            )
            shortKey = ""
            modifier = None

        scriptPath = os.path.join(bundle.libPath(), infoMenu["path"])
        scriptFileName = os.path.basename(scriptPath)

        script = dict(fileName=scriptFileName, path=scriptPath)

        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            preferredName, "executeScript:", shortKey
        )
        if modifier:
            item.setKeyEquivalentModifierMask_(modifier)
        item.setRepresentedObject_(script)
        currentMenu.addItem_(item)
