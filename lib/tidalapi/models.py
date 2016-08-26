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
from datetime import datetime
import xbmc
from xbmcgui import ListItem

import debug
from .iso8601 import iso8601
from .config import settings, CONST, ImgSize, MusicQuality, SubscriptionType
from .all_strings import _T

#------------------------------------------------------------------------------
# UserInfo
#------------------------------------------------------------------------------

class UserInfo(object):
    ''' User Informations:
        "id": 12345678,
        "username": "username",
        "firstName": "Firstname",
        "lastName": "Lastnamen",
        "email": "email@host.name",
        "created": "2015-05-11T19:36:11.692+0000",
        "picture": null,
        "newsletter": true,
        "gender": "m",
        "dateOfBirth": "1981-10-01",
        "facebookUid": 0
    '''
    id = ''
    username = ''
    firstName = ''
    lastName = ''
    email = ''
    created = None
    picture = None
    newsletter = False
    gender = 'm'
    dateOfBirth = None
    facebookUid = '0'
    subscription = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.id = '%s' % self.id  # convert numeric ID to string
        if self.created:
            self.created = iso8601.parse_date(self.created)
        if self.dateOfBirth:
            self.dateOfBirth = iso8601.parse_date(self.dateOfBirth)
        self.facebookUid = '%s' % self.facebookUid


class SubscriptionInfo(object):
    ''' Subscription Informations:
        "validUntil": "2016-09-08T19:37:12.095+0000",
        "status": "ACTIVE",
        "subscription": {"type":"HIFI",              # HIFI, PREMIUM, FREE 
                         "offlineGracePeriod":30},
        "highestSoundQuality": "LOSSLESS",
        "premiumAccess": true,
        "canGetTrial": false,
        "paymentType": "PAYPAL_REF"
    '''
    subscription = {'type':'HIFI'}
    subscriptionType = SubscriptionType.premium
    status = 'ACTIVE'
    validUntil = None
    highestSoundQuality = 'LOSSLESS'
    premiumAccess = True
    canGetTrial = False
    paymentType = ''
    
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        try:
            if self.subscription.get('type') == 'HIFI':
                self.subscriptionType = SubscriptionType.hifi
            elif self.subscription.get('type') == 'PREMIUM':
                self.subscriptionType = SubscriptionType.premium
            elif self.subscription.get('type') == 'FREE':
                self.subscriptionType = SubscriptionType.free
        except:
            debug.log('SubscriptionType not resolved !', xbmc.LOGERROR)
            self.subscriptionType = SubscriptionType.hifi
        if self.validUntil:
            self.validUntil = iso8601.parse_date(self.validUntil)    
    
#------------------------------------------------------------------------------
# BaseItem
#------------------------------------------------------------------------------

class BaseItem(object):

    # Mapped Properties
    id = None
    uuid = None

    # internal Properties
    _isFavorite = False
    _labelColor = None

    _itemPosition = 0
    _offset = 0
    _totalNumberOfItems = 0

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        if self.id:
            self.id = '%s' % self.id  # convert numeric ID to string
        else:
            self.id = self.uuid       # for Playlist data in a BaseItem

    def getSortField(self, field='name'):
        return self.id

    @property
    def _label(self):
        return self.getLabel(colored=True)

    def getLabel(self, colored=True):
        return self.id

    @property
    def _coloredLabel(self):
        label = self._label
        if not self._playable and settings.notPlayableColor:
            label = '[COLOR %s]%s (%s)[/COLOR]' % (settings.notPlayableColor, label, _T('Stream Not Ready'))
        elif sys.argv[0].find('favorite') >= 0:
            return label
        elif self._labelColor:
            label = '[COLOR %s]%s[/COLOR]' % (self._labelColor, label)
        elif self._isFavorite and settings.favoriteColor:
            label = '[COLOR %s]%s[/COLOR]' % (settings.favoriteColor, label)
        return label

    @property
    def _playable(self):
        return True

    @property
    def _imageUrl(self):
        return None

    @property
    def _fanartUrl(self):
        return None

    def getComments(self):
        return []

    def getListItem(self):
        return ListItem(label=self._coloredLabel, iconImage=self._imageUrl, thumbnailImage=self._imageUrl )

    def addExplicit(self, text):
        if text.find('Explicit') == -1:
            return unicode.format(CONST.explicitMask, label=text)
        return text

