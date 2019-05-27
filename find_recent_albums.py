from spotipyhelper import *

from datetime import datetime
import json
import os


def main():

    print("Finding new albums.")

    sp = subSpotify(scope='''
        playlist-read-private 
        playlist-read-collaborative 
        user-follow-read 
        ''')

    saved_songs = [t['track'] for t in sp.aggregate_paging_results(sp.current_user_saved_tracks())]
    saved_artist_ids = {artist['id'] for song in saved_songs for artist in song["artists"]}

    print(f'Found {len(saved_artist_ids)} saved artists.')

    try:
        #If this file doesn't exist yet, all albums will be treated as new and written to the newly created file.
        with open('mr_albums.json', 'x') as created_file:
            created_file.write('{}')
    except:
        pass

    with open('mr_albums.json', 'r') as read_file:
        mr_albums = json.load(read_file)

    new_albums = {}
    for artist_id in saved_artist_ids:
        try:
            albums = sp.aggregate_paging_results(sp.artist_albums(artist_id))
        except:
            #Refresh token
            sp = subSpotify(scope='''
                playlist-read-private 
                playlist-read-collaborative 
                user-follow-read 
                ''')
            albums = sp.aggregate_paging_results(sp.artist_albums(artist_id))

        if albums:
            new_album = max(albums, key=album_date_key)
        else:
            print(f'Couldn\'t find any albums for {artist_id}')
            continue

        if artist_id not in mr_albums or album_date_key(new_album)>album_date_key(mr_albums[artist_id]):
            new_albums[artist_id] = {'album':new_album['name'], 'release_date':new_album['release_date']}
            mr_albums[artist_id] = {'id': new_album['id'], 'release_date':new_album['release_date']}

    if new_albums:
        #Refresh token
        sp = subSpotify(scope='''
            playlist-read-private 
            playlist-read-collaborative 
            user-follow-read 
            ''')
    
        artists = sp.get_artists_by_id(new_albums.keys())

        new_albums_printout = {artist['id']: dict({'artist_name':artist['name']}, **new_albums[artist['id']]) for artist in artists}

        #col_width = max(len(entry) for album in new_albums_printout.values() for entry in album.values())
        col_widths = [max(len(album[col]) for album in new_albums_printout.values()) for col in ['artist_name', 'album', 'release_date']]
        today = datetime.now().date()
        with open('New_Albums.txt', 'a') as log_file:
            log_file.write(f'\n{today}\n')
            for new_album in new_albums_printout.values():
                log_file.write('\t'.join(entry.ljust(col_width) for col_width,entry in zip(col_widths,new_album.values()))+'\n')
    else:
        print("No new albums found.")

    with open('mr_albums.json', 'w') as write_file:
        json.dump(mr_albums, write_file)

    os.system('pause')


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