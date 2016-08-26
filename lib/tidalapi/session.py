# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Thomas Amland, Arne Svenson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import json, re, os
from types import DictionaryType
from threading import Thread
from Queue import Queue

import xbmc, xbmcgui, xbmcvfs
import requests
from requests.packages import urllib3

import config
import debug 
from .config import settings, CONST, USER_AGENTS, SubscriptionType, MusicQuality
from .models import UserInfo, SubscriptionInfo, BaseItem, ArtistItem, AlbumItem, PlaylistItem, PlaylistPosItem, TrackItem, VideoItem, SearchResult, FolderItem, PromotionItem, MusicURL, VideoURL
from .m3u8 import load as m3u8_load
from .all_strings import _T
from .metacache import MetaCache

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

#------------------------------------------------------------------------------
# Globals
#------------------------------------------------------------------------------

# This User-Agent is used !
USER_AGENT = USER_AGENTS["Mobile"]

#------------------------------------------------------------------------------
# Session Class to call TIDAL-API functions
#------------------------------------------------------------------------------

class Session(object):

    def __init__(self):
        self.is_logged_in = False
        self.metaCache = MetaCache()
        self.errorCodes = []
        # Disable OpenSSL Warnings in URLLIB3
        urllib3.disable_warnings()

    def load_session(self):
        if settings._session_id and settings._session_country and settings._user_id:
            self.session_id = settings._session_id
            self.playlist_session_id = settings._playlist_session_id
            self.country_code = settings._session_country
            self.user = User(self, user_id=settings._user_id)
            self.favorites = Favorites(self, user_id=settings._user_id)
            self.is_logged_in = True
        else:
            # No User Playlists and Favorites available (Trail Mode)
            self.session_id = ''
            self.playlist_session_id = ''
            self.country_code = ''
            self.user = TrialUser()
            self.favorites = EmptyFavorites()
            self.is_logged_in = False
            settings.cacheAlbums = False # Don't use Album Cache in Demo Mode
        if not settings.country:
            if settings._session_country:
                settings.country = settings._session_country
                config.setSetting('country', settings.country)
            else:
                # Automatic Detection of local country code
                headers = { "User-Agent": USER_AGENT,
                            "X-Tidal-Token": CONST.apiToken['BROWSER'] }
                r = requests.request('GET', urljoin(CONST.apiLocation, 'country/context'), params={'countryCode': 'WW'}, headers=headers)
                if r.ok:
                    settings.country = r.json().get('countryCode')
                    config.setSetting('country', settings.country)
            
        return self.is_logged_in

    def upgrade_settings(self):
        if settings._session_id and not settings._playlist_session_id:
            # Second Session ID is missing (first login after Upgrade from V1.2.X) !
            if settings.username and settings.password:
                # Relogin automatically
                self.login(settings.username, settings.password)
            elif self.is_logged_in:
                # New login needed
                self.logout()

    def close(self):
        if self.metaCache:
            try:
                self.metaCache.close()
            except:
                pass

    def login(self, username, password):
        if not username or not password:
            self.logout()
            return False
        url = urljoin(CONST.apiLocation, 'login/username')
        payload = {
            'username': username,
            'password': password,
        }
        # Get SessionID for Playlist-Queries (to get Video Streams in Playlists)
        headers = { "User-Agent": USER_AGENT,
                    "X-Tidal-Token": CONST.apiToken['BROWSER'] }
        r = requests.post(url, data=payload, headers=headers)
        if not r.ok:
            debug.log(r.text, xbmc.LOGERROR)
            xbmcgui.Dialog().notification(settings.addon_name, 'Error %s: %s' % (r.status_code, r.reason), xbmcgui.NOTIFICATION_ERROR)
            self.logout()
            return False
        body = r.json()
        config.setSetting('playlist_session_id', body['sessionId'])
        # Get SessionID for all other Queries with second Token to get HTTP streams and allow FLAC and Video streaming
        headers = { "User-Agent": USER_AGENT,
                    "X-Tidal-Token": CONST.apiToken['MOBILE'] }
        r = requests.post(url, data=payload, headers=headers)
        if not r.ok:
            debug.log(r.text, xbmc.LOGERROR)
            xbmcgui.Dialog().notification(settings.addon_name, 'Error %s: %s' % (r.status_code, r.reason), xbmcgui.NOTIFICATION_ERROR)
            self.logout()
            return False
        body = r.json()
        # Save Login-Session
        config.setSetting('user_id', unicode(body['userId']))
        config.setSetting('session_id', body['sessionId'])
        config.setSetting('country_code', body['countryCode'])
        if not settings.country:
            config.setSetting('country', body['countryCode'])
        # Determine SubscriptionType
        config.reloadConfig()
        self.load_session()
        return self.is_logged_in

    def logout(self):
        config.setSetting('user_id', '')
        config.setSetting('session_id', '')
        config.setSetting('playlist_session_id', '')
        config.setSetting('country_code', '')
        config.reloadConfig()
        self.load_session()
        return not self.is_logged_in

    def getUserInfo(self):
        """ Returns true if current session is valid, false otherwise. """
        if not self.is_logged_in or self.user is None or not self.user.id or not self.session_id:
            return None
        userInfo = None
        r = self.request(method='GET', path='users/%s' % self.user.id)
        if r.ok:
            userInfo = UserInfo(**r.json())
            r = self.request(method='GET', path='users/%s/subscription' % self.user.id)
            if r.ok:
                userInfo.subscription = SubscriptionInfo(**r.json())
        if not r.ok:
            debug.log('Error retreiving User Information for ID %s ' % self.user.id, level=xbmc.LOGERROR)
        return userInfo

    def autologin(self):
        username = config.getSetting('username')
        password = config.getSetting('password')
        if not username or not password:
            # Ask for username/password
            dialog = xbmcgui.Dialog()
            username = dialog.input(_T('Username'))
            if not username:
                return
            password = dialog.input(_T('Password'), option=xbmcgui.ALPHANUM_HIDE_INPUT)
            if not password:
                return
        if self.login(username, password):
            if not config.getSetting('username') or not config.getSetting('password'):
                # Ask about remembering username/password
                dialog = xbmcgui.Dialog()
                if dialog.yesno(CONST.addon_name, _T('Remember login details?')):
                    config.setSetting('username', username)
                    config.setSetting('password', password)

    def request(self, method, path, params=None, data=None, headers=None):
        request_params = {
            'countryCode': settings.country if settings.country else self.country_code
        }
        if params:
            request_params.update(params)
        url = urljoin(CONST.apiLocation, path)
        if headers == None:
            headers = { "User-Agent": USER_AGENT }
        else:
            headers["User-Agent"] = USER_AGENT
        if self.is_logged_in:
            if path.find('playlist') >= 0:
                headers['X-Tidal-SessionId'] = self.playlist_session_id
            else:
                headers['X-Tidal-SessionId'] = self.session_id
        else:
            # Request with Preview-Token
            request_params.update({'token': CONST.apiToken['PREVIEW']})
        if settings.log_details == 2:
            debug.log("Request: %s" % url, xbmc.LOGSEVERE)
        r = requests.request(method, url, params=request_params, data=data, headers=headers)
        if settings.log_details in [1, 2]:
            debug.log("Answer : %s" % r.url, xbmc.LOGDEBUG)
        if not r.ok:
            debug.log(r.url, xbmc.LOGERROR)
            try:
                msg = r.reason
                json_obj = r.json()
                msg = json_obj.get('userMessage')
            except:
                pass
            if r.text:
                debug.log(r.text, xbmc.LOGERROR)
            elif msg:
                debug.log(msg, xbmc.LOGERROR)
            if not r.status_code in self.errorCodes:
                self.errorCodes.append(r.status_code)
                xbmcgui.Dialog().notification('%s Error %s' % (settings.addon_name, r.status_code), msg, xbmcgui.NOTIFICATION_ERROR)
        if r.content and settings.log_details == 3:
            # Only in Detail-Log because the JSon-Dump costs a lot CPU time
            try:
                debug.log("response: %s" % json.dumps(r.json(), indent=4), xbmc.LOGSEVERE)
            except:
                debug.log("response has no json object", xbmc.LOGWARNING)
        return r

    def get_user(self, user_id):
        return self._map_request('users/%s' % user_id, ret='user')

    def get_artist(self, artist_id):
        return self._map_request('artists/%s' % artist_id, ret='artist')

    def get_artist_albums(self, artist_id):
        return self._map_request('artists/%s/albums' % artist_id, params={'limit': 999}, ret='albums')

    def get_artist_albums_ep_singles(self, artist_id):
        return self._map_request('artists/%s/albums' % artist_id, params={'filter': 'EPSANDSINGLES', 'limit': settings.top_limit}, ret='albums')

    def get_artist_albums_other(self, artist_id):
        return self._map_request('artists/%s/albums' % artist_id, params={'filter': 'COMPILATIONS', 'limit': settings.top_limit}, ret='albums')

    def get_artist_videos(self, artist_id):
        return self._map_request('artists/%s/videos' % artist_id, params={'limit': 999}, ret='videos')

    def get_artist_top_tracks(self, artist_id):
        return self._map_request('artists/%s/toptracks' % artist_id, params={'limit': settings.top_limit}, ret='tracks')

    def cleanup_text(self, text):
        clean_text = re.sub(r"\[.*\]", ' ', text)         # Remove Tags: [wimpLink ...] [/wimpLink]
        clean_text = re.sub(r"<br.>", ' ', clean_text)    # Remove Tags: <br/>
        return clean_text
    
    def get_artist_bio(self, artist_id):
        bio = self.request('GET', 'artists/%s/bio' % artist_id, params={'includeImageLinks': 'false'}).json()
        if bio.get('summary'):
            bio['summary'] = self.cleanup_text(bio.get('summary'))
        if bio.get('text'):
            bio['text'] = self.cleanup_text(bio.get('text'))
        return bio

    def get_artist_similar(self, artist_id):
        return self._map_request('artists/%s/similar' % artist_id, params={'limit': 999}, ret='artists')

    def get_artist_radio(self, artist_id):
        return self._map_request('artists/%s/radio' % artist_id, params={'limit': settings.top_limit}, ret='tracks')

    def get_artist_playlists(self, artist_id):
        return self._map_request('artists/%s/playlistscreatedby' % artist_id, ret='playlists')

    def get_album(self, album_id, bypassBuffer=False):
        if not bypassBuffer:
            # Get Album from Buffer
            json_obj = self.metaCache.fetch('album', album_id)
            if json_obj and 'artist' in json_obj:
                return self._parse_album(json_obj)
        # Load Album from TIDAL
        album = self._map_request('albums/%s' % album_id, ret='album')
        return album

    def get_album_json_thread(self):
        try:
            while not xbmc.abortRequested and not self.abortAlbumThreads:
                try:
                    album_id = self.albumQueue.get_nowait()
                except:
                    break
                debug.log('Requesting Album ID %s' % album_id, level=xbmc.LOGSEVERE)
                r = self.request(method='GET', path='albums/%s' % album_id)
                if r.ok:
                    json_obj = r.json()
                    if json_obj:
                        self.jsonQueue.put(json_obj)
                else:
                    if r.status_code == 429 and not self.abortAlbumThreads:
                        self.abortAlbumThreads = True
                        debug.log('Too many requests. Aborting Workers ...', xbmc.LOGERROR)
                        skipCount = 0
                        while not xbmc.abortRequested:
                            try:
                                album_id = self.albumQueue.get_nowait()
                                skipCount += 1
                            except:
                                break
                        if skipCount > 0:
                            debug.log('Skipped %s albums.' % skipCount, xbmc.LOGERROR)
                            xbmcgui.Dialog().notification('Album Cache Error', _T('%s Albums not loaded') % skipCount, xbmcgui.NOTIFICATION_ERROR)
        except Exception, e:
            debug.logException(e)

    def update_albums_in_tracklist(self, items):
        if settings.cacheAlbums:
            # Step 1: Read all available Albums from Cache
            album_ids = []
            missing = []
            self.abortAlbumThreads = False
            for item in items:
                if isinstance(item, TrackItem) and item._playable and not item.album.releaseDate:
                    # Try to read Album from Cache
                    json_obj = self.metaCache.fetch('album', item.album.id)
                    if json_obj:
                        item.album = self._parse_album(json_obj)
                    else:
                        missing.append(item)
                        if not item.album.id in album_ids:
                            album_ids.append(item.album.id)
            if len(album_ids) > 5 and settings.max_http_requests > 1:
                # Step 2: Load JSon-Data from all missing Albums
                self.albumQueue = Queue()
                for album_id in album_ids:
                    self.albumQueue.put(album_id)
                self.jsonQueue = Queue()
                debug.log('Starting Threads to load Albums')
                runningThreads = []
                while len(runningThreads) < settings.max_http_requests:
                    try:
                        worker = Thread(target=self.get_album_json_thread)
                        worker.start()
                        runningThreads.append(worker)
                    except Exception, e:
                        debug.logException(e)
                debug.log('Waiting until all Threads are terminated')
                for worker in runningThreads:
                    worker.join(20)
                    if worker.isAlive():
                        debug.log('Worker %s is still running ...' % worker.ident, xbmc.LOGWARNING)
                debug.log('Write %s Albums into the MetaCache' % self.jsonQueue.qsize())
                album_ids = []
                while not xbmc.abortRequested:
                    try:
                        json_obj = self.jsonQueue.get_nowait()
                        if 'id' in json_obj:
                            album_ids.append(json_obj.get('id'))
                            self.metaCache.insertAlbumJson(json_obj)
                    except:
                        break
            if missing:
                debug.log('Putting %s from %s missing Albums into TrackItems' % (len(album_ids), len(missing)))
            # Step 3: Fill missing Albums into the TrackItems
            if 429 in self.errorCodes: self.errorCodes.remove(429)
            for item in missing:
                if 429 in self.errorCodes:
                    break # Abort if "Too Many Requests" occurs
                if item.album and item._playable and item.album.id in album_ids:
                    album = self.get_album(item.album.id)
                    if album:
                        item.album = album

    def get_album_tracks(self, album_id):
        items = self._map_request('albums/%s/tracks' % album_id, ret='tracks')
        album = self.get_album(album_id, bypassBuffer=True)
        if album:
            for item in items:
                item.album = album
        return items

    def get_playlist(self, playlist_id):
        return self._map_request('playlists/%s' % playlist_id, ret='playlist')

    def get_playlist_items(self, playlist_id=None, playlist=None, ret='playlistitems'):
        if not playlist:
            playlist = self.get_playlist(playlist_id)
            if not playlist: return []
        # Don't read empty playlists
        if playlist.numberOfTracks == 0 and playlist.numberOfVideos == 0:
            debug.log('Skipping empty Playlist "%s"' % playlist.title) 
            return []
        itemCount = playlist.numberOfTracks + playlist.numberOfVideos
        offset = 0
        result = []
        if playlist.numberOfVideos <= 0 or ret.startswith('track'):
            debug.log('Loading %s Tracks of UserPlaylist "%s"' % (itemCount, playlist.title))
            items = self._map_request('playlists/%s/tracks' % playlist.id, params={'limit': 9999}, ret='baseitems' if ret.startswith('baseitem') else 'tracks')
            if items and len(items) > 0:
                result += items
        else:
            debug.log('Loading %s Tracks and %s Videos of UserPlaylist "%s"' % (playlist.numberOfTracks, playlist.numberOfVideos, playlist.title))
            while offset < itemCount:
                items = self._map_request('playlists/%s/items' % playlist.id, params={'limit': 100, 'offset': offset}, ret='baseitems' if ret.startswith('baseitem') else 'playlistitems')
                if items and len(items) > 0:
                    result += items
                offset += 100
        if settings.cachePlaylists and playlist.type == 'USER' and ret.startswith('playlistitem'):
            # Update User Playlist in the Cache
            self.metaCache.insertUserPlaylist(playlist.id, playlist.title, [item.id for item in result])
        if not ret.startswith('baseitem'):
            # Reset the track numbers
            track_no = 0
            for item in result:
                if isinstance(item, PlaylistPosItem):
                    item._playlist = playlist
                    item._playlistPos = track_no
                    if playlist.type == 'USER': 
                        item._user_playlist_id = playlist.id
                        item._user_playlist_tack_no = track_no
                track_no += 1
                if isinstance(item, TrackItem):
                    item.volumeNumber = 0
                    item.trackNumber = track_no
            if ret.startswith('track'):
                result = [item for item in result if isinstance(item, TrackItem)]
            elif ret.startswith('video'):
                result = [item for item in result if isinstance(item, VideoItem)]
        if ret.startswith('playlistitem') or ret.startswith('track'):
            self.update_albums_in_tracklist(result)
        return result

    def get_folder_items(self, group):
        items = map(self._parse_folder, self.request('GET', group).json())
        for item in items:
            item._group = group
            if settings.folderColor:
                item._labelColor = settings.folderColor
        return items

    def get_folder_content(self, group, path, content_type, offset=0, limit=0):
        params = {'limit': limit if limit > 0 else settings.page_size}
        if offset > 0:
            params.update({'offset': offset})
        items = self._map_request('/'.join([group, path, content_type]), params=params, ret=content_type)
        if content_type == 'tracks':
            self.update_albums_in_tracklist(items)
        track_no = 0
        for item in items:
            track_no += 1
            item._forceArtistInLabel = True
            item.trackNumber = track_no + offset
        return items

    def get_promotions(self, group=None):
        params = {'limit': 100}
        if group:
            params.update({'group': group,
                           'clientType': 'BROWSER',
                           'subscriptionType': 'HIFI'})
        json_obj = self.request('GET', 'promotions', params=params).json()
        items = json_obj['items']
        return [self._parse_promotion(item) for item in items]

    def get_track(self, track_id, withAlbum=False):
        item = self._map_request('tracks/%s' % track_id, ret='track')
        if item.album and (withAlbum or settings.cacheAlbums):
            album = self.get_album(item.album.id)
            if album:
                item.album = album
            # Fill/repair track/volume numbers
            if item.trackNumber == 0:
                item.trackNumber = 1
            elif item.trackNumber > item.album.numberOfTracks:
                item.trackNumber = item.album.numberOfTracks
            if item.volumeNumber == 0:
                item.volumeNumber = 1
            elif item.volumeNumber > item.album.numberOfVolumes:
                item.volumeNumber = item.album.numberOfVolumes
        return item

    def get_track_radio(self, track_id):
        items = self._map_request('tracks/%s/radio' % track_id, params={'limit': settings.top_limit}, ret='tracks')
        self.update_albums_in_tracklist(items)
        return items

    def get_recommended_items(self, item_type, item_id):
        items = self._map_request('%s/%s/recommendations' % (item_type, item_id), params={'limit': settings.top_limit}, ret=item_type)
        if item_type == 'tracks':
            self.update_albums_in_tracklist(items)
        return items
    
    def get_video(self, video_id):
        return self._map_request('videos/%s' % video_id, ret='video')

    def _map_request(self, url, method='GET', params=None, data=None, headers=None, ret=None):
        r = self.request(method, url, params=params, data=data, headers=headers)
        if not r.ok:
            return [] if ret.endswith('s') else None
        json_obj = r.json()
        if 'items' in json_obj:
            items = json_obj.get('items')
            result = []
            offset = 0
            if params and 'offset' in params:
                offset = params.get('offset')
            itemPosition = offset
            try:
                numberOfItems = int('0%s' % json_obj.get('totalNumberOfItems')) if 'totalNumberOfItems' in json_obj else 9999
            except:
                numberOfItems = 9999
            for item in items:
                retType = ret
                if 'type' in item and ret.startswith('playlistitem'):
                    retType = item['type']
                if 'item' in item:
                    item = item['item']
                elif 'track' in item and ret.startswith('track'):
                    item = item['track']
                elif 'video' in item and ret.startswith('video'):
                    item = item['video']
                nextItem = self._parse_one_item(item, retType)
                if isinstance(nextItem, BaseItem):
                    nextItem._itemPosition = itemPosition
                    nextItem._offset = offset
                    nextItem._totalNumberOfItems = numberOfItems
                result.append(nextItem)
                itemPosition = itemPosition + 1
        else:
            result = self._parse_one_item(json_obj, ret)
            if isinstance(result, PlaylistItem):
                # Get ETag of Playlist which must be used to add/remove entries of playlists
                try: 
                    result._etag = r.headers._store['etag'][1]
                    debug.log('ETag of Playlist "%s" is "%s"' % (result.title, result._etag))
                except:
                    debug.log('No ETag in response header for playlist "%s" (%s)' % (json_obj.get('title'), json_obj.get('id')), level=xbmc.LOGERROR)
        return result

    def get_music_url(self, track_id, quality=None):
        params = { }
        if self.is_logged_in:
            url = 'tracks/%s/streamUrl' % track_id
            if quality:
                params["soundQuality"] = quality
            else:
                params['soundQuality'] = settings.musicQuality
            if params["soundQuality"] in [MusicQuality.lossless, MusicQuality.lossless_hd] and settings.subscription_type != SubscriptionType.hifi:
                # Switching down to HIGH quality
                params["soundQuality"] = MusicQuality.high
                xbmcgui.Dialog().notification(_T('Attention'), _T('Switching down to HIGH quality'), xbmcgui.NOTIFICATION_WARNING)
                settings.musicQuality = MusicQuality.high
                config.setSetting("music_quality", '1')
        else:
            url = 'tracks/%s/previewurl' % track_id               
        r = self.request('GET', url, params)
        if not r.ok:
            return None
        media = MusicURL(**r.json()) 
        if not self.is_logged_in:
            # Mark for Trial Mode
            media.soundQuality = MusicQuality.trial
        debug.log("Play Track: Quality=%s, URL=%s" % (media.soundQuality, media._stream_url), xbmc.LOGNOTICE)
        return media

    def get_video_url(self, video_id, maxHeight=0):
        params = { }
        if self.is_logged_in:
            r = self.request('GET', 'videos/%s/streamUrl' % video_id, params)
        else:
            r = self.request('GET', 'videos/%s/previewurl' % video_id, params)
        if not r.ok:
            return None
        media = VideoURL(**r.json())
        media._height = 0
        media._stream_url = media.url
        if maxHeight <= 0:
            maxHeight = settings.maxVideoHeight
            for slowServer in settings.slowServers:            
                if slowServer and slowServer in media.url:
                    maxHeight = settings.maxVideoHeightSlowServers
                    break
        if media.url.lower().find('.m3u8') > 0:
            media._m3u8obj = m3u8_load(media.url)
            if media._m3u8obj.is_variant and not media._m3u8obj.cookies:
                # Variant Streams with Cookies have to be played without stream selection.
                # You have to change the Bandwidth Limit in Kodi Settings to select other streams !
                # Select stream with highest resolution <= maxVideoHeight
                for playlist in media._m3u8obj.playlists:
                    try:
                        width, height = playlist.stream_info.resolution
                        if height > media._height and height <= maxHeight:
                            if re.match(r'https?://', playlist.uri):
                                media._stream_url = playlist.uri
                            else:
                                media._stream_url = media._m3u8obj.base_uri + playlist.uri
                            media._width = width
                            media._height = height
                    except:
                        pass
        debug.log("PlayVideo: Quality=%sp, URL=%s" % (media._height, media._stream_url), xbmc.LOGNOTICE)
        return media

    def search(self, types, value, limit=50):
        search_types = types.upper()
        if search_types == 'ALL':
            search_types = ','.join(CONST.searchTypes)
        params = {
            'query': value,
            'limit': limit,
            'types': search_types
        }
        result = self._map_request('search', params=params, ret='search')
        if result.tracks:
            self.update_albums_in_tracklist(result.tracks)
        return result
            
