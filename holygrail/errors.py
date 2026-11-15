"""Exception domain. Pesan sudah berbahasa Indonesia dan aman ditampilkan ke pengguna."""


class HolyGrailError(Exception):
    """Basis semua error yang aman ditampilkan ke pengguna."""


class ValidationError(HolyGrailError):
    """Input pengguna tidak valid."""


class AuthError(HolyGrailError):
    """Login gagal atau akun terkunci."""


class StockError(HolyGrailError):
    """Stok tidak mencukupi."""


class PaymentError(HolyGrailError):
    """Pembayaran tidak valid (mis. uang kurang)."""


class NotFoundError(HolyGrailError):
    """Data tidak ditemukan."""
