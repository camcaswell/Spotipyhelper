from spotipyhelper import *
from album_filters import *

import os
from prettytable import PrettyTable
import re
from datetime import datetime


def find_new_albums():

    print("Finding new albums.")

    sp = subSpotify(scope='''
        playlist-read-private 
        playlist-read-collaborative 
        user-follow-read 
        ''')

    datestring = input('Cutoff date (yyyy-mm-dd): ')

    saved_artists = sp.get_saved_artists()

    print(f'Found {len(saved_artists)} saved artists.')

    new_albums = sp.albums_after(datestring, saved_artists)

    # Filter out garbage albums
    new_albums = {a_id:(artist, [(a,d) for a,d in a_w_d if not garbage_album(a)]) for a_id, (artist, a_w_d) in new_albums.items()}
    # Remove any artists that have no new albums left
    new_albums = {a_id:(artist, a_w_d) for a_id, (artist, a_w_d) in new_albums.items() if a_w_d}


    if new_albums:
        table = PrettyTable(['Artist', 'Album', 'Release Date'])
        artists = [a for a,_ in new_albums.values()]
        artists.sort(key= lambda a: a['name'])
        for artist in artists:
            _,albums_with_dates = new_albums[artist['id']]
            albums_with_dates = [(a,d) for a,d in albums_with_dates if not garbage_album(a)]
            if albums_with_dates:
                first_album, first_date = albums_with_dates[0]
                table.add_row([artist['name'], first_album['name'], first_date])
                for album, date in albums_with_dates[1:]:
                    table.add_row(['', album['name'], date])

        with open('New_Albums.txt', 'a', encoding='utf-8') as write_file:
            write_file.write(f'\nNew albums between {datestring} and {datetime.now().date()}\n')
            write_file.write(table.get_string())

        print(table.get_string())


    else:
        print("No new albums found.")

    os.system('pause')


if __name__=='__main__':
    find_new_albums()