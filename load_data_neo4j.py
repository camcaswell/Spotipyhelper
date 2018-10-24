import spotipy
from spotipyhelper import *
 
from py2neo import Graph, Node, Relationship, Subgraph
 
import configparser
import csv
from time import time

class NoneAsKey(TypeError):
    ''' Raised when trying to construct a node by passing None as an attribute
        when that attribute is supposed to be the key for that type of node.
    '''
    def __init__(self, msg=None):
        super().__init__(msg)

 
class UserNode(Node):
    ''' A subclass of py2neo.Node specifically for User nodes.
        Node key: id
        Other properties: name
    '''
    def __init__(self, *otherLabels, id=None, name=None, **otherAttrs):
        if not id:
            raise NoneAsKey('UserNode must have an id.')
        if not name:
            name = id
        super().__init__('User', *otherLabels, id=id, name=name, **otherAttrs)
        self.__primarylabel__ = 'User'
        self.__primarykey__ = 'id'
 
class PlaylistNode(Node):
    ''' A subclass of py2neo.Node specifically for Playlist nodes.
        Node key: id
        Other properties: name
    '''
    def __init__(self, *otherLabels, id=None, name=None, **otherAttrs):
        if not id:
            raise NoneAsKey('PlaylistNode must have an id.')
        # py2neo.Node treats 'name' attributes specially and it doesn't like receiving a None value for 'name'
        if name:
            otherAttrs['name'] = name
        super().__init__('Playlist', *otherLabels, id=id, **otherAttrs)
        self.__primarylabel__ = 'Playlist'
        self.__primarykey__ = 'id'
 
class SongNode(Node):
    ''' A subclass of py2neo.Node specifically for Song nodes.
        Node key: id
        Other properties: name, pop, duration
    '''
    def __init__(self, *otherLabels, id=None, name=None, **otherAttrs):
        if not id:
            raise NoneAsKey('SongNode must have an id.')
        # py2neo.Node treats 'name' attributes specially and it doesn't like receiving a None value for 'name'
        if name:
            otherAttrs['name'] = name
        super().__init__('Song', *otherLabels, id=id, **otherAttrs)
        self.__primarylabel__ = 'Song'
        self.__primarykey__ = 'id'
 
class ArtistNode(Node):
    ''' A subclass of py2neo.Node specifically for Artist nodes.
        Node key: id
        Other properties: name, pop
    '''
    def __init__(self, *otherLabels, id=None, name=None, **otherAttrs):
        if not id:
            raise NoneAsKey('ArtistNode must have an id.')
        # py2neo.Node treats 'name' attributes specially and it doesn't like receiving a None value for 'name'
        if name:
            otherAttrs['name'] = name
        super().__init__('Artist', *otherLabels, id=id, **otherAttrs)
        self.__primarylabel__ = 'Artist'
        self.__primarykey__ = 'id'
 
class AlbumNode(Node):
    ''' A subclass of py2neo.Node specifically for Album nodes.
        Node key: id
        Other properties: name, pop, release_date
    '''
    def __init__(self, *otherLabels, id=None, name=None, **otherAttrs):
        if not id:
            raise NoneAsKey('AlbumNode must have an id.')
        # py2neo.Node treats 'name' attributes specially and it doesn't like receiving a None value for 'name'
        if name:
            otherAttrs['name'] = name
        super().__init__('Album', *otherLabels, id=id, **otherAttrs)
        self.__primarylabel__ = 'Album'
        self.__primarykey__ = 'id'
 
class GenreNode(Node):
    ''' A subclass of py2neo.Node specifically for Genre nodes.
        Node key: name
    '''
    def __init__(self, *otherLabels, name=None, **otherAttrs):
        if not name:
            raise NoneAsKey('GenreNode must have a name.')
        super().__init__('Genre', *otherLabels, name=name, **otherAttrs)
        self.__primarylabel__ = 'Genre'
        self.__primarykey__ = 'name'


