# Copyright (c) 2020 Chris ter Beke.
# Thingiverse plugin is released under the terms of the LGPLv3 or higher.
from typing import List, Callable, Any, Optional

from PyQt5.QtNetwork import QNetworkRequest

from ....Settings import Settings
from ...PreferencesHelper import PreferencesHelper
from ...api.AbstractApiClient import AbstractApiClient
from ...api.ApiHelper import ApiHelper
from ...api.JsonObject import JsonObject


class ThingiverseApiClient(AbstractApiClient):
    """ Client for interacting with the Thingiverse API. """

    def __init__(self):
        super().__init__()
        PreferencesHelper.initSetting(Settings.THINGIVERSE_USER_NAME_PREFERENCES_KEY, "")

    @property
    def available_views(self) -> List[str]:
        return ["My Likes", "My Collections", "My Things", "My Makes", "Popular", "Featured", "Newest"]

    @property
    def user_id(self):
        return PreferencesHelper.getSettingValue(Settings.THINGIVERSE_USER_NAME_PREFERENCES_KEY)

    def getThingsFromCollectionQuery(self, collection_id: str) -> str:
        return "collections/{}/things".format(collection_id)

    def getThingsBySearchQuery(self, search_terms: str) -> str:
        return "search/{}/?sort=relevent".format(search_terms)
    
    def getThingsLikedByUserQuery(self) -> str:
        return "users/{}/likes".format(self.user_id)

    def getThingsByUserQuery(self) -> str:
        return "users/{}/things".format(self.user_id)

    def getThingsMadeByUserQuery(self) -> str:
        return "users/{}/copies".format(self.user_id)

    def getPopularThingsQuery(self) -> str:
        return "popular"

    def getFeaturedThingsQuery(self) -> str:
        return "featured"

    def getNewestThingsQuery(self) -> str:
        return "newest"

    def getCollections(self, on_finished: Callable[[List[JsonObject]], Any],
                       on_failed: Optional[Callable[[JsonObject], Any]]) -> None:
        url = "{}/users/{}/collections".format(self._root_url, self.user_id)
        reply = self._manager.get(self._createEmptyRequest(url))
        self._addCallback(reply, on_finished, on_failed)

    def getThings(self, query: str, page: int, on_finished: Callable[[List[JsonObject]], Any],
                  on_failed: Optional[Callable[[JsonObject], Any]] = None) -> None:
        url = "{}/{}?per_page={}&page={}".format(self._root_url, query, Settings.PER_PAGE, page)
        reply = self._manager.get(self._createEmptyRequest(url))
        self._addCallback(reply, on_finished, on_failed, parser=ApiHelper.parseReplyAsListOfThings)

    def getThing(self, thing_id: int, on_finished: Callable[[JsonObject], Any],
                 on_failed: Optional[Callable[[JsonObject], Any]] = None) -> None:
        url = "{}/things/{}".format(self._root_url, thing_id)
        reply = self._manager.get(self._createEmptyRequest(url))
        self._addCallback(reply, on_finished, on_failed)

    def getThingFiles(self, thing_id: int, on_finished: Callable[[List[JsonObject]], Any],
                      on_failed: Optional[Callable[[JsonObject], Any]] = None) -> None:
        url = "{}/things/{}/files".format(self._root_url, thing_id)
        reply = self._manager.get(self._createEmptyRequest(url))
        self._addCallback(reply, on_finished, on_failed)

    def downloadThingFile(self, file_id: int, file_name: str, on_finished: Callable[[bytes], Any]) -> None:
        url = "{}/files/{}/download".format(self._root_url, file_id)
        reply = self._manager.get(self._createEmptyRequest(url))
        self._addCallback(reply, on_finished, parser=ApiHelper.parseReplyAsBytes)

    @property
    def _root_url(self):
        return "https://api.thingiverse.com"

    def _setAuth(self, request: QNetworkRequest) -> None:
        request.setRawHeader(b"Authorization", "Bearer {}".format(Settings.THINGIVERSE_API_TOKEN).encode())
