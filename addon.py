# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Thomas Amland
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

import xbmc, xbmcgui, xbmcaddon, xbmcplugin, sys
from xbmcgui import ListItem
from requests import HTTPError
from lib import wimpy
from lib.wimpy.models import Album, Artist
from lib.wimpy import Quality
from routing import Plugin

plugin = Plugin()
addon = xbmcaddon.Addon()

quality = [Quality.lossless, Quality.high, Quality.low][int('0'+addon.getSetting('quality'))]
config = wimpy.Config(
    session_id=addon.getSetting('session_id'),
    country_code=addon.getSetting('country_code'),
    user_id=addon.getSetting('user_id'),
    api=wimpy.TIDAL_API if addon.getSetting('site') == '1' else wimpy.WIMP_API,
    quality=quality,
)
wimp = wimpy.Session(config)


def view(data_items, urls, end=True):
    list_items = []
    for item, url in zip(data_items, urls):
        li = ListItem(item.name)
        info = {'title': item.name}
        if isinstance(item, Album):
            info.update({'album': item.name, 'artist': item.artist.name})
        elif isinstance(item, Artist):
            info.update({'artist': item.name})
        li.setInfo('music', info)
        li.setThumbnailImage(item.image)
        list_items.append((url, li, True))
    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    if end:
        xbmcplugin.endOfDirectory(plugin.handle)


def track_list(tracks):
    xbmcplugin.setContent(plugin.handle, 'songs')
    list_items = []
    for track in tracks:
        if not track.available:
            continue
        url = plugin.url_for(play, track_id=track.id)
        li = ListItem(track.name)
        li.setProperty('isplayable', 'true')
        li.setInfo('music', {
            'title': track.name,
            'tracknumber': track.track_num,
            'discnumber': track.disc_num,
            'artist': track.artist.name,
            'album': track.album.name})
        if track.album:
            li.setThumbnailImage(track.album.image)
        radio_url = plugin.url_for(track_radio, track_id=track.id)
        li.addContextMenuItems(
            [('Track Radio', 'XBMC.Container.Update(%s)' % radio_url,)])
        list_items.append((url, li, False))
    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    xbmcplugin.endOfDirectory(plugin.handle)


def add_directory(title, view_func, **kwargs):
    xbmcplugin.addDirectoryItem(
        plugin.handle, plugin.url_for(view_func, **kwargs), ListItem(title), True)


def urls_from_id(view_func, items):
    return [plugin.url_for(view_func, item.id) for item in items]


@plugin.route('/')
def root():
    add_directory('My music', my_music)
    add_directory('Featured Playlists', promotions)
    add_directory("What's New", whats_new)
    add_directory('Genres', genres)
    add_directory('Moods', moods)
    add_directory('Search', search)
    add_directory('Login', login)
    add_directory('Logout', logout)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/track_radio/<track_id>')
def track_radio(track_id):
    track_list(wimp.get_track_radio(track_id))


@plugin.route('/moods/<mood>')
def moods_playlists(mood):
    items = wimp.get_mood_playlists(mood)
    view(items, urls_from_id(playlist_view, items))


@plugin.route('/moods')
def moods():
    items = wimp.get_moods()
    for mood in items:
        add_directory(mood['name'], moods_playlists, mood=mood['path'])
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/genres')
def genres():
    items = wimp.get_genres()
    for item in items:
        add_directory(item['name'], genre, _genre=item['path'])
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/genre/<_genre>')
def genre(_genre):
    add_directory('Playlists', genre_playlists, _genre=_genre)
    add_directory('Albums', genre_albums, _genre=_genre)
    add_directory('Tracks', genre_tracks, _genre=_genre)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/genre/<_genre>/playlists')
def genre_playlists(_genre):
    items = wimp.get_genre_items(_genre, 'playlists')
    view(items, urls_from_id(playlist_view, items))


@plugin.route('/genre/<_genre>/albums')
def genre_albums(_genre):
    items = wimp.get_genre_items(_genre, 'albums')
    view(items, urls_from_id(album_view, items))


@plugin.route('/genre/<_genre>/tracks')
def genre_tracks(_genre):
    items = wimp.get_genre_items(_genre, 'tracks')
    track_list(items)


@plugin.route('/promotions')
def promotions():
    items = wimp.get_featured()
    view(items, urls_from_id(playlist_view, items))


@plugin.route('/featured/tracks/<_type>')
def featured_tracks(_type):
    items = wimp.get_recommended_new_top('tracks', _type)
    track_list(items)


@plugin.route('/featured/playlists/<_type>')
def featured_playlists(_type):
    items = wimp.get_recommended_new_top('playlists', _type)
    view(items, urls_from_id(playlist_view, items))


@plugin.route('/featured/albums/<_type>')
def featured_albums(_type):
    items = wimp.get_recommended_new_top('albums', _type)
    view(items, urls_from_id(album_view, items))


@plugin.route('/whats_new')
def whats_new():
    add_directory('New Playlists', featured_playlists, _type='new')
    add_directory(
        'Recommended Playlists', featured_playlists, _type='recommended')
    add_directory('New Albums', featured_albums, _type='new')
    add_directory('Top Albums', featured_albums, _type='top')
    add_directory('Recommended Albums', featured_albums, _type='recommended')
    add_directory('New Tracks', featured_tracks, _type='new')
    add_directory('Top Tracks', featured_tracks, _type='top')
    add_directory('Recommended Tracks', featured_tracks, _type='recommended')
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/my_music')
def my_music():
    add_directory('My Playlists', my_playlists)
    add_directory('Favourite Playlists', favourite_playlists)
    add_directory('Favourite Artists', favourite_artists)
    add_directory('Favourite Albums', favourite_albums)
    add_directory('Favourite Tracks', favourite_tracks)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/not_implemented')