#------------------------------------------------------------------------------
# Class ArtistItem
#------------------------------------------------------------------------------

class ArtistItem(BaseItem):
    ''' All Information of an Artist:
        'id': 4332277,
        'name': u'Ariana Grande'
        'picture': u'49bc9621-4426-455a-9300-450b9fe1bd4e',
        'url': u'http://www.tidal.com/artist/4332277',
    '''
    # Mapped Properties
    name = None
    picture = None
    url = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        if self.id == None:
            self.id = CONST.artistIdVariousArtists
        if self.name == None:
            self.name = 'Unknown'
        self.id = '%s' % self.id  # Convert numeric to string

    def getSortField(self, field='name'):
        return self.name

    def getLabel(self, colored=True):
        return self.name

    @property
    def _imageUrl(self):
        if self.picture:
            return CONST.profilePictureUrl.format(picture=self.picture.replace('-', '/'), size=ImgSize.artist[1])
        return settings.addon_icon

    @property
    def _fanartUrl(self):
        if self.picture:
            return CONST.profilePictureUrl.format(picture=self.picture.replace('-', '/'), size=ImgSize.artist[6])
        return CONST.artistImageURL.format(width=1080, height=720, artistid=self.id)

    def getListItem(self):
        li = BaseItem.getListItem(self)
        li.setInfo('music', {
            'artist': self.name,
            'comment': ', '.join(self.getComments())
        })
        if settings.showFanart and self._fanartUrl:
            li.setArt({'fanart': self._fanartUrl})
        return li

#------------------------------------------------------------------------------
# Class AlbumItem
#------------------------------------------------------------------------------

class AlbumItem(BaseItem):
    ''' Album Informations:
        'id': 17953403
        'title': u'Girl On Fire',
        'artist': {u'type': u'MAIN', u'id': 1552, u'name': u'Alicia Keys'},
        'artists': [{u'type': u'MAIN', u'id': 1552, u'name': u'Alicia Keys'}],
        'numberOfTracks': 13,
        'numberOfVolumes': 1,
        'duration': 3188,
        'type': u'ALBUM',
        'copyright': u'(P) 2012 RCA Records, a division of Sony Music Entertainment',
        'streamStartDate': u'2012-11-23T00:00:00.000+0000',
        'url': u'http://www.tidal.com/album/17953403',
        'explicit': False,
        'allowStreaming': True,
        'cover': u'f05bf614-60ba-4fa4-a535-e4be3d2cf28c',
        'premiumStreamingOnly': False,
        'releaseDate': u'2012-11-23',
        'version': None,
        'streamReady': True,
    '''
    # Mapped Properties
    title = 'Unknown'
    artist = ArtistItem()
    artists = []    # All Artists
    numberOfTracks = 1
    numberOfVolumes = 1
    duration = -1
    allowStreaming = True
    streamReady = True
    premiumStreamingOnly = False
    streamStartDate = None
    releaseDate = None
    cover = None
    type = 'ALBUM'
    explicit = False
    version = None
    
    # internal Properties
    _ftArtists = []  # All artists except main (filled by parser)
    _forceArtistInLabel = False
    _compilation = False
    
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.id = '%s' % self.id  # Convert numeric to string
        if self.releaseDate:
            self.releaseDate = iso8601.parse_date(self.releaseDate)
        if self.streamStartDate:
            self.streamStartDate = iso8601.parse_date(self.streamStartDate)

    def getSortField(self, field='artist'):
        if field == 'date':
            if self.releaseDate:
                return self.releaseDate 
            if self.streamStartDate:
                return self.streamStartDate 
            return datetime.now() 
        elif field == 'title' or field == 'name' or not self.artist:
            return self.title
        return '%s - %s' % (self.artist.name, self.title)

    @property
    def _playable(self):
        return self.allowStreaming

    def getLabel(self, colored=True):
        albumType = '[%s] ' % self.type if settings.showAlbumType and self.type else ''
        withYear = ' (%s)' % self._year if self._year else ''
        if self.isArtistInLabel():
            artistName = self.artist.getLabel(colored) if self._isFavorite or not colored or not self._playable else self.artist._coloredLabel
            text = '%s%s - %s' % (albumType, artistName, self.title)
        else:
            text = '%s%s' % (albumType, self.title)
        if self.explicit:
            text = self.addExplicit(text)
        return '%s%s' % (text, withYear)
    
    @property
    def _year(self):
        year = None
        if self.releaseDate:
            year = self.releaseDate.year
        elif self.streamStartDate:
            year = self.streamStartDate.year
        return year

    @property
    def _imageUrl(self):
        if self.cover:
            return CONST.profilePictureUrl.format(picture=self.cover.replace('-', '/'), size=ImgSize.album[3])
        return settings.addon_icon

    @property
    def _fanartUrl(self):
        if self.artist and isinstance(self.artist, ArtistItem):
            return self.artist._fanartUrl
        elif self.cover:
            return CONST.profilePictureUrl.format(picture=self.cover.replace('-', '/'), size=ImgSize.album[4])
        return settings.addon_fanart

    def isCompilation(self):
        return self._compilation

    def isArtistInLabel(self):
        return self.type == 'EP' or self._forceArtistInLabel
    
    def getFtArtistsText(self):
        text = ''
        for item in self._ftArtists:
            if len(text) > 0:
                text = text + ', '
            text = text + item.name
        if len(text) > 0:
            text = 'ft. by ' + text
        return text

    def getComments(self):
        comments = []
        comment = self.getFtArtistsText()
        if comment:
            comments.append(comment)
        if settings.log_details > 1:
            comments.append('album_id=%s' % self.id)
        return comments
    
    def getListItem(self):
        li = BaseItem.getListItem(self)
        li.setInfo('music', {
            'artist': self.artist.name if self.artist else self._label,
            'album': self.title,
            'genre': self.getFtArtistsText(),    # to show this in MediaInfo Window
            'comment': ', '.join(self.getComments()),
            'year': self._year,
        })
        if settings.showFanart and self._fanartUrl:
            li.setArt({'fanart': self._fanartUrl})
        return li

