def garbage_album(album):
    pat = re.compile('|'.join([
            r"[0-9]0(?:\')?s",
            r"\bClassic\b",
            r"\bR[n&]B\b",
            r"\bAlt(?: |-)Rock\b",
            r"\bHip(?: |-)Hop\b",
            r"\b(?:Summer|Fall|Winter|Spring|Christmas) (?:Pop|Rock)",
            r"\b[0-9]{2,4} Greatest\b",
            r"\([^\(]*Live[^\)]*\)",
            r"\bPlaylist\b",
            r"\bOriginal.*(?:Score|Soundtrack)\b",
            r"\bInstrumentals?\b",
            r"\bRemaster(?:ed)?\b",
            r"\bAcoustic\b",
            r"\bNow That\'?s What I Call Music\b",
            ]),
        re.IGNORECASE
        )
    return len(album['artists']) > 10 or re.search(pat, album['name'])

def garbage_filter_test():
    tests = [
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
    ]

    for test in tests:
        print()
        print(test, garbage_album(test))