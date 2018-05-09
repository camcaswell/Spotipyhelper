import spotipy
from spotipyhelper import *


if __name__ == '__main__':

	sp = subSpotify(scope='''
		playlist-read-private 
		playlist-read-collaborative 
		user-follow-read 
		''')

	song_uri = input("\nPaste song URI here: ")

	try:
		while (song_uri != "x"):

			try:
				song = sp.track(song_uri)

				playlists = sp.playlists_where_song_appears(sp.me()['id'], song['id'])

				if playlists:
					print(f"\n{song['name']} appears in: \n")
					for playlist in playlists:
						print(f"* {playlist['name']}")

				else:
					print(f"\n{song['name']} doesn't appear in any of your playlists.")

			except spotipy.SpotifyException:
				print("Invalid URI")

			song_uri = input("\nPaste song URI here: ")

	except Exception as error:
		print(f"something went wrong:\n{error}")
		input()