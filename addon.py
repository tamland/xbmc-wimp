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

import os, textwrap, traceback, urllib
from datetime import datetime
import xbmc, xbmcgui, xbmcplugin, xbmcvfs
from xbmcgui import ListItem
from routing import Plugin
from requests import HTTPError

from lib.tidalapi import config
from lib.tidalapi import debug

from lib.tidalapi.config import settings
from lib.tidalapi.session import Session
from lib.tidalapi.models import PlaylistItem
from lib.tidalapi.all_strings import _T, _P
from lib.tidalapi.guistuff import add_directory, add_media, add_search_result, setViewMode

#------------------------------------------------------------------------------
# Initialization
#------------------------------------------------------------------------------

plugin = Plugin(settings.addon_base_url)
plugin.name = settings.addon_name

# Initial Session Configuration
tidalSession = Session()
tidalSession.load_session()
tidalSession.upgrade_settings()

#------------------------------------------------------------------------------
# Root Menu
#------------------------------------------------------------------------------

@plugin.route('/')
def root():
    xbmcplugin.setContent(plugin.handle, 'files')
    if tidalSession.is_logged_in:
        add_directory(_T('My Music'), plugin.url_for(user_home))
    else:
        add_directory(_T('Not logged in - Trial Mode active !'), plugin.url_for(login), info=_T('Trial Mode'), color=settings.favoriteColor, isFolder=False)
    add_directory(_T("What's New"), plugin.url_for(folder, group='featured'))
    add_directory(_T('TIDAL Rising'), plugin.url_for(folder, group='rising'))
    add_directory(_T('TIDAL Discovery'), plugin.url_for(folder, group='discovery'))
    add_directory(_T('Promotions'), plugin.url_for(promotions))
    add_directory(_T('Movies'), plugin.url_for(folder, group='movies'))
    add_directory(_T('Shows'), plugin.url_for(folder, group='shows'))
    add_directory(_T('Genres'), plugin.url_for(folder, group='genres'))
    add_directory(_T('Moods'), plugin.url_for(folder, group='moods'))
    add_directory(_T('Search'), plugin.url_for(search))
    if tidalSession.is_logged_in:
        add_directory(_T('Logout'), plugin.url_for(logout), isFolder=False)
    else:
        add_directory(_T('Login'), plugin.url_for(login), isFolder=False)
    xbmcplugin.endOfDirectory(plugin.handle)
    setViewMode('files', 'folders')

@plugin.route('/login')
def login():
    tidalSession.autologin()
    xbmc.executebuiltin('Container.Refresh()')

@plugin.route('/logout')
def logout():
    tidalSession.logout()
    xbmc.executebuiltin('Container.Refresh()')

@plugin.route('/do_nothing')
def do_nothing():
    # For Dummy List Items
    pass

#------------------------------------------------------------------------------
# Menu: My Music
#------------------------------------------------------------------------------

@plugin.route('/user_home')
def user_home():
    xbmcplugin.setContent(plugin.handle, 'files')
    cm = []
    if len(settings.import_export_path) > 0:
        cm = [ (_T('Export {what}').format(what=_T('Playlists')), 'RunPlugin(%s)' % plugin.url_for(user_playlist_export_all)),
               (_T('Import {what}').format(what=_T('Playlists')), 'RunPlugin(%s)' % plugin.url_for(user_playlist_import)) ]
    add_directory(_T('My Playlists'), plugin.url_for(user_playlists), contextmenu=cm)
    if len(settings.import_export_path) > 0:
        cm = [ (_T('Export {what}').format(what=_T('Playlists')), 'RunPlugin(%s)' % plugin.url_for(favorite_export, what='playlists')),
               (_T('Import {what}').format(what=_T('Playlists')), 'RunPlugin(%s)' % plugin.url_for(favorite_import, what='playlists')) ]
    add_directory(_T('Favorite Playlists'), plugin.url_for(favorite_playlists), contextmenu=cm)
    if len(settings.import_export_path) > 0:
        cm = [ (_T('Export {what}').format(what=_T('Artists')), 'RunPlugin(%s)' % plugin.url_for(favorite_export, what='artists')),
               (_T('Import {what}').format(what=_T('Artists')), 'RunPlugin(%s)' % plugin.url_for(favorite_import, what='artists')) ]
    add_directory(_T('Favorite Artists'), plugin.url_for(favorite_artists), contextmenu=cm)
    if len(settings.import_export_path) > 0:
        cm = [ (_T('Export {what}').format(what=_T('Albums')), 'RunPlugin(%s)' % plugin.url_for(favorite_export, what='albums')),
               (_T('Import {what}').format(what=_T('Albums')), 'RunPlugin(%s)' % plugin.url_for(favorite_import, what='albums')) ]
    add_directory(_T('Favorite Albums'), plugin.url_for(favorite_albums), contextmenu=cm)
    if len(settings.import_export_path) > 0:
        cm = [ (_T('Export {what}').format(what=_T('Tracks')), 'RunPlugin(%s)' % plugin.url_for(favorite_export, what='tracks')),
               (_T('Import {what}').format(what=_T('Tracks')), 'RunPlugin(%s)' % plugin.url_for(favorite_import, what='tracks')) ]
    add_directory(_T('Favorite Tracks'), plugin.url_for(favorite_tracks), contextmenu=cm)
    if len(settings.import_export_path) > 0:
        cm = [ (_T('Export {what}').format(what=_T('Videos')), 'RunPlugin(%s)' % plugin.url_for(favorite_export, what='videos')),
               (_T('Import {what}').format(what=_T('Videos')), 'RunPlugin(%s)' % plugin.url_for(favorite_import, what='videos')) ]
    add_directory(_T('Favorite Videos'), plugin.url_for(favorite_videos), contextmenu=cm)
    add_directory(_T('User Info'), plugin.url_for(user_info), isFolder=False)
    xbmcplugin.endOfDirectory(plugin.handle)
    setViewMode('files', 'folders')

