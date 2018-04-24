import spotipy
from spotipyhelper import *

''' try with set subtraction
'''

token = generate_token('''
						user-library-read
						playlist-read-private
						playlist-modify-private
						''')

sp = subSpotify(auth=token)

first_return = sp.current_user_saved_tracks()
pointers = sp.aggregate_paging_results(first_return)
library = [p['track'] for p in pointers]

lonely_songs = []
for song in library:
	if sp.playlists_where_song_appears(sp.me()['id'], song['id']) == []:
		lonely_songs.append(song)

print(*[s['name'] for s in lonely_songs], sep='\n')
print(len(lonely_songs))

sp.user_playlist_create(user=sp.me()['id'],
						name='All the Lonely Songs',
						public=False,
						description='The ones that slipped through the cracks')

playlists = sp.user_playlists(sp.me()['id'])
filtered = list(filter(lambda p: p['name']=='All the Lonely Songs', playlists))

if len(filtered)==1:
	new_playlist = filtered[0]
else:
	print("Something went wrong; ended up with too many playlists")
	quit()

sp.user_playlist_add_tracks(sp.me()['id'],
							new_playlist['id'],
							[s['id'] for s in lonely_songs])