import spotipy
from spotipyhelper import *

import json

def main():

    sp = subSpotify(scope='''
        playlist-read-private 
        playlist-read-collaborative 
        user-follow-read 
        ''')

    saved_songs = [t['track'] for t in sp.aggregate_paging_results(sp.current_user_saved_tracks())]
    saved_artist_ids = {artist['id'] for song in saved_songs for artist in song["artists"]}

    mr_albums = {}

    for artist_id in saved_artist_ids:
        albums = sp.aggregate_paging_results(sp.artist_albums(artist_id))
        mr_album = max(albums, key=album_date_key)
        mr_albums[artist_id] = {'id': mr_album['id'], 'date':mr_album['release_date']}

    with open('mr_albums.json', 'w') as write_file:
        json.dump(mr_albums, write_file)

    print("done")

def album_date_key(album):

    date_list = album['release_date'].split('-')
    if len(date_list)==1:
        date_list.extend(["00", "00"])
    elif len(date_list)==2:
        date_list.extend(["00"])
    elif len(date_list)!=3:
        raise ValueError("Date string has the wrong number of components.")

    if len(date_list[0])!=4:
        raise ValueError("Year component of date string is the wrong length.")

    for i,c in enumerate(date_list[1:]):
        if len(c)==1:
            date_list[i+1] = "0"+c
        elif len(c)!=2:
            raise ValueError("Date string component is the wrong length.")

    ret_string = ''
    for c in date_list:
        ret_string += c
    return ret_string

if __name__=='__main__':
    main()