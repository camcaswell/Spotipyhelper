import spotipy
from spotipyhelper import *
 
from py2neo import Graph, Node, Relationship
 
import configparser

# Change tx.merge() statements to tx.run('MERGE...') in order to print stats on how many new nodes were created etc
# Consolidate duplicate albums/songs/artists(?) with a platonic node and SAME_AS relationships
# Write methods for db/Spotify sync

class NoneAsKey(TypeError):
    ''' Raised when trying to construct a node by passing None as an attribute
        when that attribute is supposed to be the key for that type of node.
    '''
    def __init__(self, msg=None):
        super().__init__(msg)

 
class UserNode(Node):
    # id, name
    def __init__(self, id, **otherAttrs):
        if not id:
            raise NoneAsKey('UserNode must have an id.')
        if not name:
            name = id
        super().__init__('User', id=id, **otherAttrs)
        self.__primarylabel__ = 'User'
        self.__primarykey__ = 'id'
 
class PlaylistNode(Node):
    # id, name
    def __init__(self, id, **otherAttrs):
        if not id:
            raise NoneAsKey('PlaylistNode must have an id.')
        super().__init__('Playlist', id=id, **otherAttrs)
        self.__primarylabel__ = 'Playlist'
        self.__primarykey__ = 'id'
 
class SongNode(Node):
    # id, name, pop, duration
    def __init__(self, id, **otherAttrs):
        if not id:
            raise NoneAsKey('SongNode must have an id.')
        super().__init__('Song', id=id, **otherAttrs)
        self.__primarylabel__ = 'Song'
        self.__primarykey__ = 'id'
 
class ArtistNode(Node):
    # id, name, pop
    def __init__(self, id, **otherAttrs):
        if not id:
            raise NoneAsKey('ArtistNode must have an id.')
        super().__init__('Artist', id=id, **otherAttrs)
        self.__primarylabel__ = 'Artist'
        self.__primarykey__ = 'id'
 
class AlbumNode(Node):
    #id, name, pop, release_date
    def __init__(self, id, **otherAttrs):
        if not id:
            raise NoneAsKey('AlbumNode must have an id.')
        super().__init__('Album', id=id, **otherAttrs)
        self.__primarylabel__ = 'Album'
        self.__primarykey__ = 'id'
 
class GenreNode(Node):
    # name
    def __init__(self, name):
        if not name:
            raise NoneAsKey('GenreNode must have a name.')
        super().__init__('Genre', name=name)
        self.__primarylabel__ = 'Genre'
        self.__primarykey__ = 'name'

 
def load_friends(spclient, graph, user_ids): 
    ''' loads friends into the db from a list of their ids
    '''
    tx = graph.begin()

    for user in [spclient.user(x) for x in user_ids]:

        userNode = UserNode(
            id=user['id'],
            name=user['display_name'],
            )
        userNode.add_label('Friend')
        tx.merge(userNode)

    tx.commit()

def load_playlists(spclient, graph):   
    ''' loads playlists followed by friends into the db
        also takes care of FOLLOWS relationships, OWNS relationships,
        and users who own the playlists that are followed by friends
    '''
    tx = graph.begin()

    for user in [record['f'] for record in tx.run("MATCH (f:Friend) RETURN f")]:
        for playlist in spclient.aggregate_paging_results(spclient.user_playlists(user['id'])):
 
            plNode = PlaylistNode(
                id=playlist['id'],
                name=playlist['name'],
                )
            userNode = UserNode(
                id=user['id'],
                name=user['name'],
                )
            plOwnerNode = UserNode(
                id=playlist['owner']['id'],
                name=(playlist['owner']['display_name']),
                )    
            followsRel = Relationship(
                userNode,
                'FOLLOWS',
                plNode,
                )
            ownsRel = Relationship(
                plOwnerNode,
                'OWNS',
                plNode,
                )
 
            tx.merge(plNode)
            #tx.merge(userNode)     not necessary because user nodes should already be in the db
            tx.merge(plOwnerNode)
            tx.merge(followsRel)
            tx.merge(ownsRel)
 
    tx.commit()
 
def load_songs(spclient, graph):
    ''' loads songs that appear on already-loaded playlists into the db
        also takes care of INCLUDES relationships
    '''
    tx = graph.begin()

    for record in tx.run('MATCH (u:User)-[:OWNS]->(p:Playlist) RETURN p,u'):
 
        owner = record['u']
        playlist = record['p']
 
        plNode = PlaylistNode(
            id=playlist['id'],
            )

        for track_obj in spclient.aggregate_paging_results(spclient.user_playlist(owner['id'], playlist['id'])['tracks']):
 
            song = track_obj['track']
            try:
                songNode = SongNode(
                id=song['id'],
                name=song['name'],
                pop=song['popularity'],
                duration=song['duration_ms'],
                )

            except NoneAsKey:
                # This usually means that the song is a local file instead of a Spotify track.
                print(f"This song from playlist: -{playlist['name']}- didn\'t have an id: {song['name']}")

            else:
                inclRel = Relationship(
                plNode,
                'INCLUDES',
                songNode,
                added_at=track_obj['added_at'],
                added_by=track_obj['added_by']['id'],
                )
 
                tx.merge(songNode)
                #tx.merge(plNode)   not necessary because playlist node should already be in db
                tx.merge(inclRel)
 
    tx.commit()