#------------------------------------------------------------------------------
# Class AlbumReview
#------------------------------------------------------------------------------

class AlbumReview():
    ''' "source": "TIDAL",
        "lastUpdated": "2015-11-25T12:27:50.366+0000",
        "text": "Reprising the transcendent themes of her mega-hit, 21, Adele's gigantic third album (and first in five years) features production from Danger Mouse and Ariel Rechtshaid and co-writing from Max Martin and Tobias Jesso Jr.",
        "summary": "Reprising the transcendent themes of her mega-hit, 21, Adele's gigantic third album (and first in five years) features production from Danger Mouse and Ariel Rechtshaid and co-writing from Max Martin and Tobias Jesso Jr."
    '''
    # Mapped Properties
    source = 'TIDAL'
    lastUpdated = None
    text = ''
    summary = ''     
    
#------------------------------------------------------------------------------
# Class PlaylistItem
#------------------------------------------------------------------------------

class PlaylistItem(BaseItem):
    ''' Playlist Informations:
        'publicPlaylist': False,
        'description': u'',
        'numberOfTracks': 16,
        'numberOfVideos': 0,
        'creator': {u'id': 29874229},
        'url': u'http://www.tidal.com/playlist/244f03bb-1682-4ab3-8907-2a5dfeb42e06',
        'image': u'79897f86-83cf-47fb-9a84-2c1f86a7ca7e',
        'title': u'Alben 2015',
        'lastUpdated': u'2015-10-13T19:44:07.232+0000',
        'created': u'2015-10-13T19:43:33.411+0000',
        'duration': 3476,
        'type': u'USER', EDITORIAL, ARTIST
        'uuid': u'244f03bb-1682-4ab3-8907-2a5dfeb42e06'
    '''
    # Mapped Properties
    title = None
    description = None
    creator = None
    publicPlaylist = None
    created = None
    image = None
    lastUpdated = None
    numberOfTracks = 0
    numberOfVideos = 0
    duration = -1
    type = None

    # ETag of HTTP Response Header
    _etag = None
    _dummyTag = 'dummy'

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.id = self.uuid
        if self.created:
            self.created = iso8601.parse_date(self.created)
        if self.lastUpdated:
            self._dummyTag = self.lastUpdated
            self.lastUpdated = iso8601.parse_date(self.lastUpdated)

    def getSortField(self, field='name'):
        if field == 'date':
            if self.lastUpdated:
                return self.lastUpdated 
            if self.created:
                return self.created 
            return datetime.now() 
        return self.title

    def getLabel(self, colored=True):
        return self.title

    @property
    def _numberOfItems(self):
        return self.numberOfTracks + self.numberOfVideos

    @property
    def _year(self):
        if self.lastUpdated:
            return self.lastUpdated.year
        elif self.created:
            return self.created.year
        return None

    @property
    def _imageUrl(self):
        if self.image:
            if self.type == 'USER':
                return CONST.userPlaylistFanartUrl.format(width=512, height=512, uuid=self.uuid, cols=3, rows=3, dummy=self._dummyTag)
            else:
                return CONST.profilePictureUrl.format(picture=self.image.replace('-', '/'), size=ImgSize.playlist[1])
        return settings.addon_icon

    @property
    def _fanartUrl(self):
        if self.image:
            if self.type == 'USER':
                return CONST.userPlaylistFanartUrl.format(width=1080, height=720, uuid=self.uuid, cols=4, rows=3, dummy=self._dummyTag)
            else:
                return CONST.profilePictureUrl.format(picture=self.image.replace('-', '/'), size=ImgSize.playlist[2])
        return settings.addon_fanart

    def getListItem(self):
        li = BaseItem.getListItem(self)
        li.setInfo('music', {
            'artist': self.title,
            'album': self.description,
            'year': self._year,
            'title': 'Tracks:%s / Videos:%s' % (self.numberOfTracks, self.numberOfVideos),
            'comment': ', '.join(self.getComments())
        })
        if settings.showFanart and self._fanartUrl:
            li.setArt({'fanart': self._fanartUrl})
        return li

