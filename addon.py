from datetime import datetime
from datetime import timedelta
from compose.utils import json_decoder
from urlparse import urlparse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import xbmcplugin
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import os
import json
# import config
import sys
import time
import socket

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__icon__ = __addon__.getAddonInfo('icon')
__path__ = __addon__.getAddonInfo('path')

mode_youtube = __addon__.getSetting(id='youtube-enable')
mode_movies = __addon__.getSetting(id='movies-enable')
mode_tvshows = __addon__.getSetting(id='tv-shows-enable')

if mode_youtube == 'true':
    api_service_name = __addon__.getSetting(id='youtube-api-service-name')
    api_version = __addon__.getSetting(id='youtube-api-version')
    developer_key = __addon__.getSetting(id='youtube-api-key')
    channelsSetting = __addon__.getSetting(id='youtube-channels-name')
    searchSetting = __addon__.getSetting(id='youtube-search-terms')
    maxResultsSetting = __addon__.getSetting(id='youtube-default-max-results')
    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=developer_key)
elif mode_movies == 'true':
    movieGenreSetting = __addon__.getSetting(id='movies-genre')
    moviePlaylistSetting = __addon__.getSetting(id='movies-playlist')
elif mode_tvshows == 'true':
    tvGenreSetting = __addon__.getSetting(id='tv-shows-genre')
    tvPlaylistSetting = __addon__.getSetting(id='tv-shows-playlist')
    tvNamesSetting = __addon__.getSetting(id='tv-shows-names')


def get_videos_youtube(maxResults, order=None, duration=None, publishedAfter=None, publishedBefore=None, search=None,
                       channelId=None, related=None):
    if search is not None:
        request = youtube.search().list(part="id,snippet", q=search, type="video", videoDuration=duration,
                                        maxResults=maxResults, order=order)
    elif related is not None:
        request = youtube.search().list(part="id,snippet", relatedToVideoId=related, type="video",
                                        videoDuration=duration, maxResults=maxResults, order=order)
    elif channelId is not None:
        request = youtube.search().list(part="id,snippet", channelId=channelId, type="video",
                                        publishedAfter=publishedAfter.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                        maxResults=maxResults, order=order)
    else:
        raise NameError('Nothing to search')

    response = request.execute()
    return response.get("items", [])


def get_channelId_by_channelName(channelName):
    request = youtube.search().list(part="id,snippet", q=channelName, type="channel", maxResults=1)
    response = request.execute()
    for search_result in response.get("items", []):
        channel = search_result
    return channel["snippet"]["channelId"]


def create_local_playList():
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    return playlist


def add_item_playList(playlist, item):
    url = get_item_url(item)
    playlist.add(url=url)

    return playlist


def add_items_playList(playlist, items):
    for item in items:
        url = get_item_url(item)
        playlist.add(url=url)

    return playlist


def get_xbmc_movies(genre):
    import json
    query = {
        'jsonrpc': '2.0',
        'id': '1',
        'method': 'VideoLibrary.GetMovies',
        'params': {
            'properties': [
                "title",
                "genre",
                "year",
                "rating",
                "director",
                "trailer",
                "tagline",
                "plot",
                "plotoutline",
                "originaltitle",
                "lastplayed",
                "playcount",
                "writer",
                "studio",
                "mpaa",
                "cast",
                "country",
                "imdbnumber",
                "runtime",
                "set",
                "showlink",
                "streamdetails",
                "top250",
                "votes",
                "fanart",
                "thumbnail",
                "file",
                "sorttitle",
                "resume",
                "setid",
                "dateadded",
                "tag",
                "art",
                "userrating",
                "ratings",
                "premiered",
                "uniqueid"
            ],
            'filter': {
                'or': [
                    {"field": "genre", "operator": "contains", "value": [genre]}
                ]
            },
            'limits': {
                "start": 0, "end": 75
            },
            'sort': {
                "order": "ascending",
                "method": "year"
            }
        }
    }
    response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    return response.get('result', {}).get('movies', [])