def not_implemented():
    raise NotImplementedError()


@plugin.route('/album/<album_id>')
def album_view(album_id):
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    track_list(wimp.get_album_tracks(album_id))


@plugin.route('/artist/<artist_id>')
def artist_view(artist_id):
    xbmcplugin.setContent(plugin.handle, 'albums')
    xbmcplugin.addDirectoryItem(
        plugin.handle, plugin.url_for(top_tracks, artist_id),
        ListItem('Top Tracks'), True
    )
    xbmcplugin.addDirectoryItem(
        plugin.handle, plugin.url_for(artist_radio, artist_id),
        ListItem('Artist Radio'), True
    )
    xbmcplugin.addDirectoryItem(
        plugin.handle, plugin.url_for(similar_artists, artist_id),
        ListItem('Similar Artists'), True
    )
    albums = wimp.get_artist_albums(artist_id) + \
             wimp.get_artist_albums_ep_singles(artist_id) + \
             wimp.get_artist_albums_other(artist_id)
    view(albums, urls_from_id(album_view, albums))


@plugin.route('/artist/<artist_id>/radio')
def artist_radio(artist_id):
    track_list(wimp.get_artist_radio(artist_id))


@plugin.route('/artist/<artist_id>/top')
def top_tracks(artist_id):
    track_list(wimp.get_artist_top_tracks(artist_id))


@plugin.route('/artist/<artist_id>/similar')
def similar_artists(artist_id):
    xbmcplugin.setContent(plugin.handle, 'artists')
    artists = wimp.get_artist_similar(artist_id)
    view(artists, urls_from_id(artist_view, artists))


@plugin.route('/playlist/<playlist_id>')
def playlist_view(playlist_id):
    track_list(wimp.get_playlist_tracks(playlist_id))


@plugin.route('/user_playlists')
def my_playlists():
    items = wimp.user.playlists()
    view(items, urls_from_id(playlist_view, items))


@plugin.route('/favourite_playlists')
def favourite_playlists():
    items = wimp.user.favorites.playlists()
    view(items, urls_from_id(playlist_view, items))


@plugin.route('/favourite_artists')
def favourite_artists():
    xbmcplugin.setContent(plugin.handle, 'artists')
    items = wimp.user.favorites.artists()
    view(items, urls_from_id(artist_view, items))


@plugin.route('/favourite_albums')
def favourite_albums():
    xbmcplugin.setContent(plugin.handle, 'albums')
    items = wimp.user.favorites.albums()
    view(items, urls_from_id(album_view, items))


@plugin.route('/favourite_tracks')
def favourite_tracks():
    track_list(wimp.user.favorites.tracks())


@plugin.route('/search')
def search():
	add_directory('Artist', searchtype, _search='artist')
	add_directory('Album', searchtype, _search='album')
	add_directory('Playlist', searchtype, _search='playlist')
	add_directory('Track', searchtype, _search='track')
	xbmcplugin.endOfDirectory(plugin.handle)

	
@plugin.route('/search/<_search>')
def searchtype(_search):
	keyboard = xbmc.Keyboard('', 'Search')
	keyboard.doModal()
	if keyboard.isConfirmed():
		result = keyboard.getText()
		res = wimp.search(_search, result)
		view(res.artists, urls_from_id(artist_view, res.artists), end=False)
		view(res.albums, urls_from_id(album_view, res.albums), end=False)
		view(res.playlists, urls_from_id(playlist_view, res.playlists), end=False)
		track_list(res.tracks)


@plugin.route('/login')
def login():
    username = addon.getSetting('username')
    password = addon.getSetting('password')

    if not username or not password:
        # Ask for username/password
        dialog = xbmcgui.Dialog()
        username = dialog.input('Username')
        if not username:
            return
        password = dialog.input('Password', option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if not password:
            return

    if wimp.login(username, password):
        addon.setSetting('session_id', wimp.session_id)
        addon.setSetting('country_code', wimp.country_code)
        addon.setSetting('user_id', unicode(wimp.user.id))


@plugin.route('/logout')
def logout():
    addon.setSetting('session_id', '')
    addon.setSetting('country_code', '')
    addon.setSetting('user_id', '')


@plugin.route('/play/<track_id>')
def play(track_id):
    media_url = wimp.get_media_url(track_id)
    if not media_url.startswith('http://') and not media_url.startswith('https://'):
        host, app, playpath = media_url.split('/', 3)
        media_url = 'rtmp://%s app=%s playpath=%s' % (host, app, playpath)
    li = ListItem(path=media_url)
    mimetype = 'audio/flac' if quality == Quality.lossless else 'audio/mpeg'
    li.setProperty('mimetype', mimetype)
    xbmcplugin.setResolvedUrl(plugin.handle, True, li)


def handle_errors(f):
    try:
        f()
    except HTTPError as e:
        if e.response.status_code in [401, 403]:
            dialog = xbmcgui.Dialog()
            dialog.notification(addon.getAddonInfo('name'), "Unauthorized", xbmcgui.NOTIFICATION_ERROR)
        else:
            raise e

if __name__ == '__main__':
    handle_errors(plugin.run)
