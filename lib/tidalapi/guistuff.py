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

import sys
from urlparse import urlsplit
import xbmc, xbmcplugin
from xbmcgui import ListItem
from routing import Plugin

import config
import debug
from .config import settings
from .models import AlbumItem, ArtistItem, TrackItem, VideoItem, PromotionItem, PlaylistItem, FolderItem
from .all_strings import _T

#------------------------------------------------------------------------------
# Initialization
#------------------------------------------------------------------------------

plugin = Plugin(settings.addon_base_url)
plugin.name = settings.addon_name

#------------------------------------------------------------------------------
# Build media list for Artists, Albums, Playlists, Tracks, Videos
#------------------------------------------------------------------------------

def add_media(data_items, content=None, viewMode=None, end=True, withNextPage=False):
    if content:
        xbmcplugin.setContent(plugin.handle, content)
    list_items = []
    folder_path = sys.argv[0]
    isLoggedIn = len(settings._session_id) > 1
    
    item = None
    for item in data_items:

        url = plugin.url_for_path('/do_nothing')
        folder = not isinstance(item, TrackItem) and not isinstance(item, VideoItem)
        cm = []
        if settings.kodiVersion <= '16':
            # On Kodi 17 the context menue can't be replaced
            cm.append((_T('Play this'), 'Action(Play)'))

        if isinstance(item, ArtistItem):
            url = plugin.url_for_path('/artist_view/%s' % item.id)
            if isLoggedIn:
                if item._isFavorite:
                    cm.append((_T('Remove from Favorites'), 'RunPlugin(%s)' % plugin.url_for_path('/favorite_artist_remove/%s' % item.id)))
                else:
                    cm.append((_T('Add to Favorites'), 'RunPlugin(%s)' % plugin.url_for_path('/favorite_artist_add/%s' % item.id)))
            cm.append((_T('Similar Artists'), 'Container.Update(%s)' % plugin.url_for_path('/artist_similar/%s' % item.id)))
            cm.append((_T('Artist Radio'), 'Container.Update(%s)' % plugin.url_for_path('/artist_radio/%s' % item.id)))

        elif isinstance(item, AlbumItem) or (isinstance(item, PromotionItem) and item.type == 'ALBUM'):
            url = plugin.url_for_path('/album_view/%s' % item.id)
            if folder_path.find('artist_view') == -1 and item.artist:
                # Album view not active, so add context menu to artist page
                cm.append((_T('Show Artist'), 'Container.Update(%s)' % plugin.url_for_path('/artist_view/%s' % item.artist.id)))
            if isLoggedIn:
                if item._isFavorite:
                    cm.append((_T('Remove from Favorites'), 'RunPlugin(%s)' % plugin.url_for_path('/favorite_album_remove/%s' % item.id)))
                else:
                    cm.append((_T('Add to Favorites'), 'RunPlugin(%s)' % plugin.url_for_path('/favorite_album_add/%s' % item.id)))

        elif isinstance(item, PlaylistItem) or (isinstance(item, PromotionItem) and item.type == 'PLAYLIST'):
            if item.type == 'USER':
                url = plugin.url_for_path('/user_playlist_view/playlistitems/%s' %  item.id)
            else:
                url = plugin.url_for_path('/playlist_view/playlistitems/%s' % item.id)
            if isLoggedIn:
                if item._isFavorite:
                    cm.append((_T('Remove from Favorites'), 'RunPlugin(%s)' % plugin.url_for_path('/favorite_playlist_remove/%s' % item.id)))
                else:
                    cm.append((_T('Add to Favorites'), 'RunPlugin(%s)' % plugin.url_for_path('/favorite_playlist_add/%s' % item.id)))
                cm.append((_T('Add to Playlist ...'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_add_playlist/%s' % item.id)))
                if item.type == 'USER' and folder_path.find('user_playlist') >= 0:
                    if item.id == settings.default_trackplaylist_id:
                        cm.append((_T('Reset Default %s Playlist') % _T('Track'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_reset_default/tracks')))                
                    else:
                        cm.append((_T('Set as Default %s Playlist') % _T('Track'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_set_default/tracks/%s' % item.id)))                
                    if item.id == settings.default_videoplaylist_id:
                        cm.append((_T('Reset Default %s Playlist') % _T('Video'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_reset_default/videos')))                
                    else:
                        cm.append((_T('Set as Default %s Playlist') % _T('Video'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_set_default/videos/%s' % item.id)))                
                    cm.append((_T('Delete Playlist'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_delete/%s' % item.id)))                
                if item.type == 'USER' and len(settings.import_export_path) > 0:
                    cm.append((_T('Export {what}').format(what=_T('Playlist')), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_export/%s' % item.id)))

        elif isinstance(item, TrackItem):
            if item.streamReady:
                url = plugin.url_for_path('/play_track/%s' % item.id)
            else:
                url = plugin.url_for_path('/track_not_available/%s' % item.id)
            cm.append((_T('Show Artist'), 'Container.Update(%s)' % plugin.url_for_path('/artist_view/%s' % item.artist.id)))
            if folder_path.find('album_view') == -1 and item.album:
                cm.append((_T('Show Album'), 'Container.Update(%s)' % plugin.url_for_path('/album_view/%s' % item.album.id)))                
            if isLoggedIn:
                if item._isFavorite:
                    cm.append((_T('Remove from Favorites'), 'RunPlugin(%s)' % plugin.url_for_path('/favorite_track_remove/%s' % item.id)))
                else:
                    cm.append((_T('Add to Favorites'), 'RunPlugin(%s)' % plugin.url_for_path('/favorite_track_add/%s' % item.id)))
                if folder_path.find('user_playlist_view') == -1:
                    cm.append((_T('Add to Playlist ...'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_add_entry/track/%s' % item.id)))
                    if item._user_playlists:
                        cm.append((_T('Show Playlist'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_of_track/%s' % item.id)))
                elif item._user_playlist_id:
                    cm.append((_T('Move to other Playlist'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_move_entry/%s/%s/%s' % (item._user_playlist_id, item._user_playlist_tack_no, item.id))))
                    cm.append((_T('Remove from Playlist'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_remove_entry/%s/%s' % (item._user_playlist_id, item._user_playlist_tack_no))))
                cm.append((_T('Track Recommendations'), 'Container.Update(%s)' % plugin.url_for_path('/recommended_items/tracks/%s' % item.id)))
            cm.append((_T('Track Radio'), 'Container.Update(%s)' % plugin.url_for_path('/track_radio/%s' % item.id)))

        elif isinstance(item, VideoItem) or (isinstance(item, PromotionItem) and item.type == 'VIDEO'):
            if isinstance(item, VideoItem):
                if item.streamReady:
                    url = plugin.url_for_path('/play_video/%s' % item.id)
                else:
                    url = plugin.url_for_path('/video_not_available/%s' % item.id)
            cm.append((_T('Show Artist'), 'Container.Update(%s)' % plugin.url_for_path('/video_artist_view/%s' % item.id)))
            if isLoggedIn:
                if item._isFavorite:
                    cm.append((_T('Remove from Favorites'), 'RunPlugin(%s)' % plugin.url_for_path('/favorite_video_remove/%s' % item.id)))
                else:
                    cm.append((_T('Add to Favorites'), 'RunPlugin(%s)' % plugin.url_for_path('/favorite_video_add/%s' % item.id)))
                if folder_path.find('user_playlist_view') == -1:
                    cm.append((_T('Add to Playlist ...'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_add_entry/video/%s' % item.id)))
                    if isinstance(item, VideoItem) and item._user_playlists:
                        cm.append((_T('Show Playlist'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_of_video/%s' % item.id)))
                elif item._user_playlist_id:
                    cm.append((_T('Move to other Playlist'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_move_entry/%s/%s/%s' % (item._user_playlist_id, item._user_playlist_tack_no, item.id))))
                    cm.append((_T('Remove from Playlist'), 'RunPlugin(%s)' % plugin.url_for_path('/user_playlist_remove_entry/%s/%s' % (item._user_playlist_id, item._user_playlist_tack_no))))
                cm.append((_T('Video Recommendations'), 'Container.Update(%s)' % plugin.url_for_path('/recommended_items/videos/%s' % item.id)))

        if isinstance(item, PromotionItem):
            # Handle URLs for PromotionItems
            if item.type == 'ALBUM':
                url = plugin.url_for_path('/album_view/%s' % item.id)
            elif item.type == 'PLAYLIST':
                url = plugin.url_for_path('/playlist_view/playlistitems/%s' % item.id)
            elif item.type == 'VIDEO':
                url = plugin.url_for_path('/play_video/%s' % item.id)
                folder = False
            else:
                # don't show item type EXTURL
                continue

        li = item.getListItem()

        if settings.kodiVersion <> '16':
            # On Jarvis the Addon Settings are added by default.
            cm.append((_T('Addon Settings'), 'Addon.OpenSettings("%s")' % settings.addon_id))
        if settings.kodiVersion <= '16':
            li.addContextMenuItems(cm, replaceItems=True)
        else:
            li.addContextMenuItems(cm)
        list_items.append((url, li, folder))
        
    if withNextPage and item:
        # Add folder for next page
        try:
            nextOffset = item._offset + settings.page_size
            if nextOffset < item._totalNumberOfItems:
                path = urlsplit(sys.argv[0]).path or '/'
                path = path.split('/')[:-1]
                path.append(str(nextOffset))
                url = '/'.join(path)
                add_directory(_T('Next Page ({pos1}-{pos2})').format(pos1=nextOffset, pos2=min(nextOffset+settings.page_size, item._totalNumberOfItems)), plugin.url_for_path(url), color=settings.folderColor, isFolder=True)
        except:
            debug.log('Next Page for URL %s not set' % sys.argv[0], xbmc.LOGERROR)
    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    if end:
        xbmcplugin.endOfDirectory(plugin.handle)
        if content and viewMode:
            setViewMode(content, viewMode)


#------------------------------------------------------------------------------
# Add Search Results to media list
#------------------------------------------------------------------------------

def add_search_result(searchresults, sort=None, reverse=False, end=True):
    headline = '-------------------- %s --------------------'
    xbmcplugin.setContent(plugin.handle, 'songs')
    if searchresults.artists.__len__() > 0:
        add_directory(headline % _T('Artists'), plugin.url_for_path('/do_nothing'), color=settings.favoriteColor, isFolder=False)
        if sort:
            searchresults.artists.sort(key=lambda line: line.getSortField(sort), reverse=reverse)
        add_media(searchresults.artists, end=False)
    if searchresults.albums.__len__() > 0:
        add_directory(headline % _T('Albums'), plugin.url_for_path('/do_nothing'), color=settings.favoriteColor, isFolder=False)
        if sort:
            searchresults.albums.sort(key=lambda line: line.getSortField(sort), reverse=reverse)
        add_media(searchresults.albums, end=False)
    if searchresults.playlists.__len__() > 0:
        add_directory(headline % _T('Playlists'), plugin.url_for_path('/do_nothing'), color=settings.favoriteColor, isFolder=False)
        if sort:
            searchresults.playlists.sort(key=lambda line: line.getSortField(sort), reverse=reverse)
        add_media(searchresults.playlists, end=False)
    if searchresults.tracks.__len__() > 0:
        add_directory(headline % _T('Tracks'), plugin.url_for_path('/do_nothing'), color=settings.favoriteColor, isFolder=False)
        if sort:
            searchresults.tracks.sort(key=lambda line: line.getSortField(sort), reverse=reverse)
        add_media(searchresults.tracks, end=False)
    if searchresults.videos.__len__() > 0:
        add_directory(headline % _T('Videos'), plugin.url_for_path('/do_nothing'), color=settings.favoriteColor, isFolder=False)
        if sort:
            searchresults.videos.sort(key=lambda line: line.getSortField(sort), reverse=reverse)
        add_media(searchresults.videos, end=False)
    if end:
        xbmcplugin.endOfDirectory(plugin.handle)
        setViewMode('songs', 'playlists')

#------------------------------------------------------------------------------
# Add a directory item
#------------------------------------------------------------------------------

def colorizeText(color, text, ignoreExisting=False):
    retval = text
    if color and (not '[COLOR' in text or ignoreExisting):
        retval = '[COLOR %s]%s[/COLOR]' % (color, retval)
    return retval

def add_directory(item, endpoint, image=None, fanart=None, info=None, color=None, isFolder=True, contextmenu=None):
    # Define Custom Context Menu
    cm = []
    cm.append((_T('Open this'), 'Action(Play)'))
    if contextmenu:
        for contextitem in contextmenu: cm.append(contextitem)
    if settings.kodiVersion <> '16':
        cm.append((_T('Addon Settings'), 'Addon.OpenSettings("%s")' % settings.addon_id))    
    if isinstance(item, FolderItem):
        li = item.getListItem()
        if settings.kodiVersion <= '16':
            li.addContextMenuItems(cm, replaceItems=True)
        else:
            li.addContextMenuItems(cm)
        xbmcplugin.addDirectoryItem(plugin.handle, endpoint, li, isFolder=True)
        return
    label = item
    if not info:
        info = item
    if not image:
        image = settings.addon_icon
    if not fanart:
        fanart = settings.addon_fanart
    if color == None:
        color = settings.folderColor
    label = colorizeText(color, label, ignoreExisting=False)
    li = ListItem(label=label, iconImage=image, thumbnailImage=image)
    if settings.showFanart and fanart:
        li.setArt({'fanart': fanart})
    if info:
        li.setInfo('music', {'artist': info})
    if settings.kodiVersion <= '16':
        li.addContextMenuItems(cm, replaceItems=True)
    else:
        li.addContextMenuItems(cm)
    xbmcplugin.addDirectoryItem(plugin.handle, endpoint, li, isFolder=isFolder)

#------------------------------------------------------------------------------
# Set the view mode of the container (depending on config settings)
#------------------------------------------------------------------------------

SkinViewModes = { 'skin.confluence': {'1': {'default': '50'},   # CommonRootView
                                      '2': {'default': '51'},   # FullWidthList
                                      '3': {'default': '500'},  # ThumbnailView
                                      '4': {'default': '506',   # MusicInfoListView
                                            'musicvideos': '506' if settings.kodiVersion <= '16' else '511', # MusicVideoInfoListView
                                            'artists': '506' if settings.kodiVersion <= '16' else '512',   # ArtistMediaListView
                                            'albums': '506' if settings.kodiVersion <= '16' else '513', # AlbumInfoListView
                                            'songs': '506' }    # MusicInfoListView
                                       },
                  'skin.estuary':    {'1': {'default': '55'},   # WideList
                                      '2': {'default': '55'},   # WideList (no full with in skin Estuary)
                                      '3': {'default': '500'},  # SmallThumbs
                                      '4': {'default': '55'},   # WideList
                                       },
                  'default':         {'1': {'default': '50'},   # CommonRootView
                                      '2': {'default': '51'},   # FullWidthList
                                      '3': {'default': '500'},  # ThumbnailView
                                      '4': {'default': '506'}   # MusicInfoListView
                                       }
    }

def setViewMode(content, viewMode):
    mode = config.getSetting('view_mode_%s' % viewMode)
    if not mode:
        mode = config.getSetting('view_mode_%ss' % viewMode)
    if mode and mode != "0":
        try:
            skinModes = SkinViewModes.get(settings.skinTheme)
            if not skinModes:
                skinModes = SkinViewModes.get('default')
            if mode in skinModes:
                newModes = skinModes.get(mode) 
                newMode = newModes.get(content if content in newModes else 'default')
                if newMode: 
                    debug.log("SetViewMode: %s,%s,%s,%s,%s" % (content, viewMode, mode, settings.skinTheme, newMode), xbmc.LOGSEVERE)
                    xbmc.executebuiltin('Container.SetViewMode(%s)' % newMode)
        except:
            debug.log("SetViewMode %s failed for %s,%s in skin %s" % (mode, content, viewMode, settings.skinTheme))

# End of File