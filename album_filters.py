import re

def garbage_album(album):

    if len(album['artists']) > 10:
        return True

    pat = re.compile('|'.join([

            #Genres
            r"\bR[n&]B\b",
            r"\bHip[ -]?Hop\b",
            r"\bR'N'B\b",
            r"\bPop\b",
            r"\bSoul\b",
            r"\bCountry\b",
            r"\bJazz\b",
            r"\bDance\b",
            r"\bElectronic\b",
            r"\bRock\b",
            r"\bAlt(?:ernative)?\b",
            r"\bFunk\b",
            r"\bRap\b",

            #Compilations
            r"[0-9]0(?:[\']?s)?\b",
            r"\b(?:19|20)[0-9]{2}\b",
            r"\bCompilation\b",
            r"\bGreatest\b",
            r"\bGreat[s]?\b",
            r"\bBest Of\b",
            r"\bClassic[s]?\b",
            r"\bOldies\b",
            r"\bNow That\'?s What I Call\b",
            r"\bHits\b",
            r"\bOne Hit Wonders\b",
            r"\bCollection\b",
            r"\bAward[ -]Winning\b",
            r"\bUltimate\b",
            r"\bBallads",

            #Playlists
            r"\b(?:Summer|Autumn|Winter|Spring|Christmas)\b",
            r"\bSummertime\b",
            r"\bSeason(?:al|\'s)?\b",
            r"\bHoliday[s]?\b",
            r"\bBBQ\b",
            r"\bBarbecue\b",
            r"\bPlaylist[s]?\b",
            r"\bSong[s]?\b",
            r"\bBanger[sz]?\b",
            r"\bChilled\b",
            r"\bBeats\b",
            r"\bParty\b",
            r"\bMusic\b",
            r"\bRomantic\b",
            r"\bMood[sz]?\b",
            r"\bKaraoke\b",
            r"\bThrowback[s]?\b",
            r"\bRewind[s]?\b",
            r"\bSnuggle\b",
            r"\bGroove[sz]?\b",
            r"\bTune[sz]?\b",
            r"\bVibe[sz]?\b",
            r"\bBop[sz]?\b",
            r"\bJam[sz]?\b",
            r"\bAnthem[sz]?\b",
            r"\bMellow\b",
            r"\bPositive\b",
            r"\bJukebox\b",

            #Rereleases
            r"[\]\(][^\(\[\)\]]*Live[^\(\[\)\]]*[\)\]]",
            r"\bInstrumental[s]?\b",
            r"\bRemaster(?:ed)?\b",
            r"\bAcoustic\b",
            r"\bRemix(?:es)?\b",
            r"\bVersion\b",
            r"\bVol(?:\.|ume)?\b",
            r"\bDeluxe\b",
            r"\bMix(?:es)?\b",
            r"\bAlbum[s]?\b",

            #Other
            r"\bOriginal\b.*\bScore[s]?\b",
            r"\bSoundtrack[s]?\b",
            r"\bMovie\b",

            ]),
        re.IGNORECASE
        )
    return re.search(pat, album['name'])

def garbage_filter_test():
    names = [
        'Fast Hip-Hop Urban R&B',
        '80\'s Supershow   ',
        'Beat the World (Original Motion Picture Soundtrack)',
        'Sorry To Bother You (Original Score)',
        'Time for Music: Relaxing Instrumental Playlists for Lovers',
        'Now That\'s What I Call Music!',
        '00s Hits',
        '100 Greatest Hip-Hop',
        'Vol. 3 (Live Version)',
        'Classic Rock',
        'Alt Rock for salt socks',
        'the alt-rock for malt mocks',
        ' this (remastered)',
        'songs (Acoustic version)',
        'Heartbreak Instrumentals',
        'Playlist: only the bangers',
        'hip hop on pop',
        'Rnb',
        'old album (new version)',
        'instrumental',
    ]

    tests = [{'name':name, 'artists':[]} for name in names]
    tests.append({'name': 'collab album', 'artists':['drake' for _ in range(11)]})

    for test in tests:
        print()
        print(test)
        print(garbage_album(test))

if __name__ == '__main__':
    garbage_filter_test()