@plugin.route('/user_info')
def user_info():
    userInfo = tidalSession.getUserInfo()
    if userInfo:
        xbmcgui.Dialog().ok(heading='%s %s' % (userInfo.firstName, userInfo.lastName),
                            line1='ID: %s, E-Mail: %s' % (userInfo.id, userInfo.email), 
                            line2='SubscriptionType: %s, Status: %s' % (userInfo.subscription.subscription.get('type'), userInfo.subscription.status), 
                            line3='Created: %s, Valid until: %s' % (userInfo.created.date(), userInfo.subscription.validUntil.date()) )

#------------------------------------------------------------------------------
# User Playlist Handling
#------------------------------------------------------------------------------

@plugin.route('/user_playlists')
def user_playlists():
    add_directory(_T('Create new Playlist'), plugin.url_for(user_playlist_create))
    items = tidalSession.user.get_playlists()
    add_media(items, content='songs', viewMode='playlists')

@plugin.route('/reset_user_cache')
def reset_user_cache():
    debug.log('Deleting UserPlaylists and Favorites from MetaCache')
    tidalSession.user.delete_cache()
    tidalSession.favorites.delete_cache()

@plugin.route('/reload_user_cache')
def reload_user_cache():
    debug.log('Deleting UserPlaylists and Favorites from MetaCache')
    tidalSession.user.delete_cache()
    tidalSession.favorites.delete_cache()
    tidalSession.user.createPlaylistCache()
    tidalSession.favorites.load_all()
    xbmcgui.Dialog().notification(plugin.name, _T('Cache Rebuild complete'))

@plugin.route('/user_playlist_view/<item_type>/<playlist_id>')
def user_playlist_view(item_type, playlist_id):
    playlist = tidalSession.get_playlist(playlist_id)
    if playlist:
        viewMode = 'tracks'
        if item_type == 'videos':
            viewMode = 'videos'
        if item_type == 'playlistitems':
            if playlist.numberOfVideos > 0:
                add_directory(_T('Tracks only'), plugin.url_for(user_playlist_view, item_type='tracks', playlist_id=playlist.id), image=playlist._imageUrl, fanart=playlist._fanartUrl)
            if playlist.numberOfTracks > 0 and playlist.numberOfVideos > 0:
                add_directory(_T('Videos only'), plugin.url_for(user_playlist_view, item_type='videos', playlist_id=playlist.id), image=playlist._imageUrl, fanart=playlist._fanartUrl)
        items = tidalSession.get_playlist_items(playlist=playlist, ret=item_type)
        add_media(items, content='musicvideos' if item_type == 'videos' else 'songs', viewMode=viewMode)

@plugin.route('/user_playlist_of_track/<track_id>')
def user_playlist_of_track(track_id):
    item = tidalSession.get_track(track_id)
    selected = -1
    if item._user_playlists:
        if len(item._user_playlists) > 1:
            pl_names = [pl_title for pl_id, pl_title in item._user_playlists]
            selected = xbmcgui.Dialog().select(_T('Choose Playlist'), pl_names)            
        elif len(item._user_playlists) == 1:
            selected = 0
    if selected >= 0:
        pl_id, pl_title = item._user_playlists[selected]
        xbmc.executebuiltin('Container.Update(%s, True)' % plugin.url_for(user_playlist_view, item_type='playlistitems', playlist_id=pl_id))

@plugin.route('/user_playlist_of_video/<video_id>')
def user_playlist_of_video(video_id):
    item = tidalSession.get_video(video_id)
    selected = -1
    if item._user_playlists:
        if len(item._user_playlists) > 1:
            pl_names = [pl_title for pl_id, pl_title in item._user_playlists]
            selected = xbmcgui.Dialog().select(_T('Choose Playlist'), pl_names)            
        elif len(item._user_playlists) == 1:
            selected = 0
    if selected >= 0:
        pl_id, pl_title = item._user_playlists[selected]
        xbmc.executebuiltin('Container.Update(%s, True)' % plugin.url_for(user_playlist_view, item_type='playlistitems', playlist_id=pl_id))

@plugin.route('/user_playlist_create')
def user_playlist_create():
    dialog = xbmcgui.Dialog()
    title = dialog.input(_T('Name of new Playlist'), type=xbmcgui.INPUT_ALPHANUM)
    if title:
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        try:
            description = dialog.input(_T('Description (optional)'), type=xbmcgui.INPUT_ALPHANUM)
            tidalSession.user.create_playlist(title, description)
        except Exception, e:
            debug.logException(e)
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        xbmc.executebuiltin('Container.Refresh()')