#------------------------------------------------------------------------------
# Class PlayableItem
#------------------------------------------------------------------------------

class PlaylistPosItem(BaseItem):

    # Internal Properties
    _user_playlist_id = None    # Id of the user playlist containing this track/video
    _user_playlist_tack_no = 0  # Position number within the user playlist
    _user_playlists = None      # Array of Tuples (UserPlaylistId, Name)
    _playlist = None            # PlaylistItem if TrackItem/VideoItem is a part of a Playlist
    _playlistPos = 0            # Item position in playlist

    def getUserplaylistLabel(self, colored=True):
        userpl = ""
        if self._user_playlists and colored:
            titles = []
            for pl_id, pl_title in self._user_playlists: 
                if pl_id != self._user_playlist_id:
                    titles.append(pl_title)
            if len(titles) > 0:
                userpl = ' [' + ', '.join(titles) + ']'
                if settings.userPlaylistColor and colored:
                    userpl = '[COLOR %s]%s[/COLOR]' % (settings.userPlaylistColor, userpl)
        return userpl

#------------------------------------------------------------------------------
# Class TrackItem
#------------------------------------------------------------------------------

class TrackItem(PlaylistPosItem):
    ''' Track Informations:
        'id': 55783546
        'title': u'Conqueror'
        'artist': {u'type': u'MAIN', u'id': 55225, u'name': u'AURORA'}
        'artists': [{u'type': u'MAIN', u'id': 55225, u'name': u'AURORA'}]
        'album': {u'cover': u'b938e5c5-3ed9-40f0-a93e-42c6b16521f6', u'id': 55783545, u'title': u'Conqueror'}
        'trackNumber': 1
        'volumeNumber': 1
        'duration': 207
        'allowStreaming': True
        'description': None
        'copyright': u'(P) 2015 Decca, a division of Universal Music Operations Limited'
        'url': u'http://www.tidal.com/track/55783546'
        'popularity': 74
        'explicit': False
        'premiumStreamingOnly': False
        'streamStartDate': u'2016-02-24T00:00:00.000+0000'
        'replayGain': -9.0299999999999994
        'version': None
        'peak': 0.999969
        'streamReady': True
        'isrc': u'GBUM71506322'
    '''
    # Mapped Properties
    title = 'Unknown'
    duration = -1
    trackNumber = 1
    volumeNumber = 1
    popularity = 0
    artist = ArtistItem()
    artists = []
    album = None
    explicit = False
    isrc = None
    version = None
    allowStreaming = True
    streamReady = True
    premiumStreamingOnly = False
    streamStartDate = None
    peak = 1.0
    replayGain = 0.0

    # Internal Properties
    _ftArtists = []  # All artists except main (Filled by parser)

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.id = '%s' % self.id  # Convert numeric to string
        if self.streamStartDate:
            self.streamStartDate = iso8601.parse_date(self.streamStartDate)
        self.popularity = int("0%s" % self.popularity)
        if self.version and self.title.find(self.version) >= 0:
            # Remove Version if it is part of the title
            self.version = None

    def getSortField(self, field='title'):
        if field == 'date':
            if self.album and self.album.releaseDate:
                return self.album.releaseDate 
            if self.streamStartDate:
                return self.streamStartDate 
            return datetime.now() 
        elif field == 'title' or field == 'name' or not self.artist:
            return self.title
        return '%s - %s' % (self.artist.name, self.title)

    @property
    def _playable(self):
        return self.streamReady

    def getLabel(self, colored=True):
        if self.version:
            text = '%s (%s)' % (self.title, self.version)
        else:
            text = '%s' % self.title
        # Create text for User Playlists
        userpl = self.getUserplaylistLabel(colored)
        # Include Track Number if this track is a part of a User Playlist
        trackno = ''
        if self._user_playlist_id:
            trackno = '%s. ' % self._track_prefix
        if self.artist:
            artistName = self.artist.getLabel(colored) if self._isFavorite or not colored or not self._playable else self.artist._coloredLabel
            text = '%s%s - %s' % (trackno, artistName, text)
        else:
            text = '%s%s' % (trackno, text)
        if self.explicit:
            text = self.addExplicit(text)
        if userpl:
            text += userpl
        return text

    @property
    def _year(self):
        year = None
        if self.album:
            year = self.album._year
        if not year and self.streamStartDate:
            year = self.streamStartDate.year
        return year

    @property
    def _imageUrl(self):
        if self.album:
            if self.album.cover:
                return CONST.profilePictureUrl.format(picture=self.album.cover.replace('-', '/'), size=ImgSize.album[3])
        return settings.addon_icon

    @property
    def _fanartUrl(self):
        if self.artist and isinstance(self.artist, ArtistItem):
            return self.artist._fanartUrl
        return settings.addon_fanart

    @property
    def _track_prefix(self):
        if self.album.numberOfVolumes > 1 and self.volumeNumber > 0:
            return '%d%02d' % (self.volumeNumber, self.trackNumber)
        return '%02d' % self.trackNumber

    def getFtArtistsText(self):
        text = ''
        for item in self._ftArtists:
            if len(text) > 0:
                text = text + ', '
            text = text + item.name
        if len(text) > 0:
            text = 'ft. by ' + text
        return text

    def getComments(self):
        comments = []
        txt = self.getFtArtistsText()
        if txt:
            comments.append(txt)
        if settings.log_details > 1:
            comments.append('track_id=%s' % self.id)
        if self._user_playlists:
            comments.append('User-Playlists: ' + ', '.join([item[1] for item in self._user_playlists]))
        if self.version:
            comments.append(self.version)
        if settings.log_details == 3:
            # Show Peak and ReplayGain in Full Debug Mode
            if self.peak != 0.0:
                comments.append('Peak:%0.3f' % self.peak)            
            if self.replayGain != 0.0:
                comments.append('ReplayGain:%0.3f' % self.replayGain)
        return comments

    def getListItem(self):
        li = BaseItem.getListItem(self)
        li.setProperty('isplayable', 'true' if self._playable else 'false')
        if not self._playable:
            title = '%s (%s)' % (self.title, _T('Stream Not Ready'))
        elif self.version:
            if "remastered" in self.version.lower():
                title = self.title
            else:
                title = '%s (%s)' % (self.title, self.version)            
        else:
            title = self.title
        album = self.album.title if self.album else 'Unknown'
        infos = {
            'title': title,
            'duration': self.duration,
            'artist': self.artist.name if self.artist else 'Unknown',
            'album': album,
            'year': self._year,
            'tracknumber': self._track_prefix,
            'genre': 'Pop',
            'comment': ', '.join(self.getComments()),
            'rating': '%s' % int(round(self.popularity / 20.0)),
        }
        li.setInfo('music', infos)
        if self.artist and settings.showFanart and self._fanartUrl:
            li.setArt({'fanart': self._fanartUrl})
        return li