def merge_friends(graph, user_ids):
    ''' Merges Friend nodes into the DB from a list of their IDs.
    '''
    print(f"\nmerge_friends() called.")
    mark0 = time()
    for user_id in user_ids:
        with graph.begin() as tx:
            userNode = tx.run('MATCH (u:User {id:$id}) RETURN u', id=user_id)
            if not userNode:
                spclient = subSpotify(scope='''
                    playlist-read-private 
                    playlist-read-collaborative 
                    user-follow-read 
                    ''')
                user = spclient.user(user_id)
                tx.merge(UserNode(
                    'Friend',
                    id=user_id,
                    name=user['name']
                    ))
                print(f"Merged new friend: {user['name']}")


def merge_playlists(graph):
    ''' Merges playlists that are followed by friends in the DB.
        Also merges FOLLOWS and OWNS relationships for the playlists.
        If the owner of the playlist is not already in the DB, it merges a new User node.
    '''
    print(f"\nmerge_playlists() called.")
    mark0 = time()
    with graph.begin() as tx:
        friends_from_db = [record['f'] for record in tx.run('MATCH (f:Friend) RETURN f')]
    print(f"Found {len(friends_from_db)} friends in the DB in {time()-mark0:.1f} seconds.")

    spclient = subSpotify(scope='''
        playlist-read-private 
        playlist-read-collaborative 
        user-follow-read 
        ''')
    mark1 = time()
    users_from_spotify = [spclient.user(friend['id']) for friend in friends_from_db]
    print(f"Retrieved {len(users_from_spotify)} corresponding users from Spotify in {time()-mark1:.1f} seconds.")

    owner_counter = 0
    playlist_counter = 0
    follows_counter = 0
    owns_counter = 0
    assert len(friends_from_db)==len(users_from_spotify), "Numbers of users from DB and Spotify came out uneven."
    for index, user in enumerate(users_from_spotify):
        assert user['id']==friends_from_db[index]['id'], "Users from DB and Spotify fell out of sync."
        for playlist in spclient.aggregate_paging_results(spclient.user_playlists(user['id'])):
            with graph.begin() as tx:
                playlistNode = tx.evaluate('MATCH (p:Playlist {id:$id}) RETURN p', id=playlist['id'])
                if not playlistNode:
                    playlistNode = PlaylistNode(
                        id=playlist['id'],
                        name=playlist['name'],
                        )
                    tx.merge(playlistNode)
                    playlist_counter += 1
                    print(f"Created a new Playlist node for {playlist['name']}")
                tx.merge(Relationship(
                    friends_from_db[index],
                    'FOLLOWS',
                    playlistNode,
                    ))
                follows_counter += 1
                ownerNode = tx.evaluate('MATCH (u:User {id:$id}) RETURN u', id=playlist['owner']['id'])
                if not ownerNode:
                    ownerNode = UserNode(
                        id=playlist['owner']['id'],
                        name=playlist['owner']['name'],
                        )
                    tx.merge(ownerNode)
                    owner_counter += 1
                    print(f"Created a new User node for {playlist['owner']['id']}")
                tx.merge(Relationship(
                    ownerNode,
                    'OWNS',
                    playlistNode,
                    ))
                owns_counter += 1
    print(f"{playlist_counter} new Playlist nodes merged.")
    print(f"{follows_counter} new FOLLOWS relationships merged.")
    print(f"{owner_counter} new User nodes merged.")
    print(f"{owns_counter} new OWNS relationships merged.")