@plugin.route('/user_playlist_delete/<playlist_id>')
def user_playlist_delete(playlist_id):
    dialog = xbmcgui.Dialog()
    playlist = tidalSession.get_playlist(playlist_id)
    if not playlist or not isinstance(playlist, PlaylistItem):
        dialog.notification(plugin.name, _T('Playlist not found'), xbmcgui.NOTIFICATION_ERROR)
    else:
        ok = True
        if settings.confirmFavoriteActions:
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )        
            ok = dialog.yesno(_T('Delete Playlist ?'), _T('Are you sure to delete the playlist "%s" ?') % playlist.title)
        if ok and playlist._numberOfItems > 0:
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )        
            ok = dialog.yesno(_T('Delete Playlist ?'), _T('Playlist "%s" contains %s items. Are you really sure to delete this playlist ?') % (playlist.title, playlist._numberOfItems))
        if ok:
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            try:
                tidalSession.user.delete_playlist(playlist_id, title=playlist.title)
            except Exception, e:
                debug.logException(e)
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            xbmc.executebuiltin('Container.Refresh()')

@plugin.route('/user_playlist_add_entry/<item_type>/<item_id>')
def user_playlist_add_entry(item_type, item_id):
    playlist = tidalSession.user.selectPlaylistDialog(allowNew=True, item_type=item_type)
    if playlist:
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        try:
            tidalSession.user.add_playlist_entries(playlist=playlist, item_id=item_id)
        except Exception, e:
            debug.logException(e)
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        xbmc.executebuiltin('Container.Refresh()')

@plugin.route('/user_playlist_add_playlist/<playlist_id>')
def user_playlist_add_playlist(playlist_id):
    items = tidalSession.get_playlist_items(playlist_id)
    if len(items) > 0:
        items = [item for item in items if item._playable]
        headline = _T('Choose Playlist') + ' (%s %s)' % (len(items), _T('Tracks'))
        playlist = tidalSession.user.selectPlaylistDialog(headline=headline, allowNew=True)
        if playlist:
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            try:
                # Sort by Artist, Title
                items.sort(key=lambda line: (line.artist.name, line.title) , reverse=False)
                tidalSession.user.add_playlist_entries(playlist=playlist, items=items)
            except Exception, e:
                debug.logException(e)
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            xbmc.executebuiltin('Container.Refresh()')

@plugin.route('/user_playlist_remove_entry/<playlist_id>/<entry_no>')
def user_playlist_remove_entry(playlist_id, entry_no):
    dialog = xbmcgui.Dialog()
    item_no = int('0%s' % entry_no) + 1
    ok = True
    if settings.confirmFavoriteActions:
        ok = dialog.yesno(_T('Remove from Playlist ?'), _T('Are you sure to remove item number %s from this playlist ?') % item_no )
    if ok:
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        try:
            tidalSession.user.remove_playlist_entry(playlist_id, entry_no=entry_no)
        except Exception, e:
            debug.logException(e)
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        xbmc.executebuiltin('Container.Refresh()')       

@plugin.route('/user_playlist_move_entry/<playlist_id>/<entry_no>/<item_id>')
def user_playlist_move_entry(playlist_id, entry_no, item_id):
    dialog = xbmcgui.Dialog()
    playlist = tidalSession.user.selectPlaylistDialog(headline=_T('Move to other Playlist'), allowNew=True)
    if playlist:
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        try:
            ok = tidalSession.user.add_playlist_entries(playlist=playlist, item_id=item_id, notify=False)
            if ok:
                ok = tidalSession.user.remove_playlist_entry(playlist_id, entry_no=entry_no, notify=False)
            if ok:
                if settings.showNotifications:
                    dialog.notification(playlist.title, _T('Item moved'), xbmcgui.NOTIFICATION_INFO)
            else:
                dialog.notification(plugin.name, _T('API Call Failed'), xbmcgui.NOTIFICATION_ERROR)
        except Exception, e:
            debug.logException(e)
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        xbmc.executebuiltin('Container.Refresh()')

@plugin.route('/user_playlist_toggle')
def user_playlist_toggle():
    if not tidalSession.is_logged_in:
        return
    focusId = xbmcgui.Window().getFocusId()
    pos = xbmc.getInfoLabel('Container(%s).Position' % focusId)
    url = xbmc.getInfoLabel('Container(%s).ListitemPosition(%s).FileNameAndPath' % (focusId, pos)).decode('utf-8')
    if settings.addon_id in url and 'play_track/' in url:
        item_type = 'track'
        userpl_id = settings.default_trackplaylist_id
        userpl = settings.default_trackplaylist
        item_id = url.split('play_track/')[1]
    elif settings.addon_id in url and 'play_video/' in url:
        item_type = 'video'
        userpl_id = settings.default_videoplaylist_id
        userpl = settings.default_videoplaylist
        item_id = url.split('play_video/')[1]
    else:
        return
    try:
        if item_type == 'track':
            item = tidalSession.get_track(item_id)
        elif item_type == 'video':
            item = tidalSession.get_video(item_id)
        else:
            return
        if not userpl_id:
            # Dialog Mode if default Playlist not set
            user_playlist_add_entry(item_type, item_id)
            return
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        ok = True
        if item._user_playlists and userpl_id in [pl[0] for pl in item._user_playlists]:
            if settings.confirmFavoriteActions:
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )        
                ok = xbmcgui.Dialog().yesno(_T('My Playlists'), _T('Remove Item from Playlist "%s" ?') % userpl)
                xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            if ok:
                tidalSession.user.remove_playlist_entry(playlist_id=userpl_id, item_id=item.id)
        else:
            if settings.confirmFavoriteActions:
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )        
                ok = xbmcgui.Dialog().yesno(_T('My Playlists'), _T('Add Item to Playlist "%s" ?') % userpl)
                xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            if ok:
                tidalSession.user.add_playlist_entries(playlist_id=userpl_id, item_id=item.id)
    except:
        pass
    xbmc.executebuiltin( "Dialog.Close(busydialog)" ) # Avoid GUI Lock        
    xbmc.executebuiltin('Container.Refresh()')