#------------------------------------------------------------------------------
# Class VideoItem
#------------------------------------------------------------------------------

class VideoItem(PlaylistPosItem):
    ''' Video Informations:
        'id': 54676994
        'title': u'Little Drummer Girl Remixed [Audio]'
        'artist': {u'type': u'MAIN', u'id': 1552, u'name': u'Alicia Keys'}
        'artists': [{u'type': u'MAIN', u'id': 1552, u'name': u'Alicia Keys'}]
        'quality': 'MP4_1080P'
        'streamStartDate': u'2015-12-04T00:00:00.000+0000'
        'explicit': False
        'allowStreaming': True
        'imagePath': None
        or:
        'imagePath': u'/content/sg12/vd03/video/gen/44154847/44154847.jpg',
        'imageId': u'5aee2934-50e2-4d24-893e-bb0d142dba58'
        'releaseDate': u'2015-11-30T00:00:00.000+0000'
        'streamReady': True
        'duration': 269
        'popularity': 10
        'type': u'Music Video'
    '''
    
    # Mapped Properties
    title = 'Unknown'
    artist = ArtistItem()
    artists = []
    explicit = False
    duration = 0
    allowStreaming = True
    streamReady = True
    streamStartDate = None
    releaseDate = None
    quality = None
    imageId = None
    imagePath = None
    version = None

    # Internal Properties
    _ftArtists = []  # All artists except main (Filled by parser)
    _width = 1920
    _height = 1080

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.id = '%s' % self.id
        if self.streamStartDate:
            self.streamStartDate = iso8601.parse_date(self.streamStartDate)
        if self.releaseDate:
            self.releaseDate = iso8601.parse_date(self.releaseDate)
        try:
            self._width, self._height = CONST.videoQuality[self.quality]
        except:
            self._width, self._height = CONST.videoQuality['DEFAULT']

    def getSortField(self, field='title'):
        if field == 'date':
            if self.releaseDate:
                return self.releaseDate 
            if self.streamStartDate:
                return self.streamStartDate 
            return datetime.now() 
        elif field == 'title' or field == 'name' or not self.artist:
            return self.title
        return '%s - %s' % (self.artist.name, self.title)

    @property
    def _playable(self):
        return self.streamReady

    def getLabel(self, colored=True):
        withYear = ' (%s)' % self._year if self._year != '?' else ''
        trackno = ''
        if self._user_playlist_id:
            trackno = '%02d. ' % (self._user_playlist_tack_no + 1)
        # Create text for User Playlists
        userpl = self.getUserplaylistLabel(colored)
        if self.artist:
            artistName = self.artist.getLabel(colored) if self._isFavorite or not colored or not self._playable else self.artist._coloredLabel
            text = '%s%s - %s%s' % (trackno, artistName, self.title, withYear)
        else:
            text = '%s%s%s' % (trackno, self.title, withYear)
        if self.explicit:
            text = self.addExplicit(text)
        if userpl:
            text += userpl
        return text

    @property
    def _year(self):
        year = '?'
        if self.releaseDate:
            year = self.releaseDate.year
        elif self.streamStartDate:
            year = self.streamStartDate.year
        return year

    @property
    def _imageUrl(self):
        if self.imageId:
            return CONST.profilePictureUrl.format(picture=self.imageId.replace('-', '/'), size=ImgSize.video[1])
        elif self.imagePath:
            return CONST.videoImageURL.format(width=320, height=214, imagepath=self.imagePath)
        return settings.addon_icon

    @property
    def _fanartUrl(self):
        if self.artist and isinstance(self.artist, ArtistItem):
            return self.artist._fanartUrl
        elif self.imagePath:
            return CONST.videoImageURL.format(width=320, height=214, imagepath=self.imagePath)
            #return CONST.artistImageURL.format(width=1080, height=720, artistid=self.artist.id)
        return settings.addon_fanart

    def getFtArtistsText(self):
        text = ''
        for item in self._ftArtists:
            if len(text) > 0:
                text = text + ', '
            text = text + item.name
        if len(text) > 0:
            text = 'ft. by ' + text
        return text

    def getComments(self):
        comments = []
        comment = self.getFtArtistsText()
        if comment:
            comments.append(comment)
        if settings.log_details > 1:
            comments.append('video_id=%s' % self.id)
        return comments

    def getListItem(self):
        li = BaseItem.getListItem(self)
        li.setInfo('video', {
            #'cast': [self.artist._label],
            'artist': [self.artist.name],
            'title': self.title,
            'duration': '%s:%s' % divmod(self.duration, 60),
            'year': self._year,
            'studio': '%s' % self._year,
            #'album': 'Quality: %s' % self.quality,
            'comment': ', '.join(self.getComments()),
            'plotoutline': ', '.join(self.getComments()),
        })
        li.setProperty('isplayable', 'true' if self._playable else 'false')
        if settings.showFanart and self._fanartUrl:
            li.setArt({'fanart': self._fanartUrl})        
        # Determine the maximum resolution
        if not self._width:
            self._width, self._height = CONST.videoQuality['DEFAULT']
        li.addStreamInfo('video', { 'codec': 'h264', 'aspect': 1.78, 'width': self._width,
                         'height': self._height, 'duration': self.duration })
        li.addStreamInfo('audio', { 'codec': 'AAC', 'language': 'en', 'channels': 2 })
        return li