def merge_songs(graph, firstcall=True):
    ''' Merges Song nodes and INCLUDES relationships based on playlists already in the DB.
    '''
    print(f"\nmerge_songs() called on {'first' if firstcall else 'second'} pass.")
    mark0 = time()
    with graph.begin() as tx:
        playlists_from_db = [(record['n'], record['p']) for record in tx.run('MATCH (n:User)-[:OWNS]->(p:Playlist) RETURN n, p')]
    print(f"Found {len(playlists_from_db)} playlists in the DB in {time()-mark0:.1f} seconds.")

    mark1 = time()
    spclient = subSpotify(scope='''
        playlist-read-private 
        playlist-read-collaborative 
        user-follow-read 
        ''')
    playlists_from_spotify = spclient.get_playlists_by_id([(x[0]['id'], x[1]['id']) for x in playlists_from_db])
    print(f"Retrieved {len(playlists_from_spotify)} playlists from Spotify in {time()-mark1:.1f} seconds.")
    assert len(playlists_from_db)==len(playlists_from_spotify), "Number of playlists from the DB vs. Spotify is uneven."

    mark2 = time()
    rel_counter = 0
    song_ids_to_lookup = set([])
    for index, playlist in enumerate(playlists_from_spotify):
        assert playlist['id']==playlists_from_db[index][1]['id'], "Playlists from the DB and Spotify fell out of sync."
        for track_obj in spclient.aggregate_paging_results(playlist['tracks']):
            with graph.begin() as tx:
                songNode = tx.evaluate('MATCH (s:Song {id:$id}) RETURN s', id=track_obj['track']['id'])
                if songNode:
                    tx.merge(Relationship(
                        playlists_from_db[index][1],
                        'INCLUDES',
                        songNode,
                        added_at=track_obj['added_at'],
                        added_by=track_obj['added_by']['id'],
                        ))
                    rel_counter += 1
                else:
                    if track_obj['track']['id']:
                        assert firstcall, ("All tracks are supposed to be merged after first call. "
                            f"{track_obj['track']['name']} was missing on {playlist['name']}.")
                        song_ids_to_lookup.add(track_obj['track']['id'])
                    else:
                        # This usually means that the song is a local file instead of a Spotify track.
                        # print(f"This song from playlist: {playlist['name']} didn't have an id: {song['name']}")
                        pass
        if time()-mark2 > 60:
            print(f"{int((time()-mark0)/60)} minutes elapsed. {rel_counter} total INCLUDES relationships merged.")
            mark2 = time()
    print(f"{rel_counter} total INCLUDES relationships merged.")

    if firstcall:
        if song_ids_to_lookup:
            spclient = subSpotify(scope='''
                playlist-read-private 
                playlist-read-collaborative 
                user-follow-read 
                ''')
            songs_to_merge = spclient.get_tracks_by_id(song_ids_to_lookup)
            print(f"Attempting to merge {len(songs_to_merge)} new Song nodes.")
            for sublist in splitlist(songs_to_merge, 100):
                subgraph = Subgraph([SongNode(id=s['id'], name=s['name'], pop=s['popularity']) for s in sublist])
                with graph.begin() as tx:
                    tx.merge(subgraph)
            print(f"Calling merge_songs() for the second pass.")
            merge_songs(g, firstcall=False)
        else:
            print(f"There are no new songs to merge.")