def get_xbmc_tvshows(genre=None, name=None):
    import json
    query = {
        'jsonrpc': '2.0',
        'id': 'libTvShows',
        'method': 'VideoLibrary.GetTVShows',
        'params': {
            'properties': [
                "title",
                "genre",
                "year",
                "rating",
                "plot",
                "studio",
                "mpaa",
                "cast",
                "playcount",
                "episode",
                "imdbnumber",
                "premiered",
                "votes",
                "lastplayed",
                "fanart",
                "thumbnail",
                "file",
                "originaltitle",
                "sorttitle",
                "episodeguide",
                "season",
                "watchedepisodes",
                "dateadded",
                "tag",
                "art",
                "userrating",
                "ratings",
                "runtime",
                "uniqueid"
            ],
            # 'filter': {
            # 'or': [
            # { "field": "genre", "operator": "contains", "value": [ genre ] }
            # ]
            # }
        }
    }
    if genre is not None:
        query['params']['filter'] = {
            'or': [
                {"field": "genre", "operator": "contains", "value": [genre]}
            ]
        }
    if name is not None:
        query['params']['filter'] = {
            'or': [
                {"field": "title", "operator": "is", "value": name}
            ]
        }
    response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    return response.get('result', {}).get('tvshows', [])


def get_xbmc_tvshowseasons(tvshowid, indexStart=None, indexEnd=None):
    import json
    query = {
        'jsonrpc': '2.0',
        'id': 0,
        'method': 'VideoLibrary.GetSeasons',
        'params': {
            'tvshowid': tvshowid,
            "properties": [
                "title",
                "season",
                "showtitle",
                "playcount",
                "episode",
                "fanart",
                "thumbnail",
                "tvshowid",
                "watchedepisodes",
                "art",
                "userrating"
            ]
        }
    }
    if indexStart is not None:
        query['params']['limits'] = {
            "start": indexStart, "end": indexEnd
        }
    response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    return response.get('result', {}).get('seasons', [])


def get_xbmc_tvshowepisodes(tvshowid, season, indexStart=None, indexEnd=None):
    import json
    query = {
        'jsonrpc': '2.0',
        'id': 0,
        'method': 'VideoLibrary.GetEpisodes',
        'params': {
            'tvshowid': tvshowid,
            'season': season,
            "properties": [
                "title",
                "playcount",
                "runtime",
                "season",
                "episode",
                "showtitle",
                "lastplayed",
                "fanart",
                "thumbnail",
                "file",
                "resume",
                "tvshowid",
                "dateadded",
                "uniqueid",
                "art",
                "specialsortseason",
                "specialsortepisode",
                "userrating",
                "seasonid"
            ]
            # 'limits': {
            # "start" : indexStart, "end": indexEnd
            # }
        }
    }
    if indexStart is not None:
        query['params']['limits'] = {
            "start": indexStart, "end": indexEnd
        }
    response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    return response.get('result', {}).get('episodes', [])


def get_xbmc_mediasources():
    import json
    query = {
        'jsonrpc': '2.0',
        'id': 0,
        'method': 'Files.GetSources',
        'params': {
            'media': 'video'
        }
    }
    response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    return response.get('result', {}).get('sources', [])


def get_active_players():
    import json
    query = {
        'jsonrpc': '2.0',
        'id': 0,
        'method': 'Player.GetActivePlayers',
    }
    response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    return response.get('result', {})


def get_player_item(playerId):
    import json
    query = {
        'jsonrpc': '2.0',
        'id': 'VideoGetItem',
        'method': 'Player.GetItem',
        'params': {
            'playerid': playerId,
            "properties": [
                "title",
                "artist",
                "genre",
                "year",
                "rating",
                "duration",
                "playcount",
                "fanart",
                "originaltitle",
                "lastplayed",
                "streamdetails",
                "thumbnail",
                "file",
                "resume",
                "art",
                "description",
                "uniqueid",
                "starttime",
                "endtime",
                "userrating"
            ]
        }
    }
    response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    return response.get('result', {}).get('item', [])


