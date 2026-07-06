class MusicError(Exception):
    """Excepción base del sistema de música."""


class SearchError(MusicError):
    """No se encontraron resultados."""


class StreamError(MusicError):
    """No fue posible obtener el stream."""


class UnsupportedUrlError(MusicError):
    """La URL no pertenece a un servicio soportado."""


class SpotifyError(MusicError):
    """Error al consultar Spotify."""