#------------------------------------------------------------------------------
# Class PromotionItem
#------------------------------------------------------------------------------

class PromotionItem(BaseItem):
    ''' Featured-Item Properties:
        'subHeader': u'Die beliebtesten Songs',
        'shortHeader': u'TIDAL Top 100',
        'group': u'NEWS',  or 'RISING', 'DISCOVERY'
        'created': u'2015-09-21T12:27:31.952+0000',
        'text': u'Welche Songs sind gerade besonders beliebt auf TIDAL? Das h\xf6rt ihr in dieser w\xf6chentlich aktualisierten PlaylistItem!',
        'imageURL': u'http://resources.wimpmusic.com/images/070629e8/ea83/434f/85ef/83aadb065a21/550x400.jpg',
        'imageId': u'070629e8-ea83-434f-85ef-83aadb065a21',
        'header': u'TIDAL Top 100',
        'featured': False,
        'shortSubHeader': u'Die beliebtesten Songs',
        'standaloneHeader': None,
         for Playlists:
            'type': u'PLAYLIST',
            'artifactId': u'56c28e48-5d09-4fb0-812e-c6c7c6647dcf'
         for Albums:
            'type': u'ALBUM',
            'artifactId': u'50223865'
         for Videos:
            'type': u'VIDEO',
            'artifactId': u'50714521'
         for External URLs:
            'type': u'EXTURL',
            'artifactId': u'http://read.tidal.com/article/end-of-the-line-korey-dane-uk'
    '''
    # Mapped Properties
    subHeader = None
    shortHeader = None
    group = None        # NEWS|DISCOVERY|RISING
    created = None
    text = None
    imageId = None
    imageURL = None
    type = None         # PLAYLIST|ALBUM|VIDEO|EXTURL
    artifactId = None
    duration= 0

    # Internal Properties
    artist = None       # To fill later

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        if self.created:
            self.created = iso8601.parse_date(self.created)
        self.id = '%s' % self.artifactId
        self.id = self.id.strip()

    def getSortField(self, field='date'):
        if field == 'date':
            if self.created:
                return self.created 
            if self.streamStartDate:
                return self.streamStartDate 
            return datetime.now() 
        return '%s - %s' % (self.shortHeader, self.subHeader)

    def getLabel(self, colored=True):
        itemType = '[%s] ' % self.type if settings.showAlbumType and self.type else ''
        return '%s%s - %s' % (itemType, self.shortHeader, self.subHeader)

    @property
    def _imageUrl(self):
        if self.imageId:
            return CONST.profilePictureUrl.format(picture=self.imageId.replace('-', '/'), size=ImgSize.promo[0])
        return self.imageURL

    @property
    def _fanartUrl(self):
        if self.imageId:
            return CONST.profilePictureUrl.format(picture=self.imageId.replace('-', '/'), size=ImgSize.promo[0])
        return self.imageURL

    def getListItem(self):
        li = BaseItem.getListItem(self)
        if self.type == 'VIDEO':
            li.setProperty('isplayable', 'true')
            info = {
                'cast': [self.shortHeader],
                'artist': [self.shortHeader],
                'title': self.subHeader,
                'album': self.subHeader,
            }
            if self.type == 'VIDEO' and settings.log_details > 1:
                info.update({'plotoutline': 'video_id=%s' % self.artifactId})
            li.setInfo('video', info)
            width = 1920   # Assume maximum quality
            height = 1080
            li.addStreamInfo('video', { 'codec': 'h264', 'aspect': 1.78, 'width': width,
                             'height': height, 'duration': self.duration })
            li.addStreamInfo('audio', { 'codec': 'AAC', 'language': 'en', 'channels': 2 })
        else:
            li.setInfo('music', {
                'artist': self.shortHeader,
                'album': self.subHeader,
            })
        if settings.showFanart and self._fanartUrl:
            li.setArt({'fanart': self._fanartUrl})
        return li

