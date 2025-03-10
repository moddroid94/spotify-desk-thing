from dataclasses import dataclass


@dataclass
class TrackItem:
    name: str
    artists: str
    album: str
    image: str
    duration: int
    uri: str


@dataclass
class PlaylistItem:
    name: str
    image: str
    uri: str
    tracks: dict[str, TrackItem]


@dataclass
class DeviceItem:
    name: str
    id: str
    volume: int


@dataclass
class PlayerState:
    contexturi: str
    isplaying: bool = False
    progress: int = 0
    shuffle: bool = False
    repeat: bool = False


@dataclass
class CurrentState:
    actualtrack: TrackItem | None = None
    actualplaylist: PlaylistItem | None = None
    actualdevice: DeviceItem | None = None
    actualqueue: dict[str, TrackItem] | None = None

    playerstate: PlayerState | None = None

    userdevices: dict[str, DeviceItem] | None = None
    userplaylists: dict[str, PlaylistItem] | None = None
