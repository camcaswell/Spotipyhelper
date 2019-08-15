import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials

import configparser
import os
from json import JSONDecodeError
import datetime


class subSpotify(spotipy.Spotify):

    ''' This is a subclass of spotipy.Spotify for the purpose of defining new methods.
    '''

    def __init__(self, token=None, scope=None):
        if not token:
            token = subSpotify.generate_token(scope)
        assert token, "Failed to get token on subSpotify initialization."
        super().__init__(token)
        self._scope = scope

    @staticmethod
    def generate_token(scope):
        ''' Requires a spotify_config.cfg file with the relevant information in it
        '''
        with open('config.cfg') as fp:
            config = configparser.ConfigParser()
            config.readfp(fp)
            client_id = config.get('SPOTIFY', 'client_id')
            client_secret = config.get('SPOTIFY', 'client_secret')
            username = config.get('SPOTIFY', 'username')

        try:
            token = util.prompt_for_user_token(
                username=username,
                scope=scope,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri="http://localhost:8888/callback/",
            )
            ''' util.prompt_for_user_token() checks the cache for a valid token first,
                so if that goes wrong, this deletes the one in cache then tries again.
            '''
        except (AttributeError, JSONDecodeError):
            print("Had to delete token in cache.")
            os.remove(f".cache-{username}")
            token = util.prompt_for_user_token(
                username=username,
                scope=scope,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri="http://localhost:8888/callback/",
            )
            
        return token

    def refresh(self):
        ''' Supposed to get a freshly authorized client, but doesn't seem to be working at the moment.
        '''
        if self._scope:
            return subSpotify(self._scope)
        else:
            raise TypeError("Cannot refresh client without a scope available."
                + "\nTry constructing the original client by passing the scope instead of a whole token.")

    def get_users_by_id(self, user_ids):
        ''' Handles looking up an iterable of user IDs one at a time, then returning an aggregated list of users.
        '''
        if user_ids:
            users = []
            for user_id in user_id_list:
                users.append(self.user(user_id))
            return users
        else:
            return []

    def get_tracks_by_id(self, track_ids):
        ''' Handles splitting an iterable of IDs into appropriately-sized chunks (50), then then returning a single list of aggregated tracks.
        '''
        if track_ids:
            tracks = []
            for sublist in splitlist(list(track_ids), 50):
                tracks.extend(self.tracks(sublist)['tracks'])
            return tracks
        else:
            return []

    def get_albums_by_id(self, album_ids):
        ''' Handles splitting an iterable of IDs into appropriately-sized chunks (20), then returning a single list of aggregated albums.
        '''
        if album_ids:
            albums = []
            for sublist in splitlist(list(album_ids), 20):
                albums.extend(self.albums(sublist)['albums'])
            return albums
        else:
            return []

    def get_artists_by_id(self, artist_ids):
        ''' Handles splitting an iterable of IDs into appropriately-sized chunks (50), then returning a single list of aggregated artists.
        '''
        if artist_ids:
            artists = []
            for sublist in splitlist(list(artist_ids), 50):
                try:
                    artists.extend(self.artists(sublist)['artists'])
                except JSONDecodeError as error:
                    print(f"Encountered JSONDecodeError while attempting to retreive artists for these ids: {sublist}")
                    continue
            return artists
        else:
            return []

    def get_playlists_by_id(self, id_pairs):
        ''' Handles looking up playlists one at a time with pairs of IDs
            where an ID pair looks like: (owner_id, playlist_id)
        '''
        if id_pairs:
            playlists = []
            for pair in id_pairs:
                playlists.append(self.user_playlist(pair[0], pair[1]))
            return playlists
        else:
            return []

    def get_saved_tracks(self):
        return [t['track'] for t in self.aggregate_paging_results(self.current_user_saved_tracks())]

    def get_saved_artists(self):
        return list({artist['id'] : artist for song in self.get_saved_tracks() for artist in song["artists"]}.values())

    def get_tracks_from_playlist(self, playlist_owner=None, playlist_id=None, playlist=None):
        ''' user_playlist_tracks() returns a "paging object" which only holds 100 items at once,
            so this calls aggregate_paging_results() to get a single list of all the "playlist track objects".

            "Playlist track objects" are glorified pointers to the actual track,
            so this method resolves the pointers and returns the actual tracks.

            If you want the time the track was added or the user who added it, this method is not for you.
        '''
        if playlist:
            playlist_owner = playlist['owner']['id']
            playlist_id = playlist['id']
        elif not (playlist_owner and playlist_id):
            raise TypeError("get_tracks_from_playlist() requires a playlist, or a username and playlist id as arguments")

        try:
            query_result = self.user_playlist_tracks(playlist_owner, playlist_id)
        except spotipy.SpotifyException as error:
            print(f"Spotify threw and error while retrieving tracks from"
                + " spotify:user:{playlist_owner}:playlist:{playlist_id}:\n{error}")
            return []

        track_objs = self.aggregate_paging_results(query_result)
        return [t['track'] for t in track_objs]

    def aggregate_paging_results(self, paging_obj):
        ''' Paging objects only contain a limited number of items,
            so this method aggregates all of the requested items into one list
        '''
        return_list = paging_obj['items']
        while paging_obj['next']:
            paging_obj = self.next(paging_obj)
            return_list.extend(paging_obj['items'])
        return return_list

    def diff_between_playlists(self, playlist1, playlist2):
        ''' Returns a list of songs that only appear in one playlist or the other
        '''
        tracklist1 = self.get_tracks_from_playlist(playlist=playlist1)
        tracklist2 = self.get_tracks_from_playlist(playlist=playlist2)

        diff_ids = list( set([x['id'] for x in tracklist1]).symmetric_difference(set([x['id'] for x in tracklist2])) )

        lookup_ref = {x['id']:x for x in tracklist1}
        lookup_ref.update({y['id']:y for y in tracklist2})

        return [lookup_ref[x] for x in diff_ids]


    def playlists_where_song_appears(self, username, song_id):
        ''' Returns a list of playlists that the given song appears in for the given user
        '''
        return_list = []

        for playlist in self.aggregate_paging_results(self.user_playlists(username)):
            tracks = self.get_tracks_from_playlist(playlist=playlist)
            for song in tracks:
                if song['id'] == song_id:
                    return_list.append(playlist)
                    break

        return return_list

    def add_tracks_to_playlist(self,
        username=None, playlist_id=None, playlist=None, track_list=None, track_id_list=None, position=None):
        ''' The Spotify API will only add 100 songs to a playlist at a time,
            so this method takes care of splitting a list larger than 100 and feeding in the sublists.
        '''
        if playlist:
            username = playlist['owner']['id']
            playlist_id = playlist['id']
        elif not (username and playlist_id):
            raise TypeError("add_tracks_to_playlist() requires a playlist, or a username and playlist id as arguments")

        if track_list:
            track_id_list = [x['id'] for x in track_list]
        elif not track_id_list:
            raise TypeError("add_tracks_to_playlist() requires a list of tracks or a list of track ids as an argument")

        for sublist in splitlist(track_id_list, 100):
            self.user_playlist_add_tracks(
                username,
                playlist_id,
                sublist,
                position=position
                )

    def lonely_songs(self):
        ''' Returns a list of the songs in the user's library that do not appear in any of their playlists
        '''
        pointers = self.aggregate_paging_results(self.current_user_saved_tracks())
        lonely_songs = { p['track']['id'] : p['track'] for p in pointers }

        playlists = self.aggregate_paging_results(self.current_user_playlists())
        for playlist in playlists:
            tracks = self.get_tracks_from_playlist(playlist=playlist)
            for track in tracks:
                lonely_songs.pop(track['id'], None)

        return list(lonely_songs.values())

    def albums_after(self, datestring, artists=[]):
        ''' datestring: 'yyyymmdd'
            Returns a dict of all albums released after the given date from artists in your saved library.
        '''
        cutoff = parse_date(datestring)
        if not artists:
            artists = self.get_saved_artists()

        new_albums = {}
        for artist in artists:
            try:
                albums = sp.aggregate_paging_results(sp.artist_albums(artist['id']))
            except:
                #Refresh token
                sp = subSpotify(scope='''
                    playlist-read-private 
                    playlist-read-collaborative 
                    user-follow-read 
                    ''')
                albums = sp.aggregate_paging_results(sp.artist_albums(artist['id']))

            if albums:
                albums_with_dates = [ (a,parse_date(a['release_date'])) for a in albums]
                albums_with_dates = [ (a,d) for a,d in albums_with_dates if d>=cutoff]
                albums_with_dates.sort(key=lambda p: p[1])
                new_albums[artist['id']] = (artist, albums_with_dates)
            else:
                print(f'Couldn\'t find any albums for {artist["id"]}')
                continue
        return new_albums


