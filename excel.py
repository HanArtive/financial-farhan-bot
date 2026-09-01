import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# =========================
# SUPABASE
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL belum diatur.")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY belum diatur.")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# =========================
# TAMBAH TRANSAKSI
# =========================

def add_transaction(
    jenis,
    kategori,
    nominal,
    keterangan=""
):

    response = (
        supabase
        .table("transaksi")
        .insert({
            "jenis": jenis,
            "kategori": kategori,
            "nominal": nominal,
            "keterangan": keterangan
        })
        .execute()
    )

    if not response.data:
        raise Exception(
            "Transaksi gagal disimpan ke Supabase."
        )

    transaction = response.data[0]

    transaction_id = transaction["id"]

    # Ambil tanggal dari database jika tersedia
    tanggal_raw = transaction.get("tanggal")

    if tanggal_raw:
        try:
            tanggal = datetime.fromisoformat(
                str(tanggal_raw).replace(
                    "Z",
                    "+00:00"
                )
            )
        except (ValueError, TypeError):
            tanggal = datetime.now(timezone.utc)
    else:
        tanggal = datetime.now(timezone.utc)

    return transaction_id, tanggal