#------------------------------------------------------------------------------
# Parse JSON Data into Media-Item-Objects
#------------------------------------------------------------------------------

    def _parse_one_item(self, json_obj, ret=None):
        if ret == 'album' and settings.cacheAlbums:
            # Put album json data into the Cache
            self.metaCache.insertAlbumJson(json_obj)
        parse = None
        if ret.startswith('baseitem'):
            parse = self._parse_baseitem
        elif ret.startswith('artist'):
            parse = self._parse_artist
        elif ret.startswith('album'):
            parse = self._parse_album
        elif ret.startswith('track'):
            parse = self._parse_track
        elif ret.startswith('video'):
            parse = self._parse_video
        elif ret.startswith('playlist'):
            parse = self._parse_playlist
        elif ret.startswith('folder'):
            parse = self._parse_folder
        elif ret.startswith('search'):
            parse = self._parse_search
        else:
            raise NotImplementedError()
        oneItem = parse(json_obj)
        return oneItem    
    
    def _parse_baseitem(self, json_obj):
        item = BaseItem(**json_obj)
        return item

    def _parse_artist(self, json_obj):
        artist = ArtistItem(**json_obj)
        artist._isFavorite = self.favorites.isFavoriteArtist(artist.id)
        return artist

    def _parse_all_artists(self, artist_id, json_obj):
        allArtists = []
        ftArtists = []        
        for item in json_obj:
            nextArtist = self._parse_artist(item)
            allArtists.append(nextArtist)
            if nextArtist.id <> artist_id:
                ftArtists.append(nextArtist)
        return (allArtists, ftArtists)
    
    def _parse_album(self, json_obj, artist=None):
        album = AlbumItem(**json_obj)
        if artist:
            album.artist = artist
        elif 'artist' in json_obj:            
            album.artist = self._parse_artist(json_obj['artist'])
        elif 'artists' in json_obj:            
            album.artist = self._parse_artist(json_obj['artists'][0])            
        if 'artists' in json_obj:            
            album.artists, album._ftArtists = self._parse_all_artists(album.artist.id, json_obj['artists'])
        else:
            album.artists = [album.artist]
            album._ftArtists = []
        album._isFavorite = self.favorites.isFavoriteAlbum(album.id)
        return album
    
    def _parse_playlist(self, json_obj):
        playlist = PlaylistItem(**json_obj)
        playlist._isFavorite = self.favorites.isFavoritePlaylist(playlist.id)
        return playlist
    
    def _parse_promotion(self, json_obj):
        item = PromotionItem(**json_obj)
        if item.type == 'ALBUM':
            item._isFavorite = self.favorites.isFavoriteAlbum(item.id)
        elif item.type == 'PLAYLIST':
            item._isFavorite = self.favorites.isFavoritePlaylist(item.id)
        elif item.type == 'VIDEO':
            item._isFavorite = self.favorites.isFavoriteVideo(item.id)
        return item
    
    def _parse_track(self, json_obj):
        track = TrackItem(**json_obj)
        if 'artist' in json_obj:
            track.artist = self._parse_artist(json_obj['artist'])
        elif 'artists' in json_obj:            
            track.artist = self._parse_artist(json_obj['artists'][0])            
        if 'artists' in json_obj:            
            track.artists, track._ftArtists = self._parse_all_artists(track.artist.id, json_obj['artists'])
        else:
            track.artists = [track.artist]
            track._ftArtists = []
        track.album = self._parse_album(json_obj['album'], artist=track.artist)
        track._isFavorite = self.favorites.isFavoriteTrack(track.id)
        track._user_playlists = self.user.playlistsForItem(track.id)
        if not self.is_logged_in and track.duration > 30:
            # 30 Seconds Limit in Trial Mode
            track.duration = 30
        return track
    
    def _parse_video(self, json_obj):
        video = VideoItem(**json_obj)
        if 'artist' in json_obj:
            video.artist = self._parse_artist(json_obj['artist'])
        if 'artists' in json_obj:            
            video.artists, video._ftArtists = self._parse_all_artists(video.artist.id, json_obj['artists'])
            if not 'artist' in json_obj and len(video.artists) > 0:
                video.artist = video.artists[0]
        else:
            video.artists = [video.artist]
            video._ftArtists = []
        video._isFavorite = self.favorites.isFavoriteVideo(video.id)
        video._user_playlists = self.user.playlistsForItem(video.id)
        if not self.is_logged_in and video.duration > 30:
            # 30 Seconds Limit in Trial Mode
            video.duration = 30
        return video
    
    def _parse_folder(self, json_obj):
        return FolderItem(**json_obj)

    def _parse_search(self, json_obj):
        result = SearchResult()
        if 'artists' in json_obj:
            result.artists = [self._parse_artist(json) for json in json_obj['artists']['items']]
        if 'albums' in json_obj:
            result.albums = [self._parse_album(json) for json in json_obj['albums']['items']]
        if 'tracks' in json_obj:
            result.tracks = [self._parse_track(json) for json in json_obj['tracks']['items']]
        if 'playlists' in json_obj:
            result.playlists = [self._parse_playlist(json) for json in json_obj['playlists']['items']]
        if 'videos' in json_obj:
            result.videos = [self._parse_video(json) for json in json_obj['videos']['items']]
        return result

