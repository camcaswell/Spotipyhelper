import spotipy
import spotipy.util as util
from spotipy import Spotify

import configparser
import os
from json import JSONDecodeError

class subSpotify(Spotify):

	''' This is a subclass of spotipy.Spotify for the purpose of defining new methods.
		If you ever want to construct a client with more than just *auth*, __init__ needs to be rewritten.
	'''

	def __init__(self, auth):
		super().__init__(auth)


	def get_tracks_from_playlist(self, playlist_owner, playlist_id):

		''' user_playlist_tracks() returns a "paging object" which only holds 100 items at once,
			so this scrolls through and aggregates all of the requested items into one list.

			Also, the paging object in this case actually holds a list of "playlist track objects",
			which are glorified pointers to the actual track, so the method returns the actual tracks.

			If you want the time the track was added or the user who added it, this method is not for you.
		'''
		try:
			results = self.user_playlist_tracks(playlist_owner, playlist_id)
		except spotipy.SpotifyException as error:
			print("Spotify threw an error while retrieving tracks from spotify:user:{}:playlist:{}:\n{}".format(playlist_owner, playlist_id, error))
			return []

		track_objs = results['items']
		while results['next']:
			results = self.next(results)
			track_objs.extend(results['items'])
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


	def playlists_where_song_appears(self, username, song_id):

		''' Returns a list of playlists that the given song appears in for the given user
		'''
		return_list = []

		for playlist in self.user_playlists(username)['items']:
			tracks = self.get_tracks_from_playlist(playlist['owner']['id'], playlist['id'])
			for song in tracks:
				if song['id'] == song_id:
					return_list.append(playlist)
					break

		return return_list

	


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
			redirect_uri="http://localhost:8888/callback/")

	except (AttributeError, JSONDecodeError):
		os.remove(".cache-{}".format(username))
		token = util.prompt_for_user_token(
			username=username,
			scope=scope,
			client_id=client_id,
			client_secret=client_secret,
			redirect_uri="http://localhost:8888/callback/")

	return token