# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Arne Svenson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import debug
from .config import addon, settings

#------------------------------------------------------------------------------
# Texts
#------------------------------------------------------------------------------

__STRINGS__ = {
           
    # Login
    'Username':                 30001,
    'Password':                 30002,

    # Global texts           
    'Artist':                   30101,
    'Album':                    30102,
    'Playlist':                 30103,
    'Track':                    30104,
    'Video':                    30105,
    'Artists':                  30106,
    'Albums':                   30107,
    'Playlists':                30108,
    'Tracks':                   30109,
    'Videos':                   30110,
    'Info':                     30111,
    'Error':                    30112,
    'Stream Not Ready':         30113,
    'Warning':                  30114,
    'Attention':                30115,
    'Switching down to HIGH quality': 30116,
    'File save error':          30117,
    'Album Year':               30118,
    'Album Artist':             30119,
    'Movies':                   30120,
    'Shows':                    30121,

    # Main Menu
    'My Music':                 30201,
    'Promotions':               30202,
    "What's New":               30203,
    'Genres':                   30204,
    'Moods':                    30205,
    'Search':                   30206,
    'Logout':                   30207,
    'Login':                    30208,
    'Remember login details?':  30209,   
    'Authorization problem':    30210,
    'TIDAL Rising':             30211,
    'TIDAL Discovery':          30212,
    'Search again':             30213,
    'Not logged in - Trial Mode active !': 30214,
    'Trial Mode':               30215,
    
    # Context Menu Items
    'Open this':                30219,
    'Play this':                30220,
    'Remove from Favorites':    30221,
    'Add to Favorites':         30222,
    'Show Artist':              30223,
    'Delete Playlist':          30224,
    'Track Radio':              30225,
    'Show Album':               30226,
    'Add to Playlist ...':      30227,
    'Remove from Playlist':     30228,
    'Addon Settings':           30229,
    'Extras ...':               30230,

    # User Menu
    'My Playlists':             30231,
    'Favorite Playlists':       30232,
    'Favorite Artists':         30233,
    'Favorite Albums':          30234,
    'Favorite Tracks':          30235,
    'Create new Playlist':      30236,
    'Name of new Playlist':     30237,
    'Description (optional)':   30238,
    'Playlist not found':       30239,
    'Delete Playlist ?':        30240,
    'Are you sure to delete the playlist "%s" ?': 30241,
    'Playlist "%s" contains %s items. Are you really sure to delete this playlist ?': 30242,
    'Playlist deleted':         30243,
    'API Call Failed':          30244,
    'Choose Playlist':          30245,
    'Item added':               30246,
    'Remove from Playlist ?':   30247,
    'Are you sure to remove item number %s from this playlist ?': 30248,
    'Entry removed':            30249,
    'Add Favorite ?':           30250,
    'Remove Favorite ?':        30251,
    'Unknown type of Favorite': 30252,
    'Add {kind} "{name}" to Favorites ?': 30253,
    'Remove {kind} "{name}" from Favorites ?': 30254,
    'added':                    30255,
    'removed':                  30256,
    '{kind} with id {id} not found': 30257,
    'Show Playlist':            30258,
    'Search all':               30259,
    'Move to other Playlist':   30260,
    'Item moved':               30261,
    'Favorite Videos':          30262,
    'Set as Default %s Playlist':  30263,
    'Reset Default %s Playlist':   30264,
    'Add Item to Playlist "%s" ?': 30265,
    'Remove Item from Playlist "%s" ?': 30266,
    'Tracks only':              30267,
    'Videos only':              30268,
    'Track Recommendations':    30269,
    'Video Recommendations':    30270,
    'Playlist created':         30271,
    'User Info':                30272,
    'Export {what}':            30273,
    'Import {what}':            30274,
    '{n} exported':             30275,
    '{n} imported':             30276,
    'Next Page ({pos1}-{pos2})': 30277,
    '%s Albums not loaded':     30278,

    # Artist Page
    'Artist Radio':             30301,
    'Artist Playlists':         30302,
    'Similar Artists':          30303,
    'Remove from Favorite Artists': 30304,
    'Add to Favorite Artists':  30305,
    'Summary':                  30306,
    'Biography':                30307,
    'Top Tracks of Artist':     30308,

}

__PLURALS__ = {
               
    'Neu':                      'Neue',
    'Deutsch':                  'Deutsche',
    'Exklusiv':                 'Exklusive',
    'Empfohlen':                'Empfohlene'

}

#------------------------------------------------------------------------------
# Redefinition of '_' for localized Strings
#------------------------------------------------------------------------------
def _T(string_id):
    try:
        if string_id in __STRINGS__:
            text = addon.getLocalizedString(__STRINGS__[string_id])
            if not text:
                text = '%s: %s' % (__STRINGS__[string_id], string_id)
            return text
        else:
            if settings.debug:
                debug.log('String is missing: %s' % string_id)
                return '?: %s' % string_id
            return string_id
    except:
        return '?: %s' % string_id

def _P(string_id):
    try:
        if string_id in __PLURALS__:
            return __PLURALS__[string_id]
        else:
            return string_id
    except:
        if settings.debug:
            return '?: %s' % string_id
        return string_id

# End of File