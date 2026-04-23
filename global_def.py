import utils.log_utils
import getpass
import platform
log = utils.log_utils.logging_init(__file__, "jbd4040_ctl_v2.log")


current_user = getpass.getuser()
# Media File Uri Path
if  platform.machine() == 'x86_64':
    MEDIAFILE_URI_PATH = f"/home/{current_user}/Videos/"
    SNAPSHOTS_URI_PATH = f"/home/{current_user}/Videos/Snapshots/"
    RECORDINGS_URI_PATH = f"/home/{current_user}/Videos/Recordings/"
    MEDIA_URI_PATH = f"/home/{current_user}/Videos/Media/"
    THUMBNAILS_URI_PATH = f"/home/{current_user}/Videos/thumbnails/"
    PLAYLISTS_URI_PATH = f"/home/{current_user}/Videos/Playlists/"
    PERSIST_CONFIG_URI_PATH = f"/home/{current_user}/Videos/persist/"
else:
    MEDIAFILE_URI_PATH = "/root/MediaFiles/"
    SNAPSHOTS_URI_PATH = "/root/MediaFiles/Snapshots/"
    RECORDINGS_URI_PATH = "/root/MediaFiles/Recordings/"
    MEDIA_URI_PATH = "/root/MediaFiles/Media/"
    THUMBNAILS_URI_PATH = "/root/MediaFiles/thumbnails/"
    PLAYLISTS_URI_PATH = "/root/MediaFiles/Playlists/"
    PERSIST_CONFIG_URI_PATH = "/root/persist_config/"