@plugin.route('/user_playlist_set_default/<item_type>/<playlist_id>')
def user_playlist_set_default(item_type, playlist_id):
    item = tidalSession.get_playlist(playlist_id)
    if item:
        if item_type.lower().find('track') >= 0:
            config.setSetting('default_trackplaylist', item.title)
            config.setSetting('default_trackplaylist_id', item.id)
            config.reloadConfig()
        elif item_type.lower().find('video') >= 0:
            config.setSetting('default_videoplaylist', item.title)
            config.setSetting('default_videoplaylist_id', item.id)
            config.reloadConfig()
    xbmc.executebuiltin('Container.Refresh()')

@plugin.route('/user_playlist_reset_default/<item_type>')
def user_playlist_reset_default(item_type):
    if item_type.lower().find('track') >= 0:
        config.setSetting('default_trackplaylist', '')
        config.setSetting('default_trackplaylist_id', '')
        config.reloadConfig()
    elif item_type.lower().find('video') >= 0:
        config.setSetting('default_videoplaylist', '')
        config.setSetting('default_videoplaylist_id', '')
        config.reloadConfig()
    xbmc.executebuiltin('Container.Refresh()')

@plugin.route('/user_playlist_export/<playlist_id>')
def user_playlist_export(playlist_id):
    try:
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        playlist = tidalSession.get_playlist(playlist_id)
        if playlist and playlist._numberOfItems > 0:
            filename = 'playlist_%s_%s.cfg' % (playlist.title, datetime.now().strftime('%Y-%m-%d-%H%M%S'))
            filename = filename.replace(' ', '_')
            tidalSession.user.export_playlists([playlist], filename)
    except Exception, e:
        debug.logException(e)
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )

@plugin.route('/user_playlist_export_all')
def user_playlist_export_all():
    try:
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        items = tidalSession.user.get_playlists(markDefault=False)
        filename = 'playlist_all_%s.cfg' % datetime.now().strftime('%Y-%m-%d-%H%M%S')
        tidalSession.user.export_playlists(items, filename)
    except Exception, e:
        debug.logException(e)
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )

@plugin.route('/user_playlist_import')
def user_playlist_import():
    path = settings.import_export_path
    if len(path) == 0:
        return
    files = xbmcvfs.listdir(path)[1]
    files = [name for name in files if name.startswith('playlist_')]
    selected = xbmcgui.Dialog().select(path, files)
    if selected < 0:    
        return
    name = os.path.join(path, files[selected])
    try:
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        tidalSession.user.import_playlists(name)
    except Exception, e:
        debug.logException(e)
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )    

#------------------------------------------------------------------------------
# User Favorites Handling
#------------------------------------------------------------------------------

@plugin.route('/favorite_toggle')
def favorite_toggle():
    if not tidalSession.is_logged_in:
        return
    if not settings.confirmFavoriteActions:
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
    try:
        ok = False
        focusId = xbmcgui.Window().getFocusId()
        pos = xbmc.getInfoLabel('Container(%s).Position' % focusId)
        path = xbmc.getInfoLabel('Container.FolderPath').decode('utf-8')
        url = xbmc.getInfoLabel('Container(%s).ListitemPosition(%s).FileNameAndPath' % (focusId, pos)).decode('utf-8')
        if settings.addon_id in url:
            forceConfirm = '/favorite_' in path
            if 'artist_view/' in url:
                ok = tidalSession.favorites.do_action('toggle', tidalSession.get_artist(url.split('artist_view/')[1]), forceConfirm)
            elif 'album_view/' in url:
                ok = tidalSession.favorites.do_action('toggle', tidalSession.get_album(url.split('album_view/')[1]), forceConfirm)
            elif 'play_track/' in url:
                ok = tidalSession.favorites.do_action('toggle', tidalSession.get_track(url.split('play_track/')[1]), forceConfirm)
            elif 'playlist_view/' in url:
                type_and_id = url.split('playlist_view/')[1]
                if '/' in type_and_id:
                    ok = tidalSession.favorites.do_action('toggle', tidalSession.get_playlist(type_and_id.split('/')[1]), forceConfirm)
            elif 'play_video/' in url:
                ok = tidalSession.favorites.do_action('toggle', tidalSession.get_video(url.split('play_video/')[1]), forceConfirm)
    except:
        pass
    if not ok:
        xbmc.executebuiltin( "Dialog.Close(busydialog)" ) # Avoid GUI Lock        