def merge_albums(graph, firstcall=True):
    ''' Merges Album nodes and ON_ALBUM relationship based on songs already in the DB.
    '''
    print(f"\nmerge_albums() called on {'first' if firstcall else 'second'} pass.")
    mark0 = time()
    with graph.begin() as tx:
        songs_from_db = [record['s'] for record in tx.run('MATCH (s:Song) RETURN s')]
    print(f"Found {len(songs_from_db)} songs in the DB in {time()-mark0:.1f} seconds.")

    mark1 = time()
    spclient = subSpotify(scope='''
        playlist-read-private 
        playlist-read-collaborative 
        user-follow-read 
        ''')
    tracks_from_spotify = spclient.get_tracks_by_id([s['id'] for s in songs_from_db])
    print(f"Retrieved {len(tracks_from_spotify)} corresponding tracks from Spotify in {time()-mark1:.1f} seconds.")
    assert len(songs_from_db)==len(tracks_from_spotify), "Number of songs in the DB vs. tracks from Spotify is uneven."

    mark2 = time()
    rel_counter = 0
    album_ids_to_lookup = set([])
    for index, track in enumerate(tracks_from_spotify):
        assert track['id']==songs_from_db[index]['id'], "Songs from the DB and tracks from Spotify fell out of sync."
        with graph.begin() as tx:
            albumNode = tx.evaluate('MATCH (a:Album {id:$id}) RETURN a', id=track['album']['id'])
            if albumNode:
                tx.merge(Relationship(
                    songs_from_db[index],
                    'ON_ALBUM',
                    albumNode
                    ))
                rel_counter += 1
            else:
                assert firstcall, ("All albums are supposed to be merged after first call. "
                    f"{track['album']['name']} was missing for song: {track['name']}.")
                album_ids_to_lookup.add(track['album']['id'])
        if time()-mark2 > 60:
            print(f"{int((time()-mark0)/60)} minutes elapsed. {rel_counter} total new ON_ALBUM relationships merged.")
            mark2 = time()
    print(f"{rel_counter} total new ON_ALBUM relationships merged.")

    if firstcall:
        if album_ids_to_lookup:
            spclient = subSpotify(scope='''
                playlist-read-private 
                playlist-read-collaborative 
                user-follow-read 
                ''')
            albums_to_merge = spclient.get_albums_by_id(album_ids_to_lookup)
            print(f"Attempting to merge {len(albums_to_merge)} new Album nodes.")
            for sublist in splitlist(albums_to_merge, 100):
                subgraph = Subgraph([AlbumNode(id=a['id'], name=a['name'], pop=a['popularity'], release_date=a['release_date']) for a in sublist])
                with graph.begin() as tx:
                    tx.merge(subgraph)
            print(f"Calling merge_albums for the second pass.")
            merge_albums(graph, firstcall=False)
        else:
            print(f"There are no new albums to merge.")




def merge_artists(graph, firstcall=True):
    ''' Merges RELEASED relationships between existing Album and Artist nodes already in the DB.
        Merges a new Artist node if necessary, then its corresponding RELEASED relationship on the second pass.
    '''
    print(f"\nmerge_artists() called on {'first' if firstcall else 'second'} pass.")
    mark0 = time()
    with graph.begin() as tx:
        albums_from_db = [record['a'] for record in tx.run('MATCH (a:Album) RETURN a')]
    print(f"Found {len(albums_from_db)} albums in the DB in {time()-mark0:.1f} seconds.")

    mark1 = time()
    spclient = subSpotify(scope='''
        playlist-read-private 
        playlist-read-collaborative 
        user-follow-read 
        ''')
    albums_from_spotify = spclient.get_albums_by_id([a['id'] for a in albums_from_db])
    print(f"Retrieved {len(albums_from_spotify)} corresponding albums from Spotify in {time()-mark1:.1f} seconds.")
    assert len(albums_from_db)==len(albums_from_spotify), "Number of albums from the DB vs. Spotify is uneven."

    artist_ids_to_lookup = set([])
    rel_counter = 0
    mark2 = time()
    for index, album in enumerate(albums_from_spotify):
        assert album['id']==albums_from_db[index]['id'], "Albums from the DB and Spotify fell out of sync."
        for artist in album['artists']:
            with graph.begin() as tx:
                artistNode = tx.evaluate('MATCH (a:Artist {id:$id}) RETURN a', id=artist['id'])
                if artistNode:
                    tx.merge(Relationship(
                        artistNode,
                        'RELEASED',
                        albums_from_db[index],
                        ))
                    rel_counter += 1
                else:
                    assert firstcall, ("All artists are supposed to be merged after first call. "
                        f"{artist['name']} was missing for album: {album['name']}.")
                    artist_ids_to_lookup.add(artist['id'])
        if time()-mark2 > 60:
            print(f"{int((time()-mark0)/60)} minutes elapsed. {rel_counter} total new PERFORMS relationships merged.")
            mark2 = time()
    print(f"{rel_counter} total new PERFORMS relationships merged.")

    if firstcall:
        if artist_ids_to_lookup:
            spclient = subSpotify(scope='''
                playlist-read-private 
                playlist-read-collaborative 
                user-follow-read 
                ''')     
            artists_to_merge = spclient.get_artists_by_id(artist_ids_to_lookup)
            print(f"Attempting to merge {len(artists_to_merge)} new Artist nodes.")
            for sublist in splitlist(artists_to_merge, 100):
                subgraph = Subgraph([ArtistNode(id=a['id'],name=a['name'],pop=a['popularity']) for a in sublist])
                with graph.begin() as tx:
                    tx.merge(subgraph)
            print(f"Calling merge_performs_rels() for the second pass.")
            merge_artists(graph, firstcall=False)
        else:
            print(f"There are no new artists to merge.")