#------------------------------------------------------------------------------
# Class to work with user favorites
#------------------------------------------------------------------------------

# Dummy Favorites for Trial Mode
class EmptyFavorites(object):

    def load_all(self): pass
    def delete_cache(self): pass
    def add_artist(self, artist_id): return False
    def remove_artist(self, artist_id): return False
    def add_album(self, album_id): return False
    def remove_album(self, album_id): return False
    def add_playlist(self, playlist_id): return False
    def remove_playlist(self, playlist_id): return False
    def add_track(self, track_id): return False
    def remove_track(self, track_id): return False
    def add_video(self, video_id): return False
    def remove_video(self, video_id): return False
    def load_artists(self, onlyBaseItems=False): return []
    def isFavoriteArtist(self, artist_id): return False
    def load_albums(self, onlyBaseItems=False): return []
    def isFavoriteAlbum(self, album_id): return False
    def load_playlists(self, onlyBaseItems=False): return []
    def isFavoritePlaylist(self, playlist_id): return False
    def load_tracks(self, onlyBaseItems=False): return []
    def isFavoriteTrack(self, track_id): return False
    def load_videos(self, onlyBaseItems=False): return []
    def isFavoriteVideo(self, video_id): return False
    def do_action(self, action, item, forceConfirm=False): return False
    def export_ids(self, what, filename, action, remove=None): return False
    def import_ids(self, what, filename, action): return

