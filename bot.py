import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Dummy HTTP Server agar Web Service Render tetap Live
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Farhan Aktif!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Jalankan server HTTP di latar belakang (background thread)
threading.Thread(target=run_dummy_server, daemon=True).start()
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import MessageHandler, filters
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from supabase import create_client
from excel import add_transaction

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# Menyimpan transaksi yang sedang menunggu konfirmasi hapus/edit
pending_delete = {}
pending_edit = {}

# ==========================================
# HELPER: Dapatkan Rentang Periode Tanggal 11
# ==========================================

def get_periode_berjalan(dt=None):
    """
    Menghitung awal periode (tgl 11) dan akhir periode (tgl 10 bulan depan)
    berdasarkan tanggal yang diberikan (default: hari ini).
    """
    if dt is None:
        dt = datetime.now(timezone.utc)

    # Jika hari ini tgl 11 atau lebih, periode mulai tgl 11 bulan ini
    if dt.day >= 11:
        awal_periode = dt.replace(day=11, hour=0, minute=0, second=0, microsecond=0)
    else:
        # Jika sebelum tgl 11, periode mulai tgl 11 bulan sebelumnya
        # Mengurangi bulan dengan aman
        bulan_lalu = dt.month - 1 if dt.month > 1 else 12
        tahun_lalu = dt.year if dt.month > 1 else dt.year - 1
        awal_periode = dt.replace(year=tahun_lalu, month=bulan_lalu, day=11, hour=0, minute=0, second=0, microsecond=0)

    # Akhir periode adalah H-1 dari tgl 11 bulan berikutnya (tgl 10)
    if awal_periode.month == 12:
        bulan_depan = 1
        tahun_depan = awal_periode.year + 1
    else:
        bulan_depan = awal_periode.month + 1
        tahun_depan = awal_periode.year

    akhir_periode = awal_periode.replace(year=tahun_depan, month=bulan_depan, day=11) - timedelta(seconds=1)

    return awal_periode, akhir_periode


# ==========================================
# START
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Halo Farhan 👋\n\n"
        "💰 Finance Bot aktif!\n"
        "📅 Periode Keuangan: Tanggal 11 s/d Tanggal 10 bulan berikutnya.\n\n"

        "📝 TAMBAH TRANSAKSI\n"
        "/tambah Pengeluaran Makan 30000 makan siang\n"
        "/tambah Pengeluaran Bensin 50000 isi bensin\n"
        "/tambah Pemasukan Gaji 5000000 gaji DENSO\n\n"

        "📌 Command lama masih tersedia:\n"
        "/makan 25000 makan siang\n"
        "/bensin 50000 isi bensin"
    )


# ==========================================
# TAMBAH TRANSAKSI UNIVERSAL
# ==========================================

async def tambah(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ Format salah.\n\n"
            "Gunakan:\n"
            "/tambah [Jenis] [Kategori] [Nominal] [Keterangan]\n\n"
            "Contoh:\n"
            "/tambah Pengeluaran Makan 30000 makan siang\n"
            "/tambah Pengeluaran Bensin 50000 isi bensin\n"
            "/tambah Pemasukan Gaji 5000000 gaji DENSO"
        )
        return

    jenis = context.args[0]
    kategori = context.args[1]

    jenis_map = {
        "pengeluaran": "Pengeluaran",
        "pemasukan": "Pemasukan"
    }

    jenis_lower = jenis.lower()

    if jenis_lower not in jenis_map:
        await update.message.reply_text(
            "❌ Jenis transaksi tidak valid.\n\n"
            "Gunakan salah satu:\n"
            "• Pengeluaran\n"
            "• Pemasukan"
        )
        return

    jenis = jenis_map[jenis_lower]

    try:
        nominal = int(context.args[2])
    except ValueError:
        await update.message.reply_text(
            "❌ Nominal harus berupa angka.\n\n"
            "Contoh:\n"
            "/tambah Pengeluaran Makan 30000 makan siang"
        )
        return

    if nominal <= 0:
        await update.message.reply_text("❌ Nominal harus lebih dari 0.")
        return

    keterangan = " ".join(context.args[3:])

    try:
        transaction_id, tanggal = add_transaction(
            jenis=jenis,
            kategori=kategori,
            nominal=nominal,
            keterangan=keterangan
        )
    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text(
            "❌ Transaksi gagal disimpan.\n\n"
            "Cek terminal/PowerShell untuk melihat error."
        )
        return

    nominal_rupiah = f"Rp{nominal:,}".replace(",", ".")

    peringatan_budget = None
    try:
        peringatan_budget = await cek_budget_setelah_transaksi(
            kategori=kategori,
            jenis=jenis
        )
    except Exception as e:
        print("ERROR CEK BUDGET:", e)

    pesan = (
        f"✅ TRANSAKSI TERCATAT\n\n"
        f"🆔 ID: {transaction_id}\n"
        f"📅 Tanggal: {tanggal.strftime('%d/%m/%Y %H:%M')}\n"
        f"📌 Jenis: {jenis}\n"
        f"🏷️ Kategori: {kategori}\n"
        f"💰 Nominal: {nominal_rupiah}\n"
        f"📝 Keterangan: {keterangan or '-'}"
    )

    if peringatan_budget:
        pesan += "\n\n" + peringatan_budget

    await update.message.reply_text(pesan)


# ==========================================
# COMMAND LAMA: MAKAN
# ==========================================