def load_albums(spclient, graph):
    ''' loads album nodes for songs already in the db
        also takes care of ON_ALBUM relationships
        meant to complete all calls to spotify API as quickly as possible before the token expires
    '''
    tx = graph.begin()

    songs_from_db = [record['s'] for record in tx.run('MATCH (s:Song) RETURN s')]

    track_objs = spclient.get_tracks_by_id([song['id'] for song in songs_from_db])
    albums = spclient.get_albums_by_id([track['album']['id'] for track in track_objs])

    assert len(albums) == len(track_objs), "Lengths of album list and track object list came out uneven somehow."

    for index, album in enumerate(albums):

        assert track_objs[index]['album']['id'] == album['id'], "Track and album lists fell out of sync somehow."

        albumNode = AlbumNode(
            id=album['id'],
            name=album['name'],
            pop=album['popularity'],
            release_date=album['release_date'],
            )
        songNode = SongNode(
            id=track_objs[index]['id'],
            )
        alRel = Relationship(
            songNode,
            'ON_ALBUM',
            albumNode,
            )

        tx.merge(albumNode)
        #tx.merge(songNode)     not necessary because the song node should already be in the db
        tx.merge(alRel)

    tx.commit()

def load_artists(spclient, graph):
    ''' loads artist nodes into the db corresponding to the albums that are already loaded
        also takes care of RELEASED relationships
        **does not take care of PERFORMS relationships between artists and songs**
    '''
    tx = graph.begin()

    albums_from_db = [record['a'] for record in tx.run('MATCH (a:Album) RETURN a')]
    albums = spclient.get_albums_by_id([album['id'] for album in albums_from_db])

    for album in albums:
        for artist in spclient.get_artists_by_id([a['id'] for a in album['artists']]):

            artistNode = ArtistNode(
                id=artist['id'],
                name=artist['name'],
                pop=artist['popularity'],
                )
            albumNode = AlbumNode(
                id=album['id'],
                )
            releasedRel = Relationship(
                artistNode,
                'RELEASED',
                albumNode,
                )

            tx.merge(artistNode)
            #tx.merge(albumNode) not necessary because the album node should already be in the db
            tx.merge(releasedRel)

    tx.commit()

def load_performs_rels(spclient, graph):
    ''' loads the PERFORMS relationships between artist and song nodes
        **does not load any nodes**
    '''
    tx = graph.begin()

    songs_from_db = [record['s'] for record in tx.run('MATCH (s:Song) RETURN s')]
    for track in spclient.get_tracks_by_id([song['id'] for song in songs_from_db]):
        for artist in spclient.get_artists_by_id([a['id'] for a in track['artists']]):

            artistNode = ArtistNode(
                id=artist['id'],
                name=artist['name'],
                pop=artist['population'],
                )
            songNode = SongNode(
                id=track['id'],
                )
            perfRel = Relationship(
                artistNode,
                'PERFORMS',
                songNode,
                )

            tx.merge(artistNode)
            #tx.merge(songNode)     not necessary because song nodes should already be in db
            tx.merge(perfRel)

    tx.commit()


def load_genres(spclient, graph):
    ''' loads genre nodes from artist nodes already in the db
        also takes care of GENRE_ASSOC relationships between artist and genre
    '''
    tx = graph.begin()

    artists_from_db = [record['a'] for record in tx.run('MATCH (a:Artist) RETURN a')]
    for artist in spclient.get_artists_by_id([a['id'] for a in artists_from_db]):
        for genre in artist['genres']:

            genreNode = GenreNode(
                name=genre
                )
            artistNode = ArtistNode(
                id=artist['id']
                )
            genreRel = Relationship(
                artistNode,
                'GENRE_ASSOC',
                genreNode
                )

            tx.merge(genreNode)
            #tx.merge(artistNode)   not necessary because artist node should already be in db
            tx.merge(genreRel)

    tx.commit()

def load_genre_album_rels(spclient, graph):
    ''' loads GENRE_ASSOC relationships between album nodes and genre nodes
        **does not load any nodes**
    '''
    tx = graph.begin()

    albums_from_db = [record['a'] for record in tx.run('MATCH (a:Album) RETURN a')]
    for album in spclient.get_albums_by_id(a['id'] for a in albums_from_db):
        for genre in album['genres']:

            genreNode = GenreNode(
                name=genre
                )
            albumNode = AlbumNode(
                id=album['id']
                )
            genreRel = Relationship(
                albumNode,
                'GENRE_ASSOC',
                genreNode
                )

            tx.merge(genreNode)
            #tx.merge(albumNode)    not necessary because album node should already be in db
            tx.merge(genreRel)



 
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
 
    #user_ids = [s.strip() for s in config.get('NEO4J', 'friend_ids').split('\n')]
 
    #load_friends(sp, g, user_ids)
    #load_playlists(sp.refresh(), g)
    #load_songs(sp.refresh(), g)
    #load_albums(sp.refresh(), g)
    #load_artists(sp.refresh(), g)
    load_performs_rels(sp.refresh(), g)
    #load_genres(sp.refresh(), g)
    #load_genre_album_rels(sp.refresh(), g)