class CurrentState:
    def __init__(self):
        self.trackname: str = ""
        self.trackimage: str = ""
        self.trackartists: str = ""
        self.trackalbum: str = ""
        self.trackduration: int = 0
        self.trackuri: str = ""

        self.stateisplaying: bool = False
        self.stateprogress: int = 0
        self.stateshuffle: bool = False
        self.staterepeat: bool = False
        self.statedevices: dict[str, DeviceItem] = {}
        self.statevolume: int = 0

        self.playercontexturi: str = ""
        self.playerqueue: dict = {}
        self.playerdeviceid: str = ""

        self.userplaylists: dict = {}


class DeviceItem:
    def __init__(self):
        self.name: str = ""
        self.id: str = ""
        self.volume: int = 0


class PlaylistItem:
    def __init__(self):
        self.name: str = ""
        self.image: str = ""
        self.uri: str = ""
        self.tracks: dict = {}