def list_xbmc_directories(path):
    import json
    query = {
        'jsonrpc': '2.0',
        'id': 0,
        'method': 'Files.GetDirectory',
        'params': {
            # 'media': 'video',
            'directory': path,
            "properties": [
                "title",
                "artist",
                "albumartist",
                "genre",
                "year",
                "rating",
                "album",
                "track",
                "duration",
                "comment",
                "lyrics",
                "musicbrainztrackid",
                "musicbrainzartistid",
                "musicbrainzalbumid",
                "musicbrainzalbumartistid",
                "playcount",
                "fanart",
                "director",
                "trailer",
                "tagline",
                "plot",
                "plotoutline",
                "originaltitle",
                "lastplayed",
                "writer",
                "studio",
                "mpaa",
                "cast",
                "country",
                "imdbnumber",
                "premiered",
                "productioncode",
                "runtime",
                "set",
                "showlink",
                "streamdetails",
                "top250",
                "votes",
                "firstaired",
                "season",
                "episode",
                "showtitle",
                "thumbnail",
                "file",
                "resume",
                "artistid",
                "albumid",
                "tvshowid",
                "setid",
                "watchedepisodes",
                "disc",
                "tag",
                "art",
                "genreid",
                "displayartist",
                "albumartistid",
                "description",
                "theme",
                "mood",
                "style",
                "albumlabel",
                "sorttitle",
                "episodeguide",
                "uniqueid",
                "dateadded",
                "size",
                "lastmodified",
                "mimetype",
                "specialsortseason",
                "specialsortepisode"
            ]
        }
    }
    response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    return response.get('result', {}).get('files', [])


def get_item_url(item):
    if mode_youtube == 'true':
        url = url = "plugin://plugin.video.youtube/play/?video_id=" + item["id"]["videoId"]
    elif mode_movies == 'true':
        url = item["file"]
    elif mode_tvshows == 'true':
        url = item["file"]

    return url


def check_connection_media_source():
    media_sources = get_xbmc_mediasources()
    for media_source in media_sources:
        url_parsed = urlparse(media_source["file"])
        ip = url_parsed.netloc
        port = 22
        xbmc.log("testing...: " + ip, level=xbmc.LOGNOTICE)
        if is_open(ip, port):
            xbmc.log("HOST IS UP: " + ip, level=xbmc.LOGNOTICE)
            ipup = True
        else:
            xbmc.log("not connect", level=xbmc.LOGNOTICE)
            ipup = False
            break
    return ipup


def is_open(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    try:
        # s.connect((ip, int(port)))
        s.connect(("192.168.1.40", int(port)))
        s.shutdown(socket.SHUT_RDWR)
        return True
    except:
        return False
    finally:
        s.close()


class Widgets_Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)

    def onPlayBackStarted(self):
        xbmc.log("OnPlayback Start! %s" % time.time(), level=xbmc.LOGNOTICE)
        if mode_youtube == 'true':
            playlist_position = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition()
            playlist_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            xbmc.log("PLAYLIST POSITION: " + str(playlist_position), level=xbmc.LOGNOTICE)
            xbmc.log("PLAYLIST SIZE: " + str(playlist_size), level=xbmc.LOGNOTICE)
            if playlist_position == playlist_size - 1:
                xbmc.sleep(3000)
                interval = timedelta(days=-7)
                publishedAfter = datetime.now() + interval
                players = get_active_players()
                for player in players:
                    if player['type'] == 'video':
                        currentItem = get_player_item(player['playerid'])
                currentVideoId = currentItem['file'].split('video_id=')[1]
                videos = get_videos_youtube(maxResults=maxResultsSetting, order="date", publishedAfter=publishedAfter,
                                            related=currentVideoId)
                for video in videos:
                    url = get_item_url(video)
                    xbmc.PlayList(xbmc.PLAYLIST_VIDEO).add(url)

    def onPlayBackStopped(self):
        xbmc.log("OnPlayback Stop! %s" % time.time(), level=xbmc.LOGNOTICE)
        if mode_movies == 'true' or mode_tvshows == 'true':
            playlist_position = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition()
            playlist_size = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
            xbmc.log("PLAYLIST POSITION: " + str(playlist_position), level=xbmc.LOGNOTICE)
            xbmc.log("PLAYLIST SIZE: " + str(playlist_size), level=xbmc.LOGNOTICE)
            window.show()
            if check_connection_media_source():
                window.close()
            else:
                for i in range(300):
                    if check_connection_media_source():
                        xbmc.sleep(3000)
                        window.close()
                        break
                    else:
                        xbmc.sleep(3000)
                xbmc.Player().play(playList, startpos=playlist_position)

    def onPlayBackError(self):
        xbmc.log("OnPlayback Error! %s" % time.time(), level=xbmc.LOGNOTICE)

    def onPlayBackEnded(self):
        xbmc.log("OnPlayback Ended! %s" % time.time(), level=xbmc.LOGNOTICE)