async def makan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Format yang benar:\n/makan 25000 makan siang")
        return

    try:
        nominal = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Nominal harus berupa angka.\nContoh: /makan 25000")
        return

    keterangan = " ".join(context.args[1:])

    transaction_id, tanggal = add_transaction(
        jenis="Pengeluaran",
        kategori="Makan",
        nominal=nominal,
        keterangan=keterangan
    )

    nominal_rupiah = f"Rp{nominal:,}".replace(",", ".")

    peringatan_budget = None
    try:
        peringatan_budget = await cek_budget_setelah_transaksi(
            kategori="Makan",
            jenis="Pengeluaran"
        )
    except Exception as e:
        print("ERROR CEK BUDGET:", e)

    pesan = (
        f"✅ TRANSAKSI TERCATAT\n\n"
        f"🆔 ID: {transaction_id}\n"
        f"📅 Tanggal: {tanggal.strftime('%d/%m/%Y %H:%M')}\n"
        f"📌 Jenis: Pengeluaran\n"
        f"🏷️ Kategori: Makan\n"
        f"💰 Nominal: {nominal_rupiah}\n"
        f"📝 Keterangan: {keterangan or '-'}"
    )

    if peringatan_budget:
        pesan += peringatan_budget

    await update.message.reply_text(pesan)


# ==========================================
# COMMAND LAMA: BENSIN
# ==========================================

async def bensin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Format yang benar:\n/bensin 50000 isi bensin")
        return

    try:
        nominal = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Nominal harus berupa angka.\nContoh: /bensin 50000")
        return

    keterangan = " ".join(context.args[1:])

    transaction_id, tanggal = add_transaction(
        jenis="Pengeluaran",
        kategori="Bensin",
        nominal=nominal,
        keterangan=keterangan
    )

    nominal_rupiah = f"Rp{nominal:,}".replace(",", ".")

    peringatan_budget = await cek_budget_setelah_transaksi(
        kategori="Bensin",
        jenis="Pengeluaran"
    )

    pesan = (
        f"✅ TRANSAKSI TERCATAT\n\n"
        f"🆔 ID: {transaction_id}\n"
        f"📅 Tanggal: {tanggal.strftime('%d/%m/%Y %H:%M')}\n"
        f"📌 Jenis: Pengeluaran\n"
        f"🏷️ Kategori: Bensin\n"
        f"💰 Nominal: {nominal_rupiah}\n"
        f"📝 Keterangan: {keterangan or '-'}"
    )

    if peringatan_budget:
        pesan += peringatan_budget

    await update.message.reply_text(pesan)


# ==========================================
# RIWAYAT TRANSAKSI
# ==========================================