@plugin.route('/favorite_export/<what>')
def favorite_export(what):
    name = 'favo_%s_%s.cfg' % (what, datetime.now().strftime('%Y-%m-%d-%H%M%S'))
    if what == 'playlists':
        tidalSession.favorites.export_ids(what=_T('Playlists'), filename=name, action=tidalSession.favorites.load_playlists)
    elif what == 'artists':
        tidalSession.favorites.export_ids(what=_T('Artists'), filename=name, action=tidalSession.favorites.load_artists, remove=tidalSession.favorites.remove_artist)
    elif what == 'albums':
        tidalSession.favorites.export_ids(what=_T('Albums'), filename=name, action=tidalSession.favorites.load_albums, remove=tidalSession.favorites.remove_album)
    elif what == 'tracks':
        tidalSession.favorites.export_ids(what=_T('Tracks'), filename=name, action=tidalSession.favorites.load_tracks, remove=tidalSession.favorites.remove_track)
    elif what == 'videos':
        tidalSession.favorites.export_ids(what=_T('Videos'), filename=name, action=tidalSession.favorites.load_videos, remove=tidalSession.favorites.remove_video)

@plugin.route('/favorite_import/<what>')
def favorite_import(what):
    path = settings.import_export_path
    if len(path) == 0:
        return
    files = xbmcvfs.listdir(path)[1]
    files = [name for name in files if name.startswith('favo_%s' % what)]
    selected = xbmcgui.Dialog().select(path, files)
    if selected < 0:    
        return
    name = os.path.join(path, files[selected])
    ok = False
    if what == 'playlists':
        ok = tidalSession.favorites.import_ids(what=_T('Playlists'), filename=name, action=tidalSession.favorites.add_playlist)
    elif what == 'artists':
        ok = tidalSession.favorites.import_ids(what=_T('Artists'), filename=name, action=tidalSession.favorites.add_artist)
    elif what == 'albums':
        ok = tidalSession.favorites.import_ids(what=_T('Albums'), filename=name, action=tidalSession.favorites.add_album)
    elif what == 'tracks':
        ok = tidalSession.favorites.import_ids(what=_T('Tracks'), filename=name, action=tidalSession.favorites.add_track)
    elif what == 'videos':
        ok = tidalSession.favorites.import_ids(what=_T('Videos'), filename=name, action=tidalSession.favorites.add_video)
    return ok

@plugin.route('/favorite_playlists')
def favorite_playlists():
    items = tidalSession.favorites.load_playlists()
    items.sort(key=lambda line: line.getSortField('name'), reverse=False)
    add_media(items, content='songs', viewMode='playlists')

@plugin.route('/favorite_playlist_add/<playlist_id>')
def favorite_playlist_add(playlist_id):
    tidalSession.favorites.do_action('add', tidalSession.get_playlist(playlist_id))

@plugin.route('/favorite_playlist_remove/<playlist_id>')
def favorite_playlist_remove(playlist_id):
    tidalSession.favorites.do_action('remove', tidalSession.get_playlist(playlist_id))

@plugin.route('/favorite_artists')
def favorite_artists():
    items = tidalSession.favorites.load_artists()
    items.sort(key=lambda line: line.getSortField('name'), reverse=False)
    add_media(items, content='artists', viewMode='artists')

@plugin.route('/favorite_artist_add/<artist_id>')
def favorite_artist_add(artist_id):
    tidalSession.favorites.do_action('add', tidalSession.get_artist(artist_id))

@plugin.route('/favorite_artist_remove/<artist_id>')
def favorite_artist_remove(artist_id):
    tidalSession.favorites.do_action('remove', tidalSession.get_artist(artist_id))

@plugin.route('/favorite_albums')
def favorite_albums():
    items = tidalSession.favorites.load_albums()
    items.sort(key=lambda line: line.getSortField('artist'), reverse=False)
    for item in items:
        item._forceArtistInLabel = True
    add_media(items, content='songs', viewMode='albums')

@plugin.route('/favorite_album_add/<album_id>')
def favorite_album_add(album_id):
    tidalSession.favorites.do_action('add', tidalSession.get_album(album_id))

@plugin.route('/favorite_album_remove/<album_id>')
def favorite_album_remove(album_id):
    tidalSession.favorites.do_action('remove', tidalSession.get_album(album_id))

@plugin.route('/favorite_tracks')
def favorite_tracks():
    items = tidalSession.favorites.load_tracks()
    items.sort(key=lambda line: line.getSortField('artist'), reverse=False)
    add_media(items, content='songs', viewMode='tracks')

@plugin.route('/favorite_track_add/<track_id>')
def favorite_track_add(track_id):
    tidalSession.favorites.do_action('add', tidalSession.get_track(track_id))

@plugin.route('/favorite_track_remove/<track_id>')
def favorite_track_remove(track_id):
    tidalSession.favorites.do_action('remove', tidalSession.get_track(track_id))

@plugin.route('/favorite_videos')
def favorite_videos():
    items = tidalSession.favorites.load_videos()
    items.sort(key=lambda line: line.getSortField('artist'), reverse=False)
    add_media(items, content='musicvideos', viewMode='videos')

@plugin.route('/favorite_video_add/<video_id>')
def favorite_video_add(video_id):
    tidalSession.favorites.do_action('add', tidalSession.get_video(video_id))

@plugin.route('/favorite_video_remove/<video_id>')
def favorite_video_remove(video_id):
    tidalSession.favorites.do_action('remove', tidalSession.get_video(video_id))

#------------------------------------------------------------------------------
# Menu: TIDAL Folders
#------------------------------------------------------------------------------

