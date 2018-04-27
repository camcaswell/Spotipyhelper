import spotipy
import spotipy.util as util

import configparser
import os
from json import JSONDecodeError

class subSpotify(spotipy.Spotify):

    ''' This is a subclass of spotipy.Spotify for the purpose of defining new methods.
        If you ever want to construct a client with more parameters than just auth, __init__ needs to be rewritten.
    '''

    def __init__(self, auth):
        super().__init__(auth)

    def get_tracks_from_playlist(self, playlist_owner=None, playlist_id=None, playlist=None):

        ''' user_playlist_tracks() returns a "paging object" which only holds 100 items at once,
            so this calls aggregate_paging_results() to get a single list of all the "playlist track objects".

           "Playlist track objects" are glorified pointers to the actual track, so this method resolves the pointers and returns the actual tracks.

            If you want the time the track was added or the user who added it, this method is not for you.
        '''
        if playlist:
            playlist_owner = playlist['owner']['id']
            playlist_id = playlist['id']
        elif not (playlist_owner and playlist):
            raise TypeError("get_tracks_from_playlist() requires a playlist, or a username and playlist id as arguments")

        try:
            query_result = self.user_playlist_tracks(playlist_owner, playlist_id)
        except spotipy.SpotifyException as error:
            print(f"Spotify threw and error while retrieving tracks from spotify:user:{playlist_owner}:playlist:{playlist_id}:\n{error}")
            return []

        track_objs = self.aggregate_paging_results(query_result)
        
        tracks = []
        for trackobj in track_objs:
            tracks.append(trackobj['track'])
        return tracks

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

    def add_tracks_to_playlist(self, username=None, playlist_id=None, playlist=None, track_list=None, track_id_list=None, position=None):

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

        split_track_list = [track_id_list[100*i:100*(i+1)] for i in range(int(len(track_id_list)/100 + 1))]

        for sublist in split_track_list:
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
    

def generate_token(scope):

    ''' Requires a spotify_config.cfg file with the relevant information in it
    '''
    config = configparser.ConfigParser()
    config.read('spotify_config.cfg')
    client_id = config.get('SPOTIFY', 'client_id')
    client_secret = config.get('SPOTIFY', 'client_secret')
    username = config.get('SPOTIFY', 'username')

    ''' util.prompt_for_user_token() checks the cache for a valid token first,
        and sometimes that gets messed up, so if it goes wrong, this deletes the one in cache then tries again.
    '''
    try:
        token = util.prompt_for_user_token(
            username=username,
            scope=scope,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://localhost:8888/callback/"
        )

    except (AttributeError, JSONDecodeError):
        os.remove(".cache-{}".format(username))
        token = util.prompt_for_user_token(
            username=username,
            scope=scope,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://localhost:8888/callback/"
        )

    return token