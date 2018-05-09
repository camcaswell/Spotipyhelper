import spotipy
from spotipyhelper import *


if __name__ == '__main__':
    
    sp = subSpotify(scope='''
        user-library-read
        playlist-read-private
        playlist-modify-private
        ''')
    
    lonely_songs = sp.lonely_songs()


    print(*[s['name'] for s in lonely_songs], sep='\n')
    print(f"You have {len(lonely_songs)} lonely songs")

    if len(lonely_songs) > 0:

        new_playlist = sp.user_playlist_create(
            user=sp.me()['id'],
            name='All the Lonely Songs',
            public=False
            )

        sp.add_tracks_to_playlist(playlist=new_playlist, track_list=lonely_songs)