async def riwayat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        limit = 10
        if context.args:
            try:
                limit = int(context.args[0])
            except ValueError:
                await update.message.reply_text(
                    "❌ Jumlah transaksi harus berupa angka.\n\n"
                    "Contoh:\n/riwayat\n/riwayat 20"
                )
                return

        limit = max(1, min(limit, 50))

        response = (
            supabase
            .table("transaksi")
            .select("*")
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        data = response.data

        if not data:
            await update.message.reply_text("📋 Belum ada transaksi.")
            return

        pesan = "📋 RIWAYAT TRANSAKSI\n\n"

        for transaksi in data:
            transaction_id = transaksi.get("id", "-")
            jenis = transaksi.get("jenis", "-")
            kategori = transaksi.get("kategori", "-")
            nominal = transaksi.get("nominal", 0)
            keterangan = transaksi.get("keterangan", "-")
            tanggal = transaksi.get("tanggal", "-")

            try:
                nominal_rupiah = f"Rp{int(nominal):,}".replace(",", ".")
            except (ValueError, TypeError):
                nominal_rupiah = f"Rp{nominal}"

            simbol = "📥" if jenis.lower() == "pemasukan" else "💸"

            pesan += (
                f"🆔 #{transaction_id}\n"
                f"📅 {tanggal}\n"
                f"{simbol} {jenis}\n"
                f"🏷️ {kategori}\n"
                f"💰 {nominal_rupiah}\n"
                f"📝 {keterangan}\n"
                f"────────────────\n"
            )

        await update.message.reply_text(pesan)

    except Exception as e:
        print("ERROR RIWAYAT:", e)
        await update.message.reply_text("❌ Gagal mengambil riwayat transaksi.")


# ==========================================
# HAPUS TRANSAKSI
# ==========================================

async def hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Masukkan ID transaksi.\n\nContoh:\n/hapus 17")
        return

    try:
        transaction_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID transaksi harus berupa angka.")
        return

    try:
        response = supabase.table("transaksi").select("*").eq("id", transaction_id).execute()
        data = response.data

        if not data:
            await update.message.reply_text(f"❌ Transaksi ID #{transaction_id} tidak ditemukan.")
            return

        transaksi = data[0]
        jenis = transaksi.get("jenis", "-")
        kategori = transaksi.get("kategori", "-")
        nominal = transaksi.get("nominal", 0)
        keterangan = transaksi.get("keterangan", "-")
        tanggal = transaksi.get("tanggal", "-")

        nominal_rupiah = f"Rp{int(nominal):,}".replace(",", ".")
        user_id = update.effective_user.id
        pending_delete[user_id] = transaction_id

        await update.message.reply_text(
            f"⚠️️ KONFIRMASI HAPUS TRANSAKSI\n\n"
            f"🆔 ID: #{transaction_id}\n"
            f"📅 Tanggal: {tanggal}\n"
            f"📌 Jenis: {jenis}\n"
            f"🏷️ Kategori: {kategori}\n"
            f"💰 Nominal: {nominal_rupiah}\n"
            f"📝 Keterangan: {keterangan}\n\n"
            f"Ketik YA untuk menghapus atau BATAL untuk membatalkan."
        )
    except Exception as e:
        print("ERROR HAPUS:", e)
        await update.message.reply_text("❌ Gagal mencari transaksi.")


async def konfirmasi_hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in pending_delete:
        return

    jawaban = update.message.text.strip().lower()

    if jawaban == "batal":
        del pending_delete[user_id]
        await update.message.reply_text("❌ Penghapusan dibatalkan.")
        return

    if jawaban != "ya":
        await update.message.reply_text("⚠️ Ketik YA untuk menghapus atau BATAL.")
        return

    transaction_id = pending_delete[user_id]
    try:
        supabase.table("transaksi").delete().eq("id", transaction_id).execute()
        del pending_delete[user_id]
        await update.message.reply_text(f"✅ TRANSAKSI #{transaction_id} BERHASIL DIHAPUS")
    except Exception as e:
        print("ERROR KONFIRMASI HAPUS:", e)
        await update.message.reply_text("❌ Gagal menghapus transaksi.")


# ==========================================
# EDIT TRANSAKSI
# ==========================================

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ Format salah.\n\nContoh:\n/edit 25 Makan 35000 makan malam"
        )
        return

    try:
        transaction_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID harus angka.")
        return

    kategori_baru = context.args[1]

    try:
        nominal_baru = int(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Nominal harus angka.")
        return

    if nominal_baru <= 0:
        await update.message.reply_text("❌ Nominal harus > 0.")
        return

    keterangan_baru = " ".join(context.args[3:])

    try:
        response = supabase.table("transaksi").select("*").eq("id", transaction_id).execute()
        data = response.data

        if not data:
            await update.message.reply_text(f"❌ Transaksi #{transaction_id} tidak ditemukan.")
            return

        transaksi = data[0]
        user_id = update.effective_user.id

        pending_edit[user_id] = {
            "id": transaction_id,
            "kategori": kategori_baru,
            "nominal": nominal_baru,
            "keterangan": keterangan_baru
        }

        await update.message.reply_text(
            f"✏️ KONFIRMASI EDIT TRANSAKSI #{transaction_id}\n\n"
            f"Kategori Baru: {kategori_baru}\n"
            f"Nominal Baru: Rp{nominal_baru:,}".replace(",", ".") + f"\n"
            f"Keterangan Baru: {keterangan_baru or '-'}\n\n"
            f"Ketik YA untuk simpan atau BATAL."
        )

    except Exception as e:
        print("ERROR EDIT:", e)
        await update.message.reply_text("❌ Gagal mengedit transaksi.")


async def konfirmasi_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in pending_edit:
        return

    jawaban = update.message.text.strip().lower()

    if jawaban == "batal":
        del pending_edit[user_id]
        await update.message.reply_text("❌ Perubahan dibatalkan.")
        return

    if jawaban != "ya":
        await update.message.reply_text("⚠️ Ketik YA untuk menyimpan atau BATAL.")
        return

    perubahan = pending_edit[user_id]
    transaction_id = perubahan["id"]

    try:
        supabase.table("transaksi").update({
            "kategori": perubahan["kategori"],
            "nominal": perubahan["nominal"],
            "keterangan": perubahan["keterangan"]
        }).eq("id", transaction_id).execute()

        del pending_edit[user_id]
        await update.message.reply_text(f"✅ TRANSAKSI #{transaction_id} BERHASIL DIUPDATE")
    except Exception as e:
        print("ERROR KONFIRMASI EDIT:", e)
        await update.message.reply_text("❌ Gagal mengupdate transaksi.")


async def konfirmasi_semua(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in pending_delete:
        await konfirmasi_hapus(update, context)
        return
    if user_id in pending_edit:
        await konfirmasi_edit(update, context)
        return


# ==========================================
# CEK SALDO
# ==========================================

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = supabase.table("transaksi").select("jenis, nominal").execute()
        data = response.data

        total_pemasukan = 0
        total_pengeluaran = 0

        for transaksi in data:
            jenis = transaksi.get("jenis", "")
            try:
                nominal = int(transaksi.get("nominal", 0))
            except (ValueError, TypeError):
                nominal = 0

            if jenis.lower() == "pemasukan":
                total_pemasukan += nominal
            elif jenis.lower() == "pengeluaran":
                total_pengeluaran += nominal

        saldo_sekarang = total_pemasukan - total_pengeluaran

        status = "🟢 Saldo masih positif" if saldo_sekarang > 0 else ("🔴 Pengeluaran lebih besar" if saldo_sekarang < 0 else "🟡 Saldo Rp0")

        await update.message.reply_text(
            f"💰 SALDO KEUANGAN TOTAL\n\n"
            f"📥 Pemasukan: Rp{total_pemasukan:,}".replace(",", ".") + "\n"
            f"📤 Pengeluaran: Rp{total_pengeluaran:,}".replace(",", ".") + "\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💵 SALDO: Rp{saldo_sekarang:,}".replace(",", ".") + f"\n\n{status}"
        )
    except Exception as e:
        print("ERROR SALDO:", e)
        await update.message.reply_text("❌ Gagal menghitung saldo.")


# ==========================================
# REKAP KEUANGAN (Siklus Tgl 11)
# ==========================================

async def rekap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        awal_periode, akhir_periode = get_periode_berjalan()

        response = supabase.table("transaksi").select("*").execute()
        data = response.data

        total_pemasukan = 0
        total_pengeluaran = 0
        kategori_pengeluaran = {}
        kategori_pemasukan = {}

        for transaksi in data:
            tanggal = transaksi.get("tanggal")
            if not tanggal:
                continue

            try:
                tanggal_dt = datetime.fromisoformat(tanggal.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            # Filter berdasarkan siklus tgl 11 s/d tgl 10
            if not (awal_periode <= tanggal_dt <= akhir_periode):
                continue

            jenis = transaksi.get("jenis", "")
            kategori = transaksi.get("kategori", "Lainnya")
            try:
                nominal = int(transaksi.get("nominal", 0))
            except (ValueError, TypeError):
                nominal = 0

            if jenis.lower() == "pemasukan":
                total_pemasukan += nominal
                kategori_pemasukan[kategori] = kategori_pemasukan.get(kategori, 0) + nominal
            elif jenis.lower() == "pengeluaran":
                total_pengeluaran += nominal
                kategori_pengeluaran[kategori] = kategori_pengeluaran.get(kategori, 0) + nominal

        def rupiah(angka):
            return f"Rp{angka:,}".replace(",", ".")

        pesan = (
            f"📊 REKAP KEUANGAN PERIODE\n"
            f"📅 {awal_periode.strftime('%d/%m/%Y')} - {akhir_periode.strftime('%d/%m/%Y')}\n\n"
            f"📥 PEMASUKAN\n"
        )

        if kategori_pemasukan:
            for kat, nom in sorted(kategori_pemasukan.items(), key=lambda x: x[1], reverse=True):
                pesan += f"💰 {kat}: {rupiah(nom)}\n"
        else:
            pesan += "Tidak ada pemasukan.\n"

        pesan += "\n📤 PENGELUARAN\n"
        if kategori_pengeluaran:
            for kat, nom in sorted(kategori_pengeluaran.items(), key=lambda x: x[1], reverse=True):
                pesan += f"💸 {kat}: {rupiah(nom)}\n"
        else:
            pesan += "Tidak ada pengeluaran.\n"

        saldo_bulan = total_pemasukan - total_pengeluaran
        pesan += (
            "\n━━━━━━━━━━━━━━━━\n"
            f"📥 Total Masuk: {rupiah(total_pemasukan)}\n"
            f"📤 Total Keluar: {rupiah(total_pengeluaran)}\n"
            f"💵 Sisa Periode: {rupiah(saldo_bulan)}"
        )

        await update.message.reply_text(pesan)

    except Exception as e:
        print("ERROR REKAP:", e)
        await update.message.reply_text("❌ Gagal membuat rekap.")


# ==========================================
# HELP (DIPERBARUI SEMUA FITUR)
# ==========================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 FINANCE BOT FARHAN - MENU BANTUAN\n"
        "📅 Periode Keuangan: Tanggal 11 s/d 10 Bulan Berikutnya\n\n"

        "📝 PENCATATAN TRANSAKSI\n"
        "• /tambah [Jenis] [Kategori] [Nominal] [Keterangan]\n"
        "  Contoh: /tambah Pengeluaran Makan 30000 makan siang\n"
        "  Contoh: /tambah Pemasukan Gaji 5000000 gaji DENSO\n\n"

        "📌 COMMAND CEPAT (LAMA)\n"
        "• /makan [Nominal] [Keterangan]\n"
        "  Contoh: /makan 25000 makan siang\n"
        "• /bensin [Nominal] [Keterangan]\n"
        "  Contoh: /bensin 50000 isi bensin\n\n"

        "✏️ KELOLA TRANSAKSI\n"
        "• /riwayat [jumlah] → Lihat riwayat (opsional: /riwayat 20)\n"
        "• /edit [ID] [Kategori] [Nominal] [Keterangan] → Edit transaksi\n"
        "• /hapus [ID] → Hapus transaksi berdasarkan ID\n\n"

        "📊 INFORMASI & LAPORAN KEUANGAN\n"
        "• /saldo → Cek saldo keseluruhan\n"
        "• /rekap → Rekap singkat keuangan periode ini\n"
        "• /laporan → Laporan keuangan bulanan lengkap (periode tgl 11)\n"
        "• /statistik → Statistik & analisis pengeluaran periode ini\n"
        "• /kategori [nama_kategori] → Cek rincian pengeluaran per kategori\n\n"

        "💵 BUDGETING\n"
        "• /budget → Cek status budget periode ini\n"
        "• /budget [Kategori] [Nominal] → Atur budget per kategori untuk periode berjalan\n"
        "  Contoh: /budget Makan 900000\n\n"

        "🎯 TARGET KEUANGAN (TABUNGAN)\n"
        "• /target [Nama Target] [Target Nominal] [Setoran Bulanan]\n"
        "  Contoh: /target Laptop 6000000 500000\n"
        "• /setor [ID Target] [Nominal] → Setor tabungan ke target\n"
        "  Contoh: /setor 1 500000\n\n"

        "💡 Tips:\n"
        "Setiap perhitungan laporan & budget otomatis direset per tanggal 11!"
    )


# ==========================================
# BUDGET (Siklus Tgl 11)
# ==========================================

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        awal_periode, akhir_periode = get_periode_berjalan()
        bulan_str = str(awal_periode.date())

        if context.args:
            if len(context.args) < 2:
                await update.message.reply_text(
                    "❌ Format salah.\n\n"
                    "Gunakan:\n/budget [Kategori] [Nominal]\n\n"
                    "Contoh:\n/budget Makan 900000"
                )
                return

            kategori = context.args[0]
            try:
                nominal = int(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Nominal harus berupa angka.")
                return

            if nominal <= 0:
                await update.message.reply_text("❌ Nominal budget harus > 0.")
                return

            existing = (
                supabase
                .table("budget")
                .select("*")
                .eq("kategori", kategori)
                .eq("bulan", bulan_str)
                .execute()
            )

            if existing.data:
                supabase.table("budget").update({"nominal": nominal}).eq("kategori", kategori).eq("bulan", bulan_str).execute()
                status = "✏️ Budget berhasil diperbarui."
            else:
                supabase.table("budget").insert({"kategori": kategori, "bulan": bulan_str, "nominal": nominal}).execute()
                status = "✅ Budget berhasil dibuat."

            nominal_rupiah = f"Rp{nominal:,}".replace(",", ".")
            await update.message.reply_text(
                f"{status}\n\n"
                f"🏷️ Kategori: {kategori}\n"
                f"📅 Periode Mulai: {awal_periode.strftime('%d/%m/%Y')}\n"
                f"💰 Budget: {nominal_rupiah}"
            )
            return

        # LIHAT BUDGET
        response = supabase.table("budget").select("*").eq("bulan", bulan_str).execute()
        budget_data = response.data

        if not budget_data:
            await update.message.reply_text(
                "💰 BELUM ADA BUDGET PERIODE INI\n\n"
                f"Periode saat ini: {awal_periode.strftime('%d/%m/%Y')} - {akhir_periode.strftime('%d/%m/%Y')}\n\n"
                "Buat budget dengan format:\n/budget Makan 900000"
            )
            return

        transaksi_response = supabase.table("transaksi").select("kategori, nominal, jenis, tanggal").execute()
        pemakaian = {}

        for transaksi in transaksi_response.data:
            jenis = transaksi.get("jenis", "")
            kategori = transaksi.get("kategori", "")
            tanggal = transaksi.get("tanggal")

            if jenis.lower() != "pengeluaran" or not tanggal:
                continue

            try:
                tanggal_dt = datetime.fromisoformat(tanggal.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            if not (awal_periode <= tanggal_dt <= akhir_periode):
                continue

            try:
                nominal_transaksi = int(transaksi.get("nominal", 0))
            except (ValueError, TypeError):
                nominal_transaksi = 0

            pemakaian[kategori] = pemakaian.get(kategori, 0) + nominal_transaksi

        def rupiah(angka):
            return f"Rp{angka:,}".replace(",", ".")

        pesan = f"💰 BUDGET PERIODE ({awal_periode.strftime('%d/%m')} - {akhir_periode.strftime('%d/%m/%Y')})\n\n"

        for item in budget_data:
            kategori = item.get("kategori", "-")
            try:
                budget_nominal = int(item.get("nominal", 0))
            except (ValueError, TypeError):
                budget_nominal = 0

            terpakai = pemakaian.get(kategori, 0)
            sisa = budget_nominal - terpakai
            persen = (terpakai / budget_nominal * 100) if budget_nominal > 0 else 0

            if sisa < 0:
                status = f"🚨 MELEBIHI {rupiah(abs(sisa))}"
            elif persen >= 80:
                status = "⚠️ Mendekati batas"
            else:
                status = "🟢 Aman"

            pesan += (
                f"🏷️ {kategori}\n"
                f"Budget: {rupiah(budget_nominal)}\n"
                f"Terpakai: {rupiah(terpakai)}\n"
                f"Sisa: {rupiah(sisa)}\n"
                f"Pemakaian: {persen:.0f}%\n"
                f"Status: {status}\n"
                f"────────────────\n"
            )

        await update.message.reply_text(pesan)

    except Exception as e:
        print("ERROR BUDGET:", e)
        await update.message.reply_text("❌ Gagal memproses budget.")


# ==========================================
# CEK PERINGATAN BUDGET (Siklus Tgl 11)
# ==========================================

async def cek_budget_setelah_transaksi(kategori: str, jenis: str):
    try:
        if jenis.lower() != "pengeluaran":
            return None

        awal_periode, akhir_periode = get_periode_berjalan()
        bulan_str = str(awal_periode.date())

        budget_response = supabase.table("budget").select("kategori, nominal").eq("bulan", bulan_str).execute()
        budget_data = budget_response.data

        budget_item = None
        for item in budget_data:
            if str(item.get("kategori", "")).strip().lower() == kategori.strip().lower():
                budget_item = item
                break

        if not budget_item:
            return None

        budget_nominal = int(budget_item.get("nominal", 0))

        transaksi_response = supabase.table("transaksi").select("kategori, nominal, jenis, tanggal").eq("jenis", "Pengeluaran").execute()
        terpakai = 0

        for transaksi in transaksi_response.data:
            if str(transaksi.get("kategori", "")).strip().lower() != kategori.strip().lower():
                continue

            tanggal = transaksi.get("tanggal")
            if not tanggal:
                continue

            try:
                tanggal_dt = datetime.fromisoformat(tanggal.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            if awal_periode <= tanggal_dt <= akhir_periode:
                terpakai += int(transaksi.get("nominal", 0))

        if budget_nominal <= 0:
            return None

        persen = (terpakai / budget_nominal) * 100
        sisa = budget_nominal - terpakai

        def rupiah(angka):
            return f"Rp{abs(int(angka)):,}".replace(",", ".")

        if terpakai > budget_nominal:
            return (
                f"\n\n🚨 PERINGATAN BUDGET\n"
                f"🏷️ {kategori}\n"
                f"💰 Budget: {rupiah(budget_nominal)}\n"
                f"💸 Terpakai: {rupiah(terpakai)}\n"
                f"🔴 Kelebihan: {rupiah(sisa)}\n"
                f"📊 Pemakaian: {persen:.0f}%\n"
                f"🚨 Budget periode ini sudah terlewati."
            )

        if persen >= 80:
            return (
                f"\n\n⚠️ PERINGATAN BUDGET\n"
                f"🏷️ {kategori}\n"
                f"💰 Budget: {rupiah(budget_nominal)}\n"
                f"💸 Terpakai: {rupiah(terpakai)}\n"
                f"🟢 Sisa: {rupiah(sisa)}\n"
                f"📊 Pemakaian: {persen:.0f}%\n"
                f"⚠️ Budget hampir habis."
            )

        return None

    except Exception as e:
        print("ERROR CEK BUDGET:", repr(e))
        return None


# ==========================================
# LAPORAN BULANAN PRO (Siklus Tgl 11)
# ==========================================

async def laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        awal_periode, akhir_periode = get_periode_berjalan()

        def rupiah(angka):
            angka = int(angka)
            return f"-Rp{abs(angka):,}".replace(",", ".") if angka < 0 else f"Rp{angka:,}".replace(",", ".")

        transaksi_response = supabase.table("transaksi").select("id, jenis, kategori, nominal, tanggal").execute()
        data = transaksi_response.data

        pemasukan = 0
        pengeluaran = 0
        jumlah_transaksi = 0
        kategori_pengeluaran = {}

        for transaksi in data:
            tanggal = transaksi.get("tanggal")
            if not tanggal:
                continue

            try:
                tanggal_dt = datetime.fromisoformat(tanggal.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            if not (awal_periode <= tanggal_dt <= akhir_periode):
                continue

            jumlah_transaksi += 1
            jenis = str(transaksi.get("jenis", "")).strip().lower()
            kategori = str(transaksi.get("kategori", "Lainnya")).strip()

            try:
                nominal = int(transaksi.get("nominal", 0))
            except (ValueError, TypeError):
                nominal = 0

            if jenis == "pemasukan":
                pemasukan += nominal
            elif jenis == "pengeluaran":
                pengeluaran += nominal
                key = kategori.lower()
                if key not in kategori_pengeluaran:
                    kategori_pengeluaran[key] = {"nama": kategori, "nominal": 0}
                kategori_pengeluaran[key]["nominal"] += nominal

        saldo = pemasukan - pengeluaran
        kategori_sorted = sorted(kategori_pengeluaran.values(), key=lambda x: x["nominal"], reverse=True)

        bulan_str = str(awal_periode.date())
        budget_response = supabase.table("budget").select("kategori, nominal").eq("bulan", bulan_str).execute()
        budget_data = budget_response.data

        budget_dict = {}
        for item in budget_data:
            kategori_budget = str(item.get("kategori", "")).strip()
            try:
                nominal_budget = int(item.get("nominal", 0))
            except (ValueError, TypeError):
                nominal_budget = 0
            budget_dict[kategori_budget.lower()] = {"nama": kategori_budget, "nominal": nominal_budget}

        pesan = (
            f"📊 LAPORAN KEUANGAN PERIODE\n"
            f"📅 {awal_periode.strftime('%d/%m/%Y')} - {akhir_periode.strftime('%d/%m/%Y')}\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"📥 PEMASUKAN\n{rupiah(pemasukan)}\n\n"
            f"💸 PENGELUARAN\n{rupiah(pengeluaran)}\n\n"
        )

        pesan += f"💰 SALDO BERSIH\n" + ("🟢 " if saldo > 0 else ("🔴 " if saldo < 0 else "🟡 ")) + f"{rupiah(saldo)}\n\n"
        pesan += f"📋 TRANSAKSI: {jumlah_transaksi} transaksi\n\n"

        if kategori_sorted:
            pesan += "🏷️ PENGELUARAN PER KATEGORI\n\n"
            for item in kategori_sorted:
                nama = item["nama"]
                nominal = item["nominal"]
                persen = (nominal / pengeluaran * 100) if pengeluaran > 0 else 0
                pesan += f"• {nama}: {rupiah(nominal)} ({persen:.0f}%)\n"
            pesan += "\n"
        else:
            pesan += "🏷️ PENGELUARAN PER KATEGORI\n\nBelum ada pengeluaran.\n\n"

        if kategori_sorted:
            terbesar = kategori_sorted[0]
            pesan += f"🏆 PENGELUARAN TERBESAR\n{terbesar['nama']}: {rupiah(terbesar['nominal'])}\n\n"

        if budget_dict:
            pesan += "💳 STATUS BUDGET PERIODE INI\n\n"
            semua_kategori = set(list(budget_dict.keys()) + list(kategori_pengeluaran.keys()))

            for key in sorted(semua_kategori):
                nama = key
                budget_nominal = 0
                terpakai = 0

                if key in budget_dict:
                    nama = budget_dict[key]["nama"]
                    budget_nominal = budget_dict[key]["nominal"]
                if key in kategori_pengeluaran:
                    nama = kategori_pengeluaran[key]["nama"]
                    terpakai = kategori_pengeluaran[key]["nominal"]

                if budget_nominal <= 0:
                    pesan += f"• {nama}\n  Terpakai: {rupiah(terpakai)}\n  ⚪ Belum ada budget\n\n"
                    continue

                sisa = budget_nominal - terpakai
                persen_budget = (terpakai / budget_nominal) * 100

                status = f"🚨 MELEBIHI {rupiah(abs(sisa))}" if terpakai > budget_nominal else ("⚠️ MENDEKATI BATAS" if persen_budget >= 80 else "🟢 AMAN")

                pesan += (
                    f"• {nama}\n"
                    f"  Budget: {rupiah(budget_nominal)}\n"
                    f"  Terpakai: {rupiah(terpakai)}\n"
                    f"  Sisa: {rupiah(sisa)}\n"
                    f"  Pemakaian: {persen_budget:.0f}%\n"
                    f"  Status: {status}\n\n"
                )
        else:
            pesan += "💳 STATUS BUDGET\n\n⚪ Belum ada budget periode ini.\n\n"

        pesan += "━━━━━━━━━━━━━━━━\n"
        if saldo > 0:
            pesan += "🟢 KONDISI KEUANGAN: Keuangan periode ini SURPLUS."
        elif saldo < 0:
            pesan += "🔴 KONDISI KEUANGAN: Pengeluaran lebih besar dari pemasukan."
        else:
            pesan += "🟡 KONDISI KEUANGAN: Pemasukan dan pengeluaran seimbang."

        await update.message.reply_text(pesan)

    except Exception as e:
        print("ERROR LAPORAN:", repr(e))
        await update.message.reply_text("❌ Gagal membuat laporan bulanan.")


# ==========================================
# STATISTIK KEUANGAN (Siklus Tgl 11)
# ==========================================

async def statistik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        awal_periode, akhir_periode = get_periode_berjalan()

        response = supabase.table("transaksi").select("id, jenis, kategori, nominal, tanggal").execute()
        data = response.data

        pemasukan = 0
        pengeluaran = 0
        jumlah_pemasukan = 0
        jumlah_pengeluaran = 0
        kategori_pengeluaran = {}

        for transaksi in data:
            tanggal = transaksi.get("tanggal")
            if not tanggal:
                continue

            try:
                tanggal_dt = datetime.fromisoformat(tanggal.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            if not (awal_periode <= tanggal_dt <= akhir_periode):
                continue

            jenis = str(transaksi.get("jenis", "")).strip().lower()
            kategori = str(transaksi.get("kategori", "Lainnya")).strip()

            try:
                nominal = int(transaksi.get("nominal", 0))
            except (ValueError, TypeError):
                nominal = 0

            if jenis == "pemasukan":
                pemasukan += nominal
                jumlah_pemasukan += 1
            elif jenis == "pengeluaran":
                pengeluaran += nominal
                jumlah_pengeluaran += 1
                kategori_key = kategori.lower()
                if kategori_key not in kategori_pengeluaran:
                    kategori_pengeluaran[kategori_key] = {"nama": kategori, "nominal": 0}
                kategori_pengeluaran[kategori_key]["nominal"] += nominal

        total_transaksi = jumlah_pemasukan + jumlah_pengeluaran
        rata_pengeluaran = (pengeluaran / jumlah_pengeluaran) if jumlah_pengeluaran > 0 else 0

        def rupiah(angka):
            return f"Rp{int(angka):,}".replace(",", ".")

        kategori_sorted = sorted(kategori_pengeluaran.values(), key=lambda x: x["nominal"], reverse=True)

        pesan = (
            f"📈 STATISTIK KEUANGAN\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"📅 Periode: {awal_periode.strftime('%d/%m/%Y')} - {akhir_periode.strftime('%d/%m/%Y')}\n\n"
            f"💰 TOTAL PEMASUKAN\n{rupiah(pemasukan)}\n\n"
            f"💸 TOTAL PENGELUARAN\n{rupiah(pengeluaran)}\n\n"
            f"📊 RATA-RATA PENGELUARAN\n{rupiah(rata_pengeluaran)} / transaksi\n\n"
            f"📋 TRANSAKSI\n"
            f"📥 Pemasukan   : {jumlah_pemasukan}\n"
            f"💸 Pengeluaran : {jumlah_pengeluaran}\n"
            f"📊 Total       : {total_transaksi}\n\n"
        )

        if kategori_sorted:
            terbesar = kategori_sorted[0]
            persen_terbesar = (terbesar["nominal"] / pengeluaran * 100) if pengeluaran > 0 else 0
            pesan += f"🏆 KATEGORI TERBOROS\n🏷️ {terbesar['nama']}\n{rupiah(terbesar['nominal'])} ({persen_terbesar:.0f}%)\n\n"

        pesan += "⚠️ ANALISIS\n"
        if total_transaksi == 0:
            pesan += "Belum ada transaksi pada periode ini."
        elif pengeluaran > pemasukan:
            pesan += "Pengeluaran kamu lebih besar daripada pemasukan periode ini.\n\n💡 Perhatikan pengeluaran pada kategori terbesar."
        elif pengeluaran == pemasukan:
            pesan += "Pemasukan dan pengeluaran sama.\n\n💡 Usahakan mulai menyisihkan tabungan."
        else:
            pesan += "Kondisi keuangan periode ini masih positif.\n\n💡 Pertahankan pengeluaran agar tetap aman."

        pesan += "\n━━━━━━━━━━━━━━━━"
        await update.message.reply_text(pesan)

    except Exception as e:
        print("ERROR STATISTIK:", e)
        await update.message.reply_text("❌ Gagal membuat statistik.")


# ==========================================
# KATEGORI PENGELUARAN (Siklus Tgl 11)
# ==========================================

async def kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        awal_periode, akhir_periode = get_periode_berjalan()

        kategori_filter = None
        if context.args:
            kategori_filter = " ".join(context.args).strip().lower()

        response = supabase.table("transaksi").select("id, jenis, kategori, nominal, tanggal").eq("jenis", "Pengeluaran").execute()
        data = response.data
        kategori_data = {}

        for transaksi in data:
            tanggal = transaksi.get("tanggal")
            if not tanggal:
                continue

            try:
                tanggal_dt = datetime.fromisoformat(tanggal.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            if not (awal_periode <= tanggal_dt <= akhir_periode):
                continue

            nama_kategori = str(transaksi.get("kategori", "Lainnya")).strip()

            if kategori_filter and nama_kategori.lower() != kategori_filter:
                continue

            try:
                nominal = int(transaksi.get("nominal", 0))
            except (ValueError, TypeError):
                nominal = 0

            key = nama_kategori.lower()
            if key not in kategori_data:
                kategori_data[key] = {"nama": nama_kategori, "nominal": 0, "jumlah": 0}

            kategori_data[key]["nominal"] += nominal
            kategori_data[key]["jumlah"] += 1

        if not kategori_data:
            pesan_kosong = f"📊 KATEGORI {kategori_filter.upper()}\n\n" if kategori_filter else "📊 PENGELUARAN PER KATEGORI\n\n"
            pesan_kosong += f"📅 {awal_periode.strftime('%d/%m/%Y')} - {akhir_periode.strftime('%d/%m/%Y')}\n\n⚪ Belum ada pengeluaran."
            await update.message.reply_text(pesan_kosong)
            return

        kategori_sorted = sorted(kategori_data.values(), key=lambda x: x["nominal"], reverse=True)
        total_pengeluaran = sum(item["nominal"] for item in kategori_sorted)

        def rupiah(angka):
            return f"Rp{int(angka):,}".replace(",", ".")

        pesan = f"📊 DETAIL KATEGORI\n━━━━━━━━━━━━━━━━\n\n" if kategori_filter else f"📊 PENGELUARAN PER KATEGORI\n━━━━━━━━━━━━━━━━\n\n"
        pesan += f"📅 {awal_periode.strftime('%d/%m/%Y')} - {akhir_periode.strftime('%d/%m/%Y')}\n\n"

        for item in kategori_sorted:
            nama = item["nama"]
            nominal = item["nominal"]
            jumlah = item["jumlah"]
            persen = (nominal / total_pengeluaran * 100) if total_pengeluaran > 0 else 0

            jumlah_bar = max(1, int(persen / 5)) if persen > 0 else 0
            bar = "█" * jumlah_bar

            pesan += (
                f"🏷️ {nama}\n"
                f"💸 {rupiah(nominal)}\n"
                f"{bar} {persen:.0f}%\n"
                f"📋 {jumlah} transaksi\n\n"
            )

        pesan += f"━━━━━━━━━━━━━━━━\n💰 TOTAL PENGELUARAN\n{rupiah(total_pengeluaran)}\n\n"
        if not kategori_filter:
            terbesar = kategori_sorted[0]
            pesan += f"🏆 TERBESAR\n{terbesar['nama']} — {rupiah(terbesar['nominal'])}\n\n"

        pesan += f"📌 JUMLAH KATEGORI\n{len(kategori_sorted)} kategori"
        await update.message.reply_text(pesan)

    except Exception as e:
        print("ERROR KATEGORI:", e)
        await update.message.reply_text("❌ Gagal mengambil data kategori.")


# ==========================================
# TAMBAH TARGET KEUANGAN
# ==========================================

async def target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Format salah.\n\n"
                "Gunakan:\n/target [Nama Target] [Nominal Target] [Setoran Bulanan]\n\n"
                "Contoh:\n/target Laptop 6000000 500000"
            )
            return

        nama_target = context.args[0].strip()

        try:
            target_nominal = int(context.args[1])
        except ValueError:
            await update.message.reply_text("❌ Nominal target harus angka.")
            return

        setoran_bulanan = int(context.args[2]) if len(context.args) >= 3 else 0

        if target_nominal <= 0 or setoran_bulanan < 0:
            await update.message.reply_text("❌ Nominal tidak valid.")
            return

        existing = supabase.table("target_keuangan").select("id, nama_target").ilike("nama_target", nama_target).execute()
        if existing.data:
            await update.message.reply_text(f"⚠️ Target '{nama_target}' sudah ada.")
            return

        response = supabase.table("target_keuangan").insert({
            "nama_target": nama_target,
            "target_nominal": target_nominal,
            "terkumpul": 0,
            "setoran_bulanan": setoran_bulanan
        }).execute()

        if not response.data:
            await update.message.reply_text("❌ Target gagal disimpan.")
            return

        target_id = response.data[0].get("id")

        def rupiah(angka):
            return f"Rp{int(angka):,}".replace(",", ".")

        await update.message.reply_text(
            f"🎯 TARGET BERHASIL DIBUAT\n━━━━━━━━━━━━━━━━\n\n"
            f"🆔 ID: {target_id}\n"
            f"🏷️ Target: {nama_target}\n"
            f"💰 Target Nominal: {rupiah(target_nominal)}\n"
            f"💵 Terkumpul: {rupiah(0)}\n"
            f"📥 Setoran/Bulan: {rupiah(setoran_bulanan)}\n\n"
            f"📊 Progress: 0%\n\n"
            f"💡 Gunakan /setor nanti untuk menambahkan uang ke target."
        )

    except Exception as e:
        print("ERROR TARGET:", e)
        await update.message.reply_text("❌ Gagal membuat target.")


# ==========================================
# SETOR KE TARGET KEUANGAN
# ==========================================

async def setor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 2:
            await update.message.reply_text("❌ Format salah.\n\nGunakan:\n/setor [ID Target] [Nominal]")
            return

        try:
            target_id = int(context.args[0])
            nominal_setoran = int(context.args[1])
        except ValueError:
            await update.message.reply_text("❌ ID dan Nominal harus angka.")
            return

        if nominal_setoran <= 0:
            await update.message.reply_text("❌ Setoran harus > 0.")
            return

        response = supabase.table("target_keuangan").select("*").eq("id", target_id).execute()
        if not response.data:
            await update.message.reply_text(f"❌ Target ID {target_id} tidak ditemukan.")
            return

        target_data = response.data[0]
        nama_target = target_data.get("nama_target", "-")
        target_nominal = int(target_data.get("target_nominal", 0))
        terkumpul_lama = int(target_data.get("terkumpul", 0))

        terkumpul_baru = terkumpul_lama + nominal_setoran
        progress = min(100, (terkumpul_baru / target_nominal) * 100)
        kekurangan = max(0, target_nominal - terkumpul_baru)

        supabase.table("target_keuangan").update({"terkumpul": terkumpul_baru}).eq("id", target_id).execute()

        def rupiah(angka):
            return f"Rp{int(angka):,}".replace(",", ".")

        status = "🎉 TARGET TERCAPAI! 🔥" if terkumpul_baru >= target_nominal else ("🔥 Hampir tercapai!" if progress >= 75 else "💪 Progress bagus!")
        bar = "█" * min(10, int(progress / 10)) + "░" * (10 - min(10, int(progress / 10)))

        await update.message.reply_text(
            f"💰 SETORAN BERHASIL\n━━━━━━━━━━━━━━━━\n\n"
            f"🆔 ID Target: {target_id}\n"
            f"🏷️ Target: {nama_target}\n\n"
            f"💵 Setoran: {rupiah(nominal_setoran)}\n"
            f"💰 Terkumpul: {rupiah(terkumpul_baru)}\n"
            f"🎯 Target: {rupiah(target_nominal)}\n"
            f"📉 Kekurangan: {rupiah(kekurangan)}\n\n"
            f"📊 Progress\n{bar} {progress:.0f}%\n\n{status}"
        )

    except Exception as e:
        print("ERROR SETOR:", e)
        await update.message.reply_text("❌ Gagal melakukan setoran.")
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Health check server untuk Render Free Tier
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Financial Farhan Aktif!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Jalankan HTTP server di background thread
threading.Thread(target=run_dummy_server, daemon=True).start()


# ==========================================
# MAIN
# ==========================================

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("riwayat", riwayat))

    app.add_handler(CommandHandler("tambah", tambah))
    app.add_handler(CommandHandler("edit", edit))
    app.add_handler(CommandHandler("saldo", saldo))
    app.add_handler(CommandHandler("rekap", rekap))
    app.add_handler(CommandHandler("budget", budget))
    app.add_handler(CommandHandler("laporan", laporan))
    app.add_handler(CommandHandler("statistik", statistik))
    app.add_handler(CommandHandler("kategori", kategori))
    app.add_handler(CommandHandler("target", target))
    app.add_handler(CommandHandler("setor", setor))
    app.add_handler(CommandHandler("makan", makan))
    app.add_handler(CommandHandler("bensin", bensin))
    app.add_handler(CommandHandler("hapus", hapus))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, konfirmasi_semua))

    print("Finance Bot berjalan (Siklus Tgl 11)...")
    app.run_polling()


if __name__ == "__main__":
    main()