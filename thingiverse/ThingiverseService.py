# Copyright (c) 2020 Chris ter Beke.
# Thingiverse plugin is released under the terms of the LGPLv3 or higher.
import pathlib
import tempfile
from typing import List, Optional, Dict, TYPE_CHECKING

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot, QUrl
from PyQt5.QtWidgets import QMessageBox

from cura.CuraApplication import CuraApplication
from .ThingiverseApiClient import ThingiverseApiClient, JSONObject
from ..Settings import Settings

if TYPE_CHECKING:
    from .ThingiverseExtension import ThingiverseExtension


class ThingiverseService(QObject):
    """
    The ThingiverseService uses the API client to serve Thingiverse content to the UI.
    """
    
    # Signal emitted when the dynamic display message changed.
    messageChanged = pyqtSignal()

    # Signal triggered when new things are found.
    thingsChanged = pyqtSignal()

    # Signal triggered when the from collection state changed.
    isFromCollectionChanged = pyqtSignal()

    # Signal triggered when user name changed.
    userNameChanged = pyqtSignal()

    # Signal triggered when the querying state changed.
    queryingStateChanged = pyqtSignal()

    # Signal triggered when the active thing changed.
    activeThingChanged = pyqtSignal()

    # Signal triggered when the active thing files changed.
    activeThingFilesChanged = pyqtSignal()

    # Signal triggered when a file has started or stopped downloading.
    downloadingStateChanged = pyqtSignal()

    def __init__(self, extension: "ThingiverseExtension", parent=None):
        super().__init__(parent)
        self._extension = extension  # type: ThingiverseExtension
        
        # Hold the dynamic display message.
        self._message = None  # type: Optional[str]

        # Hold the things found in query results.
        self._things = []  # type: List[JSONObject]
        self._query = ""  # type: str
        self._query_page = 1  # type: int
        self._is_from_collection = False  # type: bool

        # Hold the thing and thing files that we currently see the details of.
        self._thing_details = None  # type: Optional[JSONObject]
        self._thing_files = []  # type: List[JSONObject]
        self._is_downloading = False  # type: bool

        # The API client that we do all calls to Thingiverse with.
        self._api_client = ThingiverseApiClient()  # type: ThingiverseApiClient

        # Register plugins settings.
        CuraApplication.getInstance().getPreferences().preferenceChanged.connect(self._onPreferencesChanged)
        self._user_name = self._initSettings(Settings.SETTINGS_USER_NAME_PREFERENCES_KEY)

        # List of supported file types.
        self._supported_file_types = []  # type: List[str]

    def updateSupportedFileTypes(self) -> None:
        """ Refresh the available file types (triggered when plugin window is loaded). """
        supported_file_types = CuraApplication.getInstance().getMeshFileHandler().getSupportedFileTypesRead()
        self._supported_file_types = list(supported_file_types.keys())
        
    @pyqtProperty(str, notify=messageChanged)
    def message(self) -> str:
        """
        Get the dynamic display message.
        """
        return self._message or ""

    @pyqtSlot(name="openSettings")
    def openSettings(self) -> None:
        """ Open the settings window. """
        if not self._extension:
            return
        self._extension.showSettingsWindow()

    @pyqtProperty(str, notify=userNameChanged)
    def userName(self) -> str:
        """
        Get the configured username for viewing collections and likes.
        :return: The username.
        """
        return self._user_name or ""

    @pyqtSlot(str, str, name="saveSetting")
    def setSetting(self, name: str, value: str) -> None:
        """
        Change the value of a setting.
        :param name: The name of the setting.
        :param value: The new value.
        """
        preference_key = "{}/{}".format(Settings.PREFERENCE_KEY_BASE, name)
        CuraApplication.getInstance().getPreferences().setValue(preference_key, value)
        if preference_key == Settings.SETTINGS_USER_NAME_PREFERENCES_KEY:
            self.userNameChanged.emit()

    @pyqtProperty("QVariantList", notify=thingsChanged)
    def things(self) -> List[Dict[str, any]]:
        """
        Get a list of found things. Updated when performing a search.
        :return: The things.
        """
        return [thing.__dict__ for thing in self._things]

    @pyqtProperty(bool, notify=isFromCollectionChanged)
    def isFromCollection(self) -> bool:
        """
        Whether the current list of results is a user collection or not.
        :return: True if from collection, False otherwise.
        """
        return self._is_from_collection

    @pyqtProperty(bool, notify=queryingStateChanged)
    def isQuerying(self) -> bool:
        """
        Whether we're currently waiting for an API response or not.
        :return: True if waiting, False otherwise.
        """
        return self._is_querying

    @pyqtProperty("QVariant", notify=activeThingChanged)
    def activeThing(self) -> Dict[str, any]:
        """
        Get the current active thing details.
        :return: The thing.
        """
        return self._thing_details.__dict__ if self._thing_details else None

    @pyqtProperty("QVariantList", notify=activeThingFilesChanged)
    def activeThingFiles(self) -> List[Dict[str, any]]:
        """
        Get the current active thing files.
        :return: The thing files.
        """
        return [files.__dict__ for files in self._thing_files]

    @pyqtProperty(bool, notify=activeThingChanged)
    def hasActiveThing(self) -> bool:
        """
        Whether there is currently a thing active to show or not.
        :return: True when there is an active thing, false otherwise.
        """
        return bool(self._thing_details)

    @pyqtProperty(bool, notify=downloadingStateChanged)
    def isDownloading(self) -> bool:
        """
        Whether there is currently a download in progress or not.
        :return: True if currently downloading, false otherwise.
        """
        return self._is_downloading

    @pyqtSlot(str, name="search")
    def search(self, search_term: str) -> None:
        """
        Search for things by search term.
        :param search_term: What to search for.
        """
        self._executeQuery("search/{}".format(search_term))

    @pyqtSlot(name="getLiked")
    def getLiked(self) -> None:
        """
        Get the current user's liked things.
        """
        if not self._checkUserNameConfigured():
            return
        self._executeQuery("users/{}/likes".format(self._user_name))

    @pyqtSlot(name="getCollections")
    def getCollections(self) -> None:
        """
        Get the current user's collections.
        """
        if not self._checkUserNameConfigured():
            return
        self._executeQuery("users/{}/collections".format(self._user_name))

    @pyqtSlot(name="getMyThings")
    def getMyThings(self) -> None:
        """
        Get the current user's published Things.
        """
        if not self._checkUserNameConfigured():
            return
        self._executeQuery("users/{}/things".format(self._user_name))

    @pyqtSlot(name="getMakes")
    def getMakes(self) -> None:
        """
        Get the current user's made Things.
        """
        if not self._checkUserNameConfigured():
            return
        self._executeQuery("users/{}/copies".format(self._user_name))

    @pyqtSlot(name="getPopular")
    def getPopular(self) -> None:
        """
        Get the most popular things.
        The result is async and will be populated in self._things.
        """
        self._executeQuery("popular")

    @pyqtSlot(name="getFeatured")
    def getFeatured(self) -> None:
        """
        Get the featured things.
        The result is async and will be populated in self._things.
        """
        self._executeQuery("featured")

    @pyqtSlot(name="getNewest")
    def getNewest(self) -> None:
        """
        Get the newest things.
        The result is async and will be populated in self._things.
        """
        self._executeQuery("newest")

    @pyqtSlot(name="addPage")
    def addPage(self) -> None:
        """
        Append search Thing list with the next page of results.
        The search is done async and the result will be populated in self._things.
        """
        self._query_page += 1
        self._executeQuery()

    @pyqtSlot(int, name="showCollectionDetails")
    def showCollectionDetails(self, collection_id: int) -> None:
        """
        Get and show the details of a single collection.
        :param collection_id: The ID of the collection.
        """
        self._executeQuery("collections/{}/things".format(collection_id), is_from_collection=True)

    @pyqtSlot(int, name="showThingDetails")
    def showThingDetails(self, thing_id: int) -> None:
        """
        Get and show the details of a single thing.
        :param thing_id: The ID of the thing.
        """
        self._api_client.getThing(thing_id, self._onThingDetailsFinished, on_failed=self._onRequestFailed)
        self._api_client.getThingFiles(thing_id, self._onThingFilesFinished, on_failed=self._onRequestFailed)

    @pyqtSlot(name="hideThingDetails")
    def hideThingDetails(self) -> None:
        """
        Remove the thing details. This hides the detail page in the UI.
        """
        self._thing_details = None
        self.activeThingChanged.emit()

    @pyqtSlot(int, str, name="downloadThingFile")
    def downloadThingFile(self, file_id: int, file_name: str) -> None:
        """
        Download and load a thing file by it's ID.
        The downloaded object will be placed on the build plate.
        :param file_id: The ID of the file.
        :param file_name: The name of the file.
        """
        self._is_downloading = True
        self.downloadingStateChanged.emit()
        self._api_client.downloadThingFile(file_id, lambda data: self._onDownloadFinished(data, file_name))

    def loadDynamicDisplayMessage(self):
        """
        Get the dynamic display message.
        """
        self._api_client.getMessage(self._onMessage)

    def _executeQuery(self, new_query: Optional[str] = None, is_from_collection: Optional[bool] = False) -> None:
        """
        Internal function to query the API for things.
        :param new_query: Perform a new query instead of adding a new page to the existing one.
        :param is_from_collection: Specifies whether the resulting Things are part of a collection or not
        """
        if new_query:
            self._query = new_query
            self._clearSearchResults()
            self._query_page = 1
        if self._is_from_collection != is_from_collection:
            self._is_from_collection = is_from_collection
            self.isFromCollectionChanged.emit()
        self._is_querying = True
        self.queryingStateChanged.emit()
        self._api_client.get(self._query, page=self._query_page, on_finished=self._onQueryFinished,
                             on_failed=self._onRequestFailed)

    def _onThingDetailsFinished(self, thing: JSONObject) -> None:
        """
        Callback for receiving thing details on.
        :param thing: The thing.
        """
        self._thing_details = thing
        self.activeThingChanged.emit()

    def _onThingFilesFinished(self, thing_files: List[JSONObject]) -> None:
        """
        Callback for receiving a list of thing files on. Filtered on supported file types of Cura.
        :param thing_files: The thing files.
        """
        self._thing_files = [f for f in thing_files if pathlib.Path(f.name).suffix.lower().strip(".")
                             in self._supported_file_types]
        self.activeThingFilesChanged.emit()

    def _onDownloadFinished(self, file_bytes: bytes, file_name: str) -> None:
        """
        Callback to receive the file on.
        :param file_bytes: The file as bytes.
        :param file_name: The file name.
        """
        file = tempfile.NamedTemporaryFile(suffix=file_name, delete=False)
        file.write(file_bytes)
        file.close()
        CuraApplication.getInstance().readLocalFile(QUrl().fromLocalFile(file.name))
        self._is_downloading = False
        self.downloadingStateChanged.emit()

    def _onQueryFinished(self, things: List[JSONObject]) -> None:
        """
        Callback for receiving search results on.
        :param things: The found things.
        """
        self._is_querying = False
        self.queryingStateChanged.emit()
        self._things.extend(things)
        self.thingsChanged.emit()

    def _onMessage(self, response: JSONObject) -> None:
        """
        Callback for the dynamic display message.
        :param response: The message response.
        """
        self._message = str(response.message)
        self.messageChanged.emit()

    def _clearSearchResults(self) -> None:
        """
        Clear all Thing search results.
        """
        self._things = []
        self._query_page = 1
        self.hideThingDetails()
        self.thingsChanged.emit()

    @staticmethod
    def _onRequestFailed(error: Optional[JSONObject] = None) -> None:
        """
        Callback for when a request failed.
        :param error: An optional error object that was returned by the Thingiverse API.
        """
        mb = QMessageBox()
        mb.setIcon(QMessageBox.Critical)
        mb.setWindowTitle("Oh no!")
        error_message = "Unknown"
        if error:
            error_message = error.error if hasattr(error, "error") else error
        mb.setText("Thingiverse returned an error: {}.".format(error_message))
        mb.setDetailedText(str(error.__dict__) if error else "")
        mb.exec()

    @staticmethod
    def _initSettings(key: str, default_value: Optional[str] = None) -> str:
        """
        Initialize plugin settings in Cura's preferences.
        :param key: Setting key.
        :param default_value: Setting default value.
        :return: Setting value (or default value).
        """
        preferences = CuraApplication.getInstance().getPreferences()
        preferences.addPreference(key, default_value)
        return preferences.getValue(key)

    def _checkUserNameConfigured(self) -> bool:
        """
        Checks if the username setting was configured and open the settings window if it was not.
        :return:
        """
        if not self._user_name or self._user_name == "":
            self.openSettings()
            return False
        return True

    def _onPreferencesChanged(self, name: str) -> None:
        """
        Called when a preference was changed.
        :param name: Name of the changed preference
        """
        if name == Settings.SETTINGS_USER_NAME_PREFERENCES_KEY:
            self._user_name = CuraApplication.getInstance().getPreferences().getValue(
                    Settings.SETTINGS_USER_NAME_PREFERENCES_KEY)
            self.userNameChanged.emit()
