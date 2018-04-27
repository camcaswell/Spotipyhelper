import spotipy
from spotipyhelper import *


if __name__ == '__main__':

	token = generate_token('''
		playlist-read-private 
		playlist-read-collaborative 
		user-follow-read 
		''')

	if token:
		sp = subSpotify(auth=token)
	else:
		print("Failed to get token.")
		quit()

	song_uri = input("Paste song URI here: ")
	try:
		song = sp.track(song_uri)
	except (spotipy.SpotifyException):
		print("Invalid URI")
		quit()

	playlists = sp.playlists_where_song_appears(sp.me()['id'], song['id'])

	print(f"\n{song['name']} appears in: \n")
	for playlist in playlists:
		print(playlist['name'])