@plugin.route('/folder/<group>')
def folder(group):
    xbmcplugin.setContent(plugin.handle, 'files')

    promoGroup = None
    if group == 'rising':
        promoGroup = 'RISING'
    elif group == 'discovery':
        promoGroup = 'DISCOVERY'
    elif group == 'featured':
        promoGroup = 'NEWS'

    items = tidalSession.get_folder_items(group)
    totalCount = 0
    for item in items:            
        totalCount += item._content_type_count

    if promoGroup and totalCount > 10:
        # Add Promotions as Folder
        add_directory(_T('Promotions'), plugin.url_for(promotion_group, group=promoGroup))
    
    if totalCount == 1 and item:
        if item.hasArtists:
            folder_content(group, item.path, 'artists', offset=0)
        if item.hasAlbums:
            folder_content(group, item.path, 'albums', offset=0)
        if item.hasPlaylists:
            folder_content(group, item.path, 'playlists', offset=0)
        if item.hasTracks:
            folder_content(group, item.path, 'tracks', offset=0)
        if item.hasVideos:
            folder_content(group, item.path, 'videos', offset=0)
        exit
    elif totalCount <= 20 and totalCount > len(items):
        for item in items:            
            add_folder_items(item, group, longLabel=True)
    else:
        for item in items:
            if item._content_type_count < 2:
                add_folder_items(item, group, groupAsLabel=True)
            else:
                add_directory(item, plugin.url_for(folder_item, group=group, path=item.path))

    if promoGroup and totalCount <= 10:
        # Add Promotions as single Items
        promoItems = tidalSession.get_promotions(promoGroup)
        if len(promoItems) > 0:
            add_media(promoItems, end=False)

    xbmcplugin.endOfDirectory(plugin.handle)
    setViewMode('files', 'folders')

@plugin.route('/folder/<group>/<path>')
def folder_item(group, path):
    xbmcplugin.setContent(plugin.handle, 'files')
    items = tidalSession.get_folder_items(group)
    for item in items:
        if item.path == path:
            add_folder_items(item, group)
    xbmcplugin.endOfDirectory(plugin.handle)
    setViewMode('files', 'folders')

def add_folder_items(item, group, longLabel=False, groupAsLabel=False):
    if item.hasArtists:
        item._otherLabel = '%s %s' % (_P(item.name), _T('Artists')) if longLabel else item.name if groupAsLabel else _T('Artists')
        add_directory(item, plugin.url_for(folder_content, group=group, path=item.path, content_type='artists', offset=0))
    if item.hasAlbums:
        item._otherLabel = '%s %s' % (_P(item.name), _T('Albums')) if longLabel else item.name if groupAsLabel else _T('Albums')
        add_directory(item, plugin.url_for(folder_content, group=group, path=item.path, content_type='albums', offset=0))
    if item.hasPlaylists:
        item._otherLabel = '%s %s' % (_P(item.name), _T('Playlists')) if longLabel else item.name if groupAsLabel else _T('Playlists')
        add_directory(item, plugin.url_for(folder_content, group=group, path=item.path, content_type='playlists', offset=0))
    if item.hasTracks:
        item._otherLabel = '%s %s' % (_P(item.name), _T('Tracks')) if longLabel else item.name if groupAsLabel else _T('Tracks')
        add_directory(item, plugin.url_for(folder_content, group=group, path=item.path, content_type='tracks', offset=0))
    if item.hasVideos:
        item._otherLabel = '%s %s' % (_P(item.name), _T('Videos')) if longLabel else item.name if groupAsLabel else _T('Videos')
        add_directory(item, plugin.url_for(folder_content, group=group, path=item.path, content_type='videos', offset=0))

@plugin.route('/folder/<group>/<path>/<content_type>/<offset>')
def folder_content(group, path, content_type, offset):
    items = tidalSession.get_folder_content(group, path, content_type, offset=int('0%s' % offset))
    if content_type == 'artists':
        add_media(items, content='artist', viewMode='artists', withNextPage=True)
    elif content_type == 'albums':
        add_media(items, content='songs', viewMode='albums', withNextPage=True)
    elif content_type == 'playlists':
        add_media(items, content='songs', viewMode='playlists', withNextPage=True)
    elif content_type == 'tracks':
        add_media(items, content='songs', viewMode='tracks', withNextPage=True)
    elif content_type == 'videos':
        add_media(items, content='musicvideos', viewMode='videos', withNextPage=True)

#------------------------------------------------------------------------------
# Menu: Promotions
#------------------------------------------------------------------------------

@plugin.route('/promotions')
def promotions(): 
    items = tidalSession.get_promotions()
    add_media(items, content='songs', viewMode='playlists')

@plugin.route('/promotion_group/<group>')
def promotion_group(group):
    items = tidalSession.get_promotions(group)
    add_media(items, content='songs', viewMode='playlists')

#------------------------------------------------------------------------------
# Artist Page
#------------------------------------------------------------------------------

