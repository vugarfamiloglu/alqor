"""Alqor → JavaScript hədəfi (`alqor qur --hədəf js|veb`)."""

from .derleyici import (KompilyasiyaXətası, kompilyasiya, mətndən,
                        node_faylı, veb_səhifəsi)

__all__ = ["KompilyasiyaXətası", "kompilyasiya", "mətndən", "node_faylı",
           "veb_səhifəsi"]