# The 'Real' User Favorites
class Favorites(EmptyFavorites):

    favoArtists = None
    favoAlbums = None
    favoTracks = None
    favoPlaylists = None
    favoVideos = None
    
    def __init__(self, session, user_id):
        self._session = session
        self._base_url = 'users/%s/favorites' % user_id
        if not settings.cacheFavorites:
            self.favoArtists = []
            self.favoAlbums = []
            self.favoTracks = []
            self.favoPlaylists = []
            self.favoVideos = []

    def load_all(self):
        self.favoArtists = []
        self.favoAlbums = []
        self.favoTracks = []
        self.favoPlaylists = []
        self.favoVideos = []
        r = self._session.request('GET', self._base_url + '/ids')
        if r.ok:
            json_obj = r.json()
            if 'ARTIST' in json_obj:
                self.favoArtists = json_obj.get('ARTIST')
                debug.log('MetaCache: Inserting %s Favorite Artists' % len(self.favoArtists))
                self._session.metaCache.insert('favorites', 'artists', data=self.favoArtists, overwrite=True)
            if 'ALBUM' in json_obj:
                self.favoAlbums = json_obj.get('ALBUM')
                debug.log('MetaCache: Inserting %s Favorite Albums' % len(self.favoAlbums))
                self._session.metaCache.insert('favorites', 'albums', data=self.favoAlbums, overwrite=True)
            if 'PLAYLIST' in json_obj:
                self.favoPlaylists = json_obj.get('PLAYLIST')
                debug.log('MetaCache: Inserting %s Favorite Playlists' % len(self.favoPlaylists))
                self._session.metaCache.insert('favorites', 'playlists', data=self.favoPlaylists, overwrite=True)
            if 'TRACK' in json_obj:
                self.favoTracks = json_obj.get('TRACK')
                debug.log('MetaCache: Inserting %s Favorite Tracks' % len(self.favoTracks))
                self._session.metaCache.insert('favorites', 'tracks', data=self.favoTracks, overwrite=True)
            if 'VIDEO' in json_obj:
                self.favoVideos = json_obj.get('VIDEO')
                debug.log('MetaCache: Inserting %s Favorite Videos' % len(self.favoVideos))
                self._session.metaCache.insert('favorites', 'videos', data=self.favoVideos, overwrite=True)

    def delete_cache(self):
        try:
            self._session.metaCache.deleteAll('favorites')
        except Exception, e:
            debug.logException(e)            

    def add_artist(self, artist_id):
        if isinstance(artist_id, basestring):
            ids = artist_id
        else:
            ids = ','.join(artist_id)
        ok = self._session.request('POST', self._base_url + '/artists', data={'artistId': ids}).ok
        if ok:
            self.load_artists(onlyBaseItems=True)
        return ok

    def remove_artist(self, artist_id):
        ok = self._session.request('DELETE', self._base_url + '/artists/%s' % artist_id).ok
        if ok:
            self.load_artists(onlyBaseItems=True)
        return ok

    def add_album(self, album_id):
        if isinstance(album_id, basestring):
            ids = album_id
        else:
            ids = ','.join(album_id)
        ok = self._session.request('POST', self._base_url + '/albums', data={'albumId': ids}).ok
        if ok:
            self.load_albums(onlyBaseItems=True)
        return ok

    def remove_album(self, album_id):
        ok = self._session.request('DELETE', self._base_url + '/albums/%s' % album_id).ok
        if ok:
            self.load_albums(onlyBaseItems=True)
        return ok

    def add_playlist(self, playlist_id):
        if isinstance(playlist_id, basestring):
            uuids = playlist_id
        else:
            uuids = ','.join(playlist_id)
        ok = self._session.request('POST', self._base_url + '/playlists', data={'uuid': uuids}).ok
        if ok:
            self.load_playlists(onlyBaseItems=True)
        return ok

    def remove_playlist(self, playlist_id):
        ok = self._session.request('DELETE', self._base_url + '/playlists/%s' % playlist_id).ok
        if ok:
            self.load_playlists(onlyBaseItems=True)
        return ok

    def add_track(self, track_id):
        if isinstance(track_id, basestring):
            ids = track_id
        else:
            ids = ','.join(track_id)
        ok = self._session.request('POST', self._base_url + '/tracks', data={'trackIds': ids}).ok
        if ok:
            self.load_tracks(onlyBaseItems=True)
        return ok

    def remove_track(self, track_id):
        ok = self._session.request('DELETE', self._base_url + '/tracks/%s' % track_id).ok
        if ok:
            self.load_tracks(onlyBaseItems=True)
        return ok

    def add_video(self, video_id):
        if isinstance(video_id, basestring):
            ids = video_id
        else:
            ids = ','.join(video_id)
        ok = self._session.request('POST', self._base_url + '/videos', data={'videoIds': ids}).ok
        if ok:
            self.load_videos(onlyBaseItems=True)
        return ok

    def remove_video(self, video_id):
        ok = self._session.request('DELETE', self._base_url + '/videos/%s' % video_id).ok
        if ok:
            self.load_videos(onlyBaseItems=True)
        return ok

    def load_artists(self, onlyBaseItems=False):
        # New download of Favorite Artists
        if onlyBaseItems:
            rettype = 'baseitems'
        else:
            rettype = 'artists'
        debug.log('Favorites: Loading Favorite Artists')
        items = self._session._map_request(self._base_url + '/artists', params={'limit': 9999}, ret=rettype)
        if settings.cacheFavorites:
            self.favoArtists = [item.id for item in items]
            debug.log('MetaCache: Inserting %s Favorite Artists' % len(items))
            self._session.metaCache.insert('favorites', 'artists', data=self.favoArtists, overwrite=True)
        else:
            self.favoArtists = []
        return items

    def isFavoriteArtist(self, artist_id):
        if self.favoArtists == None:
            if settings.cacheFavorites:
                self.favoArtists = self._session.metaCache.fetch('favorites', 'artists')
                if self.favoArtists == None:
                    self.load_all()
            else:
                self.favoArtists = []
        return artist_id in self.favoArtists

    def load_albums(self, onlyBaseItems=False):
        # New download of Favorite Albums
        if onlyBaseItems:
            rettype = 'baseitems'
        else:
            rettype = 'albums'
        debug.log('Favorites: Loading Favorite Albums')
        items = self._session._map_request(self._base_url + '/albums', params={'limit': 9999}, ret=rettype)
        if settings.cacheFavorites:
            self.favoAlbums = [item.id for item in items]
            debug.log('MetaCache: Inserting %s Favorite Albums' % len(items))
            self._session.metaCache.insert('favorites', 'albums', data=self.favoAlbums, overwrite=True)
        else:
            self.favoAlbums = []
        return items

    def isFavoriteAlbum(self, album_id):
        if self.favoAlbums == None:
            if settings.cacheFavorites:
                self.favoAlbums = self._session.metaCache.fetch('favorites', 'albums')
                if self.favoAlbums == None:
                    self.load_all()
            else:
                self.favoAlbums = []
        return album_id in self.favoAlbums

    def load_playlists(self, onlyBaseItems=False):
        # New download of Favorite Playlists
        if onlyBaseItems:
            rettype = 'baseitems'
        else:
            rettype = 'playlists'
        debug.log('Favorites: Loading Favorite Playlists')
        items = self._session._map_request(self._base_url + '/playlists', params={'limit': 9999}, ret=rettype)
        if settings.cacheFavorites:
            self.favoPlaylists = [item.id for item in items]
            debug.log('MetaCache: Inserting %s Favorite Playlists' % len(items))
            self._session.metaCache.insert('favorites', 'playlists', data=self.favoPlaylists, overwrite=True)
        else:
            self.favoPlaylists = []
        return items

    def isFavoritePlaylist(self, playlist_id):
        if self.favoPlaylists == None:
            if settings.cacheFavorites:
                self.favoPlaylists = self._session.metaCache.fetch('favorites', 'playlists')
                if self.favoPlaylists == None:
                    self.load_all()
            else:
                self.favoPlaylists = []
        return playlist_id in self.favoPlaylists

    def load_tracks(self, onlyBaseItems=False):
        # New download of Favorite Tracks
        if onlyBaseItems:
            rettype = 'baseitems'
        else:
            rettype = 'tracks'
        debug.log('Favorites: Loading Favorite Tracks')
        items = self._session._map_request(self._base_url + '/tracks', params={'limit': 9999}, ret=rettype)
        if settings.cacheFavorites:
            self.favoTracks = [item.id for item in items]
            debug.log('MetaCache: Inserting %s Favorite Tracks' % len(items))
            self._session.metaCache.insert('favorites', 'tracks', data=self.favoTracks, overwrite=True)
        else:
            self.favoTracks = []
        if rettype == 'tracks':
            self._session.update_albums_in_tracklist(items)
        return items

    def isFavoriteTrack(self, track_id):
        if self.favoTracks == None:
            if settings.cacheFavorites:
                self.favoTracks = self._session.metaCache.fetch('favorites', 'tracks')
                if self.favoTracks == None:
                    self.load_all()
            else:
                self.favoTracks = []
        return track_id in self.favoTracks

    def load_videos(self, onlyBaseItems=False):
        # New download of Favorites
        if onlyBaseItems:
            rettype = 'baseitems'
        else:
            rettype = 'videos'
        debug.log('Favorites: Loading Favorite Videos')
        items = self._session._map_request(self._base_url + '/videos', params={'limit': 100}, ret=rettype)
        if settings.cacheFavorites:
            self.favoVideos = [item.id for item in items]
            debug.log('MetaCache: Inserting %s Favorite Videos' % len(items))
            self._session.metaCache.insert('favorites', 'videos', data=self.favoVideos, overwrite=True)
        else:
            self.favoVideos = []
        return items

    def isFavoriteVideo(self, video_id):
        if self.favoVideos == None:
            if settings.cacheFavorites:
                self.favoVideos = self._session.metaCache.fetch('favorites', 'videos')
                if self.favoVideos == None:
                    self.load_all()
            else:
                self.favoVideos = []
        return video_id in self.favoVideos

    def do_action(self, action, item, forceConfirm=False):
        dialog = xbmcgui.Dialog()
        if item:
            if action == 'toggle':
                add = not item._isFavorite
            else:
                add = action != 'remove'
            heading = _T('Add Favorite ?') if add else _T('Remove Favorite ?')
            if isinstance(item, ArtistItem):
                kind = _T('Artist')
                name = item.name
                action_cmd = self.add_artist if add else self.remove_artist
            elif isinstance(item, AlbumItem):
                kind = _T('Album')
                name = item.title
                action_cmd = self.add_album if add else self.remove_album
            elif isinstance(item, PlaylistItem):
                kind = _T('Playlist')
                name = item.title
                action_cmd = self.add_playlist if add else self.remove_playlist
            elif isinstance(item, TrackItem):
                kind = _T('Track')
                name = item.title
                action_cmd = self.add_track if add else self.remove_track
            elif isinstance(item, VideoItem):
                kind = _T('Video')
                name = item.title
                action_cmd = self.add_video if add else self.remove_video
            else:
                dialog.notification(settings.addon_name, _T('Unknown type of Favorite'), xbmcgui.NOTIFICATION_ERROR)
                return False
            if add:
                question = _T('Add {kind} "{name}" to Favorites ?').format(kind=kind, name=name)
            else:
                question = _T('Remove {kind} "{name}" from Favorites ?').format(kind=kind, name=name)
            ok = True
            if settings.confirmFavoriteActions or forceConfirm:
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )        
                ok = dialog.yesno(heading, question)
            if ok:
                ok = action_cmd(item.id)
                if ok:
                    if settings.showNotifications:
                        note = '%s %s' % (kind, _T('added') if add else _T('removed'))
                        dialog.notification(note, name, xbmcgui.NOTIFICATION_INFO)
                    xbmc.executebuiltin('Container.Refresh()')
                else:
                    dialog.notification(settings.addon_name, _T('API Call Failed'), xbmcgui.NOTIFICATION_ERROR)
            return ok
        else:
            dialog.notification(settings.addon_name, _T('Unknown type of Favorite'), xbmcgui.NOTIFICATION_ERROR)
            return False

    def export_ids(self, what, filename, action, remove=None):
        path = settings.import_export_path
        if len(path) == 0:
            return
        items = action(onlyBaseItems=False)
        if items and len(items) > 0:
            lines = [item.id + '\t' + item.getLabel(colored=False) + '\n' for item in items]
            full_path = os.path.join(path, filename)
            f = xbmcvfs.File(full_path, 'w')
            for line in lines:
                f.write(line.encode('utf-8'))
            f.close()
            xbmcgui.Dialog().notification(what, _T('{n} exported').format(n=len(lines)), xbmcgui.NOTIFICATION_INFO)
            if remove:
                ok = xbmcgui.Dialog().yesno(heading=_T('Deleting Favorite %s') % what, line1=_T('Remove {kind} "{name}" from Favorites ?').format(kind=len(items), name=what))
                if ok:
                    progress = xbmcgui.DialogProgress()
                    progress.create(_T('Deleting Favorite %s') % what)
                    idx = 0
                    for item in items:
                        if progress.iscanceled():
                            break
                        idx = idx + 1
                        percent = (idx * 100) / len(items) 
                        progress.update(percent, item.getLabel(colored=False))
                        try:
                            remove(item.id)
                        except:
                            break
                    progress.close()
    
    def import_ids(self, what, filename, action):
        try:
            ok = False
            f = xbmcvfs.File(filename, 'r')
            ids = f.read().decode('utf-8').split('\n')
            f.close()
            ids = [item.split('\t')[0] for item in ids]
            ids = [item for item in ids if len(item) > 0]
            if len(ids) > 0:
                ok = action(ids)
                if ok:
                    xbmcgui.Dialog().notification(what, _T('{n} imported').format(n=len(ids)), xbmcgui.NOTIFICATION_INFO)
        except Exception, e:
            debug.logException(e)
        return ok