@plugin.route('/artist_view/<artist_id>')
def artist_view(artist_id):
    xbmcplugin.setContent(plugin.handle, 'songs')

    focusId = xbmcgui.Window().getFocusId()
    pos = xbmc.getInfoLabel('Container(%s).Position' % focusId)
    artist_name = xbmc.getInfoLabel('Container(%s).ListitemPosition(%s).Artist' % (focusId, pos))
    imageURL = None
    fanartURL = None
    artist = tidalSession.get_artist(artist_id)
    if artist: 
        artist_name = artist.name
        imageURL = artist._imageUrl
        fanartURL = artist._fanartUrl
    add_directory('---------- %s: %s ---------' % (_T('Artist'), artist_name), # artist_name.decode(__UTF8__)
                  plugin.url_for(artist_info, artist_id), color=settings.favoriteColor, image=imageURL, fanart=fanartURL, info=artist_name)

    add_directory(_T('Top Tracks of Artist'), plugin.url_for(artist_top, artist_id), image=imageURL, fanart=fanartURL, info=artist_name)
    add_directory(_T('Videos'), plugin.url_for(artist_videos, artist_id), image=imageURL, fanart=fanartURL, info=artist_name)
    add_directory(_T('Artist Radio'), plugin.url_for(artist_radio, artist_id), image=imageURL, fanart=fanartURL, info=artist_name)
    add_directory(_T('Artist Playlists'), plugin.url_for(artist_playlists, artist_id), image=imageURL, fanart=fanartURL, info=artist_name)
    add_directory(_T('Similar Artists'), plugin.url_for(artist_similar, artist_id), image=imageURL, fanart=fanartURL, info=artist_name)

    if tidalSession.is_logged_in:
        if artist._isFavorite:
            add_directory(_T('Remove from Favorite Artists'), plugin.url_for(favorite_artist_remove, artist_id), image=imageURL, fanart=fanartURL, info=artist_name, isFolder=False)
        else:
            add_directory(_T('Add to Favorite Artists'), plugin.url_for(favorite_artist_add, artist_id), image=imageURL, fanart=fanartURL, info=artist_name, isFolder=False)

    albums = tidalSession.get_artist_albums(artist_id) + \
             tidalSession.get_artist_albums_ep_singles(artist_id) + \
             tidalSession.get_artist_albums_other(artist_id)
    add_media(albums)
    setViewMode('songs', 'albums')

@plugin.route('/artist_info/<artist_id>')
def artist_info(artist_id):
    focusId = xbmcgui.Window().getFocusId()
    pos = xbmc.getInfoLabel('Container(%s).Position' % focusId)
    artistName = xbmc.getInfoLabel('Container(%s).ListitemPosition(%s).Artist' % (focusId, pos))
    fanartURL = xbmc.getInfoLabel('Container(%s).ListitemPosition(%s).Art(fanart)' % (focusId, pos))
    thumbURL = xbmc.getInfoLabel('Container(%s).ListitemPosition(%s).Art(thumb)' % (focusId, pos))
    bio = tidalSession.get_artist_bio(artist_id)
    if bio:
        xbmcplugin.setContent(plugin.handle, 'files')
        summary = bio.get('summary')
        if summary:
            summary = textwrap.wrap(summary, width=80)
            if len(summary) > 0:
                add_directory(_T('Summary'), plugin.url_for(do_nothing), image=thumbURL, fanart=fanartURL, info=artistName, color=settings.favoriteColor, isFolder=False)
            for line in summary:
                add_directory(line, plugin.url_for(do_nothing), image=thumbURL, fanart=fanartURL, info=artistName, color=False, isFolder=False)
        text = bio.get('text')
        if text:
            text = textwrap.wrap(text, width=80)
            if len(text) > 0:
                add_directory(_T('Biography'), plugin.url_for(do_nothing), image=thumbURL, fanart=fanartURL, info=artistName, color=settings.favoriteColor, isFolder=False)
            for line in text:
                add_directory(line, plugin.url_for(do_nothing), image=thumbURL, fanart=fanartURL, info=artistName, color=False, isFolder=False)
        xbmcplugin.endOfDirectory(plugin.handle)
        setViewMode('files', 'folders')

@plugin.route('/artist_top/<artist_id>')
def artist_top(artist_id):
    items = tidalSession.get_artist_top_tracks(artist_id)
    add_media(items, content='songs', viewMode='tracks')

@plugin.route('/artist_videos/<artist_id>')
def artist_videos(artist_id):
    items = tidalSession.get_artist_videos(artist_id)
    add_media(items, content='musicvideos', viewMode='videos')

@plugin.route('/video_artist_view/<video_id>')
def video_artist_view(video_id):
    # Go to the artist page of the video artist
    item = tidalSession.get_video(video_id)
    if item.artist:
        artist_view(artist_id=item.artist.id)

@plugin.route('/artist_radio/<artist_id>')
def artist_radio(artist_id):
    items = tidalSession.get_artist_radio(artist_id)
    add_media(items, content='songs', viewMode='tracks')

@plugin.route('/artist_playlists/<artist_id>')
def artist_playlists(artist_id):
    items = tidalSession.get_artist_playlists(artist_id)
    add_media(items, content='songs', viewMode='playlists')

@plugin.route('/artist_similar/<artist_id>')
def artist_similar(artist_id):
    artists = tidalSession.get_artist_similar(artist_id)
    add_media(artists, content='artists', viewMode='artists')

#------------------------------------------------------------------------------
# Album View
#------------------------------------------------------------------------------

@plugin.route('/album_view/<album_id>')
def album_view(album_id):
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
    items = tidalSession.get_album_tracks(album_id)    
    add_media(items, content='songs', viewMode='tracks')
    xbmc.executebuiltin('Container.SetSortMethod(8)') # set SORT_METHOD_TRACKNUM

#------------------------------------------------------------------------------
# Playlist View
#------------------------------------------------------------------------------