#------------------------------------------------------------------------------
# Class FolderItem
#------------------------------------------------------------------------------

class FolderItem(BaseItem):
    
    ''' Info of available contents 
        name: "Neu", 
        path: "new", 
        hasAlbums: true, 
        hasArtists: false, 
        hasPlaylists: false, 
        hasTracks: true,
        hasVideos: false,
        image: null
    '''
    # Mapped Properties
    name = None
    path = None
    hasAlbums = False
    hasArtists = False
    hasPlaylists = False
    hasTracks = False
    hasVideos = False
    image = None

    # Internal Properties
    _group = ''
    _otherLabel = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def getSortField(self, field='name'):
        return self.name

    @property
    def id(self):
        if self._group:
            return '%s_%s' % (self._genre, self.path)
        else:
            return self.path

    def getLabel(self, colored=True):
        return self._otherLabel if self._otherLabel else self.name

    @property
    def _imgSize(self):
        imgSize = "512x512"
        if self._group == 'genres':
            imgSize = ImgSize.genre[0]
        elif self._group == 'moods':
            imgSize = ImgSize.mood[0]
        return imgSize

    @property
    def _imageUrl(self):
        if self.image:
            return CONST.profilePictureUrl.format(picture=self.image.replace('-', '/'), size=self._imgSize)
        return settings.addon_icon

    @property
    def _fanartUrl(self):
        if self.image:
            return CONST.profilePictureUrl.format(picture=self.image.replace('-', '/'), size=self._imgSize)
        return settings.addon_fanart

    @property
    def _content_type_count(self):
        count = 0
        if self.hasArtists:
            count += 1
        if self.hasAlbums:
            count += 1
        if self.hasPlaylists:
            count += 1
        if self.hasTracks:
            count += 1
        if self.hasVideos:
            count += 1
        return count

    def getListItem(self):
        li = BaseItem.getListItem(self)
        li.setInfo('music', {
            'artist': self._label,
        })
        if settings.showFanart and self._fanartUrl:
            li.setArt({'fanart': self._fanartUrl})
        return li