def gen_creds():
    #currently unsure whether this works
    with open('config.cfg') as fp:
        config = configparser.ConfigParser()
        config.readfp(fp)
        client_id = config.get('SPOTIFY', 'client_id')
        client_secret = config.get('SPOTIFY', 'client_secret')
        username = config.get('SPOTIFY', 'username')

    return SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)

def splitlist(input_list, size):
    ''' splits a list into a list of regularly-sized sublists
    '''
    return [input_list[size*i:size*(i+1)] for i in range(int(len(input_list)/size + 1))]

def parse_date(datestring):
    ''' date: yyyy[-mm[-dd]?]? -> datetime.date(yyyy, mm, dd)
        The release dates for albums may not have months or days specified.
    '''
    datestring.replace('/', '-')
    date_split = datestring.split('-')

    # month and day are 1 if not defined
    if len(date_split)==1:
        date_split.extend(["1", "1"])
    elif len(date_split)==2:
        date_split.extend(["1"])
    elif len(date_split)!=3:
        raise ValueError("Date string has the wrong number of components.")

    # Spotify data is garbage
    if date_split[0] == '0000':
        date_split[0] = '0001'

    if len(date_split[0])!=4:
        raise ValueError("Year component of date string is the wrong length.")

    return datetime.date(*[int(s) for s in date_split])
