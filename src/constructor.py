import stateclass as sc


def get_player_state(current_playbackJSON) -> sc.PlayerState:
    ps = sc.PlayerState("")
    ps.isplaying = current_playbackJSON["is_playing"]
    try:
        ps.contexturi = current_playbackJSON["context"]["uri"]
    except:
        pass
    try:
        ps.progress = int(current_playbackJSON["progress_ms"] / 1000)
    except:
        ps.progress = 0
    ps.shuffle = current_playbackJSON["shuffle_state"]
    return ps


def get_play_state(current_playbackJSON) -> bool:
    return current_playbackJSON["is_playing"]


def get_current_track(current_playbackJSON, from_history: bool = False) -> sc.TrackItem:
    if not from_history:
        ps = make_TrackItem(current_playbackJSON["item"])
    else:
        ps = make_TrackItem(current_playbackJSON["items"][0]["track"])
    return ps


def get_current_playlist(current_playback) -> sc.PlaylistItem:
    pass


def get_current_queue(queueJSON) -> dict[str, sc.TrackItem] | None:
    if queueJSON is not None:
        que: dict[str, sc.DeviceItem] = {}
        for trackJSON in queueJSON:
            track = make_TrackItem(trackJSON)
            if track is not None:
                que[track.uri] = track
        return que
    else:
        return None


def get_current_device(
    current_playbackJSON, user_devices: dict[str, sc.DeviceItem]
) -> sc.DeviceItem | None:
    actualdevice = None
    for id, device in user_devices.items():
        if id == current_playbackJSON["device"]["id"]:
            actualdevice = make_DeviceItem(current_playbackJSON["device"])
            return actualdevice
    return None


def get_context_uri(current_playback) -> str:
    pass


def get_user_playlists(user_playlistsJSON) -> dict[str, sc.PlaylistItem]:
    userpis: dict[str, sc.PlaylistItem] = {}
    for playlistJSON in user_playlistsJSON["items"]:
        pi = sc.PlaylistItem(
            name=playlistJSON["name"],
            image=(
                playlistJSON["images"][0]["url"]
                if playlistJSON["images"] is not None
                else "none"
            ),
            uri=playlistJSON["uri"],
            tracks={},
        )
        userpis[pi.uri] = pi
    return userpis


def get_playlist_items(playlistitemsJSON) -> dict[str, sc.TrackItem]:
    pitracks: dict[str, sc.TrackItem] = {}
    for trackJSON in playlistitemsJSON["items"]:
        trackObjJSON = trackJSON["track"]
        track = make_TrackItem(trackObjJSON)
        if track is not None:
            pitracks[track.uri] = track
    return pitracks


def get_user_devices(user_devicesJSON) -> dict[str, sc.DeviceItem]:
    devices: dict[str, sc.DeviceItem] = {}
    for device in user_devicesJSON["devices"]:
        dev = make_DeviceItem(device)
        devices[dev.id] = dev
    return devices


def set_device_state(
    currentdevice: sc.DeviceItem, user_devices: dict[str, sc.DeviceItem]
) -> sc.DeviceItem:
    for id, device in user_devices.items():
        return device if device.name == currentdevice.name else None


def make_TrackItem(trackdataJSON) -> sc.TrackItem | None:
    artiststr = ""
    try:
        for i in trackdataJSON["artists"]:
            artiststr = artiststr + i["name"] + ", "
        artiststr = artiststr[0:-2]
        ti = sc.TrackItem(
            name=trackdataJSON["name"],
            artists=artiststr,
            album=trackdataJSON["album"]["name"],
            image=trackdataJSON["album"]["images"][1]["url"],
            duration=int(trackdataJSON["duration_ms"] / 1000),
            uri=trackdataJSON["uri"],
        )
    except TypeError:
        return None
    return ti


def make_DeviceItem(DevicedataJSON) -> sc.DeviceItem:
    di = sc.DeviceItem(
        name=DevicedataJSON["name"],
        id=DevicedataJSON["id"],
        volume=DevicedataJSON["volume_percent"],
    )
    return di