#------------------------------------------------------------------------------
# Class SearchResults
#------------------------------------------------------------------------------

class SearchResult(object):
    ''' List of Search Result Items '''

    artists = []
    albums = []
    tracks = []
    playlists = []
    videos = []

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.artists = []
        self.albums = []
        self.tracks = []
        self.playlists = []
        self.videos = []
    
#------------------------------------------------------------------------------
# Class MusicURL
#------------------------------------------------------------------------------

class MusicURL(object):
    ''' Resolved URL for Music Streams
        "url": "rtmp.stream.tidalhifi.com/cfx/st/mp4:....",
        "trackId": 53064085, 
        "encryptionKey": "", 
        "soundQuality": "HIGH",  "LOW" or "LOSSLESS" 
        "playTimeLeftInMinutes": -1
    '''
    # Mapped Properties
    url = None
    trackId = None
    encryptionKey = None
    soundQuality = 'HIGH'
    playTimeLeftInMinutes = -1
    
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def getParams(self):
        if not self.url.startswith('http://') and not self.url.startswith('https://'):
            host, tail = self.url.split('/', 1)
            app, playpath = tail.split('/mp4:', 1)
            params = { 'url': 'rtmp://%s' % host,
                       'app': app,
                       'playpath': 'mp4:%s' % playpath }
        else:
            params = { 'url': self.url }
        return params       
    
    @property
    def _stream_url(self):
        if not self.url.startswith('http://') and not self.url.startswith('https://'):
            params = self.getParams()
            return '%s app=%s playpath=%s' % (params['url'], params['app'], params['playpath'])
        return self.url

    @property
    def _mimetype(self):
        if self.soundQuality == MusicQuality.trial:
            # Tracks are MP3 in Trial Mode
            return 'audio/mp3'
        elif self.soundQuality in [MusicQuality.lossless, MusicQuality.lossless_hd]:
            return 'audio/flac'
        return 'audio/aac'

#------------------------------------------------------------------------------
# Class VideoURL
#------------------------------------------------------------------------------

class VideoURL(object):
    ''' Resolved URL for Video Streams
        "url": "http://....m3u8",
    '''
    # Mapped Properties
    url = None

    # internal Properties
    _m3u8obj = None
    _width = 1920
    _height = 1080
    _stream_url = None
        
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @property
    def _mimetype(self):
        return 'video/mp4'

# End of File