#------------------------------------------------------------------------------
# Class to work with users playlists
#------------------------------------------------------------------------------

# The Dummy User object for Trial Mode
class TrialUser(object):

    def delete_cache(self): pass
    def newPlaylistDialog(self): return None
    def selectPlaylistDialog(self, headline=None, allowNew=False, item_type=None): return None
    def get_playlists(self, markDefault=True): return []
    def setPlaylistModified(self, playlist_id, title=None, overwrite=True): pass
    def getPlaylistCacheThread(self): pass
    def createPlaylistCache(self): pass
    def playlistsForItem(self, item_id): return None
    def isItemInPlaylist(self, item_id, playlist_id): return False
    def create_playlist(self, title, description='', notify=True): return None
    def delete_playlist(self, playlist_id, title, notify=True): return False
    def add_playlist_entries(self, playlist=None, playlist_id=None, item_id=None, items=[], notify=True): return False
    def remove_playlist_entry(self, playlist_id, entry_no=None, item_id=None, notify=True): return False

# The 'Real' User Object
class User(TrialUser):

    playlistCache = None

    def __init__(self, session, user_id):
        self._session = session
        self.id = user_id
        self._base_url = 'users/%s' % user_id
        if not settings.cachePlaylists:
            self.playlistCache = {}

    def delete_cache(self):
        try:
            if settings.cachePlaylists:
                self._session.metaCache.deleteAll('userpl')
        except Exception, e:
            debug.logException(e)            

    def newPlaylistDialog(self):
        dialog = xbmcgui.Dialog()
        title = dialog.input(_T('Name of new Playlist'), type=xbmcgui.INPUT_ALPHANUM)
        item = None
        if title:
            description = dialog.input(_T('Description (optional)'), type=xbmcgui.INPUT_ALPHANUM)
            item = self.create_playlist(title, description)
        return item

    def selectPlaylistDialog(self, headline=None, allowNew=False, item_type=None):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        try:
            if not headline:
                headline = _T('Choose Playlist')
            items = self.get_playlists()
            if (item_type == 'track' and settings.default_trackplaylist_id) or (item_type == 'video' and settings.default_videoplaylist_id):
                idx = 0
                for item in items:
                    if (item_type == 'track' and item.id == settings.default_trackplaylist_id) or (item_type == 'video' and item.id == settings.default_videoplaylist_id):
                        break
                    idx = idx + 1
                if idx > 0:
                    try:
                        # Move default playlist to the top position
                        default = items.pop(idx)
                        items.insert(0, default)
                    except:
                        pass                    
            dialog = xbmcgui.Dialog()
            item_list = [item.title for item in items]
            if allowNew:
                mask = '[COLOR {color}]%s[/COLOR]'.format(color=settings.folderColor) if settings.folderColor else '%s'
                item_list.append(mask % _T('Create new Playlist'))
        except Exception, e:
            debug.logException(e)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        selected = dialog.select(headline, item_list)
        if selected >= len(items):
            item = self.newPlaylistDialog()
            return item
        elif selected >= 0:
            return items[selected]
        return None

    def get_playlists(self, markDefault=True):
        items = self._session._map_request(self._base_url + '/playlists', params={'limit': 9999}, ret='playlists')
        if settings.cachePlaylists:
            # Create empty User Playlist Cache entries, if not exist
            playlist_ids = []
            for item in items:
                self.setPlaylistModified(item.id, item.title, overwrite=False)
                playlist_ids.append(item.id)
            # Delete unknown IDs from Cache
            cache_ids = self._session.metaCache.fetchAllIds('userpl')
            for cache_id in cache_ids:
                if not cache_id in playlist_ids:
                    debug.log('MetaCache: Deleting UserPlaylist "%s"' % cache_id)
                    self._session.metaCache.delete('userpl', cache_id)
            if len(playlist_ids) == 0:
                self._session.metaCache.insertUserPlaylist('dummy', 'Empty', [])
        if markDefault:
            # Select Default UserPlaylist as Favorite and UserPlaylist Color
            for item in items:
                labelTags = []
                if item.id == settings.default_trackplaylist_id:
                    item._isFavorite = True
                    item._labelColor = settings.userPlaylistColor
                    if not _T('Tracks') in labelTags:
                        labelTags.append(_T('Tracks'))
                elif item.id == settings.default_videoplaylist_id:
                    item._isFavorite = True
                    item._labelColor = settings.userPlaylistColor
                    if not _T('Videos') in labelTags:
                        labelTags.append(_T('Videos'))
                if labelTags:
                    item.title = '%s (%s)' % (item.title, ','.join(labelTags))
        return items
     
    def setPlaylistModified(self, playlist_id, title=None, overwrite=True):
        if settings.cachePlaylists:
            self._session.metaCache.insertUserPlaylist(playlist_id, title, items=None, overwrite=overwrite)
            self.playlistCache = None  # Force Reload of the Cache content

    def getPlaylistCacheThread(self):
        try:
            while not xbmc.abortRequested:
                try:
                    playlist = self.playlistQueue.get_nowait()
                except:
                    break
                debug.log('Requesting Tracks for UserPlaylist "%s"' % playlist.title)
                items = self._session.get_playlist_items(playlist=playlist, ret='baseitems')
                playlist_data = {'id': playlist.id, 
                                 'title': playlist.title, 
                                 'items': [item.id for item in items] }
                self.playlistDataQueue.put(playlist_data)
        except Exception, e:
            debug.logException(e)
   
    def createPlaylistCache(self):
        self.playlistCache = {}
        if not settings.cachePlaylists:
            return
        items = self._session.metaCache.fetchAllData('userpl')
        # Playlists without items to reload
        itemsToReload = [item for item in items if not 'items' in item]
        if 'dummy' in itemsToReload:
            if len(itemsToReload) == 1:
                debug.log('User has no UserPlaylist !')
                return
            debug.log('MetaCache: Deleting UserPlaylist "dummy"')
            self._session.metaCache.delete('userpl', 'dummy')
        loadedPlaylists = {}
        if not items or itemsToReload:
            # Download all UserPlaylists to (re)create Cache entries
            debug.log('Loading UserPlaylists for Cache ...')
            userplaylists = self.get_playlists(markDefault=False)
            for item in userplaylists:
                if item.id <> 'dummy':
                    loadedPlaylists.update({item.id: item})
            # Read updated Cache entries
            items = self._session.metaCache.fetchAllData('userpl')
            # Playlists without items to reload
            itemsToReload = [item for item in items if not 'items' in item]
            # Playlists with items      
            items = [item for item in items if 'items' in item]
            # Fill missing track lists in the cache
            workers = []
            self.playlistQueue = Queue()
            self.playlistDataQueue = Queue()
            # Step 1: Determine UserPlaylists to load
            for item in itemsToReload:
                if settings.max_http_requests < 2 or len(itemsToReload) == 1: 
                    # Read TrackIDs directly
                    baseitems = self._session.get_playlist_items(item.get('id'), ret='baseitems')
                    item.update({'items': [baseitem.id for baseitem in baseitems]})
                    self._session.metaCache.insertUserPlaylist(item.get('id'), item.get('title'), item.get('items'))
                    items.append(item)
                elif item.get('id') in loadedPlaylists:
                    self.playlistQueue.put(loadedPlaylists.get(item.get('id')))
            # Step 2: Load Playlist Tracks with multiple Threads
            maxThreads = self.playlistQueue.qsize()
            if maxThreads > settings.max_http_requests:
                maxThreads = settings.max_http_requests
            if maxThreads > 0:
                debug.log('Starting Threads to read UserPlaylists')
            while maxThreads > 0:
                try:
                    maxThreads = maxThreads - 1
                    worker = Thread(target=self.getPlaylistCacheThread)
                    worker.start()
                    workers.append(worker)
                except Exception, e:
                    debug.logException(e)
            if workers:
                debug.log('Waiting until all Threads are terminated')
            for worker in workers:
                worker.join(20)
                if worker.isAlive():
                    debug.log('Worker %s is still running ...' % worker.ident, xbmc.LOGWARNING)
            if self.playlistDataQueue.qsize() > 0:
                debug.log('Write %s UserPlaylists into the MetaCache' % self.playlistDataQueue.qsize())
                while not xbmc.abortRequested:
                    try:
                        item = self.playlistDataQueue.get_nowait()
                    except:
                        break
                    self._session.metaCache.insertUserPlaylist(item.get('id'), item.get('title'), item.get('items'))
                    items.append(item)
        # Step 3: Build PlaylistCache for Tracks
        for item in items:
            track_ids = item.get('items')
            if track_ids:
                if not self.playlistCache:
                    # Because setPlaylistModified() can reset the playlistCache to None
                    self.playlistCache = {}
                for track_id in track_ids:
                    entry = self.playlistCache.get(track_id)
                    if not entry:
                        entry = []
                    entry.append((item.get('id'), item.get('title')))
                    self.playlistCache.update({track_id: entry})
    
    def playlistsForItem(self, item_id):
        if self.playlistCache == None:
            self.createPlaylistCache()
        return self.playlistCache.get(item_id)

    def isItemInPlaylist(self, item_id, playlist_id):
        found = False
        plists = self.playlistsForItem(item_id)
        if plists:
            for pl_id, pl_name in plists:
                if pl_id == playlist_id:
                    debug.log('Item ID %s is allready in Playlist %s (%s)' % (item_id, pl_name, pl_id))
                    found = True
                    break
        return found

    def create_playlist(self, title, description='', notify=True):
        playlist = self._session._map_request(self._base_url + '/playlists', method='POST', data={'title': title, 'description': description}, ret='playlist')
        if playlist:
            if settings.showNotifications and notify:
                xbmcgui.Dialog().notification(playlist.title, _T('Playlist created'), xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification(settings.addon_name, _T('API Call Failed'), xbmcgui.NOTIFICATION_ERROR)
        return playlist

    def delete_playlist(self, playlist_id, title=None, notify=True):
        ok = self._session.request('DELETE', 'playlists/%s' % playlist_id).ok
        # Refresh buffer of Playlist Tracks
        self.setPlaylistModified(playlist_id, overwrite=True)
        if ok:
            if playlist_id == settings.default_trackplaylist_id:
                settings.default_trackplaylist_id = ''
                settings.default_trackplaylist = ''
                config.setSetting('default_trackplaylist_id', '')
                config.setSetting('default_trackplaylist', '')
            elif playlist_id == settings.default_videoplaylist_id:
                settings.default_videoplaylist_id = ''
                settings.default_videoplaylist = ''
                config.setSetting('default_videoplaylist_id', '')
                config.setSetting('default_videoplaylist', '')
            if settings.showNotifications and notify:
                xbmcgui.Dialog().notification(title if title else playlist_id, _T('Playlist deleted'), xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification(settings.addon_name, _T('API Call Failed'), xbmcgui.NOTIFICATION_ERROR)
        return ok

    def add_playlist_entries(self, playlist=None, playlist_id=None, item_id=None, items=[], notify=True):
        if not playlist:
            playlist = self._session.get_playlist(playlist_id)
        tracklist = []
        if item_id and not self.isItemInPlaylist(item_id, playlist.id):
            tracklist.append(item_id)
        for item in items:
            if not item.id in tracklist and not self.isItemInPlaylist(item.id, playlist.id): 
                tracklist.append(item.id)
        ok = True
        if len(tracklist) > 0:
            trackIds = ','.join(tracklist)
            if not playlist._etag:
                # Read Playlist to get ETag
                playlist = self._session.get_playlist(playlist.id)
            if playlist and playlist._etag:
                headers = {'If-None-Match': '%s' % playlist._etag}
                data = {'trackIds': trackIds, 'toIndex': playlist._numberOfItems}
                ok = self._session.request('POST', 'playlists/%s/tracks' % playlist.id, data=data, headers=headers).ok
            else:
                debug.log('Got no ETag for playlist %s' & playlist.id, level=xbmc.LOGERROR)
                ok = False
        # Refresh buffer of Playlist Tracks
        self.setPlaylistModified(playlist.id, playlist.title, overwrite=True)
        if ok:
            if settings.showNotifications and notify:
                xbmcgui.Dialog().notification(playlist.title, _T('Item added'), xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification(settings.addon_name, _T('API Call Failed'), xbmcgui.NOTIFICATION_ERROR)
        return ok

    def remove_playlist_entry(self, playlist_id, entry_no=None, item_id=None, notify=True):
        if item_id:
            # Get Track/Video-ID to remove from Playlist
            entry_no = None
            items = self._session.get_playlist_items(playlist_id)
            for item in items:
                if item.id == item_id:
                    entry_no = item._user_playlist_tack_no
            if entry_no == None:
                return False
        # Read Playlist to get ETag
        playlist = self._session.get_playlist(playlist_id)
        if playlist and playlist._etag:
            headers = {'If-None-Match': '%s' % playlist._etag}
            ok = self._session.request('DELETE', 'playlists/%s/tracks/%s' % (playlist_id, entry_no), headers=headers).ok
        else:
            ok = False
        if playlist:
            # Refresh buffer of Playlist Tracks
            self.setPlaylistModified(playlist.id, playlist.title, overwrite=True)
            if ok:
                if settings.showNotifications and notify:
                    xbmcgui.Dialog().notification(playlist.title, _T('Entry removed'), xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcgui.Dialog().notification(settings.addon_name, _T('API Call Failed'), xbmcgui.NOTIFICATION_ERROR)
        return ok

    def export_playlists(self, playlists, filename):
        path = settings.import_export_path
        if len(path) == 0:
            return
        full_path = os.path.join(path, filename)
        fd = xbmcvfs.File(full_path, 'w')
        numItems = 0
        for playlist in playlists:
            items = self._session.get_playlist_items(playlist=playlist)
            if len(items) > 0:
                numItems += playlist._numberOfItems
                fd.write(repr({ 'uuid': playlist.id,
                                'title': playlist.title,
                                'description': playlist.description,
                                'ids': [item.id for item in items]  }) + b'\n')
        fd.close()
        xbmcgui.Dialog().notification(_T('{n} exported').format(n=_T('Playlists')), xbmcgui.NOTIFICATION_INFO)

    def import_playlists(self, filename):
        try:
            ok = False
            f = xbmcvfs.File(filename, 'r')
            lines = f.read().decode('utf-8').split('\n')
            f.close()
            playlists = []
            names = []
            for line in lines:
                try:
                    if len(line) > 0:
                        item = eval(line)
                        if isinstance(item, DictionaryType):
                            playlists.append(item)
                            names.append(item.get('title'))
                except:
                    pass
            if len(names) < 1:
                return False
            selected = xbmcgui.Dialog().select(_T('Import {what}').format(what=_T('Playlist')), names)
            if selected < 0:
                return False
            item = playlists[selected]
            baseItems = [BaseItem(id=bItem) for bItem in item.get('ids')]
            dialog = xbmcgui.Dialog()
            title = dialog.input(_T('Name of new Playlist'), item.get('title'), type=xbmcgui.INPUT_ALPHANUM)
            if not title:
                return False
            description = dialog.input(_T('Description (optional)'), item.get('description'), type=xbmcgui.INPUT_ALPHANUM)
            playlist = self.create_playlist(title, description, notify=False)
            if playlist:
                ok = self.add_playlist_entries(playlist=playlist, items=baseItems, notify=False)
                if ok:
                    xbmcgui.Dialog().notification(playlist.title, _T('Item added'), xbmcgui.NOTIFICATION_INFO)
        except Exception, e:
            debug.logException(e)
        return ok

# End of File