def merge_performs_rels(graph, firstcall=True):
    ''' Merges PERFORMS relationships between Artist and Song nodes based on Song nodes in the DB.
        Merges a new Artist node if necessary, and then its corresponding PERFORMS relationship on the second pass.
    '''
    print(f"\nmerge_performs_rels() called on {'first' if firstcall else 'second'} pass.")
    mark0 = time()
    with graph.begin() as tx:
        query_result = tx.run('MATCH (s:Song) RETURN s')  
    songs_from_db = [record['s'] for record in query_result]
    print(f"Found {len(songs_from_db)} songs in the DB in {time()-mark0:.1f} seconds.")
    
    mark1 = time()
    spclient = subSpotify(scope='''
        playlist-read-private 
        playlist-read-collaborative 
        user-follow-read 
        ''')
    tracks_from_spotify = spclient.get_tracks_by_id([song['id'] for song in songs_from_db])
    print(f"Retrieved {len(tracks_from_spotify)} corresponding tracks from Spotify in {time()-mark1:.1f} seconds.")
    assert len(songs_from_db) == len(tracks_from_spotify), "Number of songs from the DB and tracks from Spotify are uneven."
   
    mark2 = time()
    rel_counter = 0
    artist_ids_to_lookup = set([])
    for index, track in enumerate(tracks_from_spotify):
        assert track['id'] == songs_from_db[index]['id'], "DB songs and Spotify songs fell out of sync."
        for artist in track['artists']:
            with graph.begin() as tx:
                artistNode = tx.evaluate('MATCH (a:Artist {id:$id}) RETURN a', id=artist['id'])
                if artistNode:
                    tx.merge(Relationship(
                        artistNode,
                        'PERFORMS',
                        songs_from_db[index],
                        ))
                    rel_counter += 1
                else:
                    assert firstcall, (f"All artists are supposed to be merged after first call. "
                        f"{artist['name']} was missing for track: {track['name']}.")
                    artist_ids_to_lookup.add(artist['id'])
        if time()-mark2 > 60:
            print(f"{int((time()-mark0)/60)} minutes elapsed. {rel_counter} total new PERFORMS relationships merged.")
            mark2 = time()
    print(f"{rel_counter} total new PERFORMS relationships merged.")

    if firstcall and artist_ids_to_lookup:
        spclient = subSpotify(scope='''
            playlist-read-private 
            playlist-read-collaborative 
            user-follow-read 
            ''')
        artists_to_merge = spclient.get_artists_by_id(artist_ids_to_lookup)
        print(f"Attempting to merge {len(artists_to_merge)} new Artist nodes.")
        for sublist in splitlist(artists_to_merge, 100):
            subgraph = Subgraph([ArtistNode(id=a['id'],name=a['name'],pop=a['popularity']) for a in sublist])
            with graph.begin() as tx:
                tx.merge(subgraph)
        print(f"Calling merge_performs_rels() for the second pass.")
        merge_performs_rels(graph, firstcall=False)