@plugin.route('/playlist_view/<item_type>/<playlist_id>')
def playlist_view(item_type, playlist_id):
    playlist = tidalSession.get_playlist(playlist_id)
    if playlist:
        viewMode = 'tracks'
        if item_type == 'videos':
            viewMode = 'videos'
        if item_type == 'playlistitems':
            if playlist.numberOfVideos > 0:
                add_directory(_T('Tracks only'), plugin.url_for(playlist_view, item_type='tracks', playlist_id=playlist.id), image=playlist._imageUrl, fanart=playlist._fanartUrl)
            if playlist.numberOfTracks > 0 and playlist.numberOfVideos > 0:
                add_directory(_T('Videos only'), plugin.url_for(playlist_view, item_type='videos', playlist_id=playlist.id), image=playlist._imageUrl, fanart=playlist._fanartUrl)
        items = tidalSession.get_playlist_items(playlist=playlist, ret=item_type)
        add_media(items, content='musicvideos' if item_type == 'videos' else 'songs', viewMode=viewMode)

#------------------------------------------------------------------------------
# Track Functions
#------------------------------------------------------------------------------

@plugin.route('/track_radio/<track_id>')
def track_radio(track_id):
    items = tidalSession.get_track_radio(track_id)
    add_media(items, content='songs', viewMode='tracks')

@plugin.route('/recommended_items/<item_type>/<item_id>')
def recommended_items(item_type, item_id):
    items = tidalSession.get_recommended_items(item_type, item_id)
    add_media(items, content='songs', viewMode='tracks')

@plugin.route('/play_track/<track_id>')
def play_track(track_id):
    media = tidalSession.get_music_url(track_id)
    if media:
        li = ListItem(path=media._stream_url)
        li.setProperty('mimetype', media._mimetype)
        try:
            xbmcplugin.setResolvedUrl(plugin.handle, True, li)
        except:
            pass

@plugin.route('/track_not_available/<track_id>')
def track_not_available(track_id):
    pass

#------------------------------------------------------------------------------
# Video Functions
#------------------------------------------------------------------------------

@plugin.route('/play_video/<video_id>')
def play_video(video_id):
    media = tidalSession.get_video_url(video_id)
    if media:
        li = ListItem(path=media._stream_url)
        li.setProperty('mimetype', media._mimetype)
        try:
            xbmcplugin.setResolvedUrl(plugin.handle, True, li)
        except:
            pass

@plugin.route('/video_not_available/<video_id>')
def video_not_available(video_id):
    pass

#------------------------------------------------------------------------------
# Menu: Search
#------------------------------------------------------------------------------

@plugin.route('/search')
def search():
    xbmcplugin.setContent(plugin.handle, 'files')
    add_directory(_T('Search all'), plugin.url_for(search_type, field='all'), isFolder=False)
    add_directory(_T('Artist'), plugin.url_for(search_type, field='artists'), isFolder=False)
    add_directory(_T('Album'), plugin.url_for(search_type, field='albums'), isFolder=False)
    add_directory(_T('Playlist'), plugin.url_for(search_type, field='playlists'), isFolder=False)
    add_directory(_T('Track'), plugin.url_for(search_type, field='tracks'), isFolder=False)
    add_directory(_T('Video'), plugin.url_for(search_type, field='videos'), isFolder=False)
    xbmcplugin.endOfDirectory(plugin.handle)
    setViewMode('files', 'folders')

@plugin.route('/search_type/<field>')
def search_type(field):
    keyboard = xbmc.Keyboard('', _T('Search'))
    keyboard.doModal()
    if keyboard.isConfirmed():
        keyboardinput = keyboard.getText()
        if keyboardinput:
            xbmc.executebuiltin('Container.Update(%s, True)' % plugin.url_for(search_exec, field=field, text=urllib.quote_plus(keyboardinput)))

@plugin.route('/search_edit/<field>/<text>')
def search_edit(field, text):
    s_text = urllib.unquote_plus(text).decode('utf-8')
    keyboard = xbmc.Keyboard(s_text, _T('Search'))
    keyboard.doModal()
    if keyboard.isConfirmed():
        keyboardinput = keyboard.getText()
        if keyboardinput:
            xbmc.executebuiltin('Container.Update(%s, True)' % plugin.url_for(search_exec, field=field, text=urllib.quote_plus(keyboardinput)))

@plugin.route('/search_exec/<field>/<text>')
def search_exec(field, text):
    # Unquote special Characters
    s_field = urllib.unquote_plus(field).decode('utf-8')
    s_text = urllib.unquote_plus(text).decode('utf-8')
    results = tidalSession.search(s_field, s_text, limit=50 if s_field.upper() == 'ALL' else 100)
    add_directory(_T('Search again'), plugin.url_for(search_edit, field=field, text=text), isFolder=False)
    add_search_result(results, sort='match', reverse=True, end=True)
    
#------------------------------------------------------------------------------
# MAIN Program of the Plugin
#------------------------------------------------------------------------------

if __name__ == '__main__':
    try:
        plugin.run()
        tidalSession.close()
        debug.killDebugThreads()
    except HTTPError as e:
        if e.response.status_code in [401, 403]:
            dialog = xbmcgui.Dialog()
            dialog.notification(plugin.name, _T('Authorization problem'), xbmcgui.NOTIFICATION_ERROR)
        traceback.print_exc()

# End of File