player = Widgets_Player()
no_signal = xbmcgui.ControlImage(0, 0, 1280, 720, __path__ + "/resources/no-signal-tv-screen.jpg")
window = xbmcgui.WindowDialog()
window.addControl(no_signal)
if __name__ == '__main__':
    xbmc.executebuiltin("Playlist.Clear")
    playList = create_local_playList()

    if mode_youtube == 'true':
        interval = timedelta(days=-7)
        publishedAfter = datetime.now() + interval
        youTubeVideos = []

        if channelsSetting is not None and channelsSetting != '':
            channels = channelsSetting.split(',')
            for channel in channels:
                channelId = get_channelId_by_channelName(channel)
                youTubeVideos.extend(
                    get_videos_youtube(maxResults=maxResultsSetting, order="date", publishedAfter=publishedAfter,
                                       channelId=channelId))
        elif searchSetting is not None and channelsSetting != '':
            youTubeVideos = get_videos_youtube(maxResults=maxResultsSetting, order="date",
                                               publishedAfter=publishedAfter, search=searchSetting)
        if youTubeVideos:
            playList = add_items_playList(playList, youTubeVideos)

    elif mode_movies == 'true':
        window.show()
        for i in range(300):
            if check_connection_media_source():
                window.close()
                break
            else:
                xbmc.sleep(3000)
        xbmc.executebuiltin("PlayerControl(repeatall)")
        if not moviePlaylistSetting:
            movies = get_xbmc_movies("Drama")
        elif movieGenreSetting is not None:
            movies = get_xbmc_movies(movieGenreSetting)

        for movie in movies:
            playList = add_item_playList(playList, movie)

    elif mode_tvshows == 'true':
        window.show()
        for i in range(300):
            if check_connection_media_source():
                window.close()
                break
            else:
                xbmc.sleep(3000)
        if tvPlaylistSetting.strip():
            movies = get_xbmc_tvshows(tvGenreSetting)
        elif tvNamesSetting.strip():
            shows = tvNamesSetting.split(',')
            seasons = range(1, 3)
            indexStart = 3
            seasonEmpty = True
            for season in seasons:

                seasonShowsEpisodes = []
                for show in shows:
                    tvshows = get_xbmc_tvshows(name=show)
                    tvshowsSeason = get_xbmc_tvshowseasons(tvshowid=tvshows[0]['tvshowid'], indexStart=season - 1,
                                                           indexEnd=season)
                    if tvshowsSeason:
                        episodes = get_xbmc_tvshowepisodes(tvshowid=tvshows[0]['tvshowid'],
                                                           season=tvshowsSeason[0]['season'])
                        if episodes:
                            seasonShowsEpisodes.append(episodes)

                for seasonShowEpisodes in seasonShowsEpisodes:
                    if seasonShowEpisodes:
                        seasonEmpty = False
                while not seasonEmpty:
                    for seasonShowEpisodes in seasonShowsEpisodes:
                        for i in range(indexStart):
                            if seasonShowEpisodes:
                                episode = seasonShowEpisodes.pop(0)
                                playList = add_item_playList(playList, episode)

                    seasonEmpty = True
                    for seasonShowEpisodes in seasonShowsEpisodes:
                        if seasonShowEpisodes:
                            seasonEmpty = False

        elif tvGenreSetting.strip():
            tvshows = get_xbmc_tvshows(genre=tvGenreSetting)
            for tvshow in tvshows:
                seasons = get_xbmc_tvshowseasons(tvshow['tvshowid'])
                for season in seasons:
                    episodes = get_xbmc_tvshowepisodes(tvshow['tvshowid'], season['season'])
                    playList = add_items_playList(playList, episodes)

    xbmc.Player().play(playList)

    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        # Sleep/wait for abort for 10 seconds
        if monitor.waitForAbort(10):
            # Abort was requested while waiting. We should exit
            break
        xbmc.sleep(500)