def merge_genres(graph):
    ''' Merges Genre nodes from Artist nodes already in the DB.
        Also takes care of GENRE_ASSOC relationships between Artist and Genre nodes.
    '''
    print("\nmerge_genres() called.")
    mark0 = time()
    with graph.begin() as tx:
        artists_from_db = [record['a'] for record in tx.run('MATCH (a:Artist) RETURN a')]
        print(f"Found {len(artists_from_db)} artists in the DB.")
        #albums_from_db = [record['b'] for record in tx.run('MATCH (b:Album) RETURN b')]
        #print(f"Found {len(albums_from_db)} albums in the DB.")

    spclient = subSpotify(scope='''
        playlist-read-private 
        playlist-read-collaborative 
        user-follow-read 
        ''')
    artists_from_spotify = spclient.get_artists_by_id([a['id'] for a in artists_from_db])
    print(f"Retrieved {len(artists_from_spotify)} corresponding artists from Spotify.")
    #albums_from_spotify = spclient.get_albums_by_id([b['id'] for b in albums_from_db])
    #print(f"Retrieved {len(albums_from_spotify)} corresponding albums from Spotify.")

    node_counter = 0
    rel_counter = 0
    mark1 = mark2 = time()
    assert len(artists_from_db) == len(artists_from_spotify), "Number of artists from DB and Spotify came out uneven."
    for index, artist in enumerate(artists_from_spotify):
        assert artist['id'] == artists_from_db[index]['id'], "Artists from Spotify and DB fell out of sync."
        for genre_name in artist['genres']:
            with graph.begin() as tx:
                genreNode = tx.evaluate('MATCH (g:Genre {name:$name}) RETURN g', name=genre_name)
                if not genreNode:
                    genreNode = GenreNode(name=genre_name)
                    node_counter += 1
                genreRel = Relationship(
                    artists_from_db[index],
                    'GENRE_ASSOC',
                    genreNode,
                    )
                rel_counter += 1
                tx.merge(genreNode | genreRel)
        if time()-mark1 > 60:
            print(
                f"{int((time()-mark0)/60)} minutes elapsed. "
                f"{node_counter} new Genre nodes created. "
                f"{rel_counter} GENRE_ASSOC relationships created."
                )
            mark1 = time()

    print(f"Artist-genre associations completed in {int((time()-mark2)/60)} minutes.")
    print(f"{node_counter} new Genre nodes created. {rel_counter} GENRE_ASSOC relationships created.")

    # Currently Spotify doesn't populate the 'genres' attribute of Album objects. They may start in the near future, though.
    '''
    mark1 = mark2 = time()
    assert len(albums_from_db) == len(albums_from_spotify), "Number of albums from DB and Spotify came out uneven."
    for index, album in enumerate(albums_from_spotify):
        assert album['id'] == albums_from_db[index]['id'], "Albums from Spotify and DB fell out of sync."
        for genre_name in album['genres']:
            with graph.begin() as tx:
                genreNode = tx.evaluate('MATCH (g:Genre {name:$name}) RETURN g', name=genre_name)
                if not genreNode:
                    genreNode = GenreNode(name=genre_name)
                    genre_counter += 1
                genreRel = Relationship(
                    albums_from_db[index],
                    'GENRE_ASSOC',
                    genreNode,
                    )
                rel_counter += 1
                tx.merge(Subgraph(genreNode | genreRel))
        if time()-mark1 > 60:
            print(
                f"{int((time()-mark0)/60)} minutes elapsed. "
                f"{node_counter} new Genre nodes created. "
                f"{rel_counter} GENRE_ASSOC relationships created."
                )
            mark1 = time()

    print(f"Album-genre associations completed in {int((time()-mark2)/60)} minutes.")
    print(f"{node_counter} new Genre nodes created. {rel_counter} GENRE_ASSOC relationships created.")
    '''

def sanitize(stringyboi):
    ''' For sanitizing strings to be used in DB queries.
        You should probably be using parameters instead.
    '''
    return stringyboi.translate(str.maketrans({
        '\'':'\\\'',
        '\"':'\\\"',
        '\\':'\\\\',
        }))


if __name__ == '__main__':

    sp = subSpotify(scope='''
        playlist-read-private 
        playlist-read-collaborative 
        user-follow-read 
        ''')
 
    config = configparser.ConfigParser()
    config.read('config.cfg') 
    user = config.get('NEO4J', 'user')
    password = config.get('NEO4J', 'password')
    
    g = Graph('http://localhost:7474/db/data', user=user, password=password)
 
    merge_friends(g, [s.strip() for s in config.get('NEO4J', 'friend_ids').split('\n')])
    merge_playlists(g)
    merge_songs(g)
    merge_albums(g)
    merge_artists(g)
    merge_performs_rels(g)
    merge_genres(g)
