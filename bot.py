import os
from datetime import datetime, timezone
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
# Menyimpan transaksi yang sedang menunggu konfirmasi hapus
pending_delete = {}
pending_edit = {}
# ==========================================
# START
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Halo Farhan 👋\n\n"
        "💰 Finance Bot aktif!\n\n"

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

    # Cek jumlah argument
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

    # ==========================================
    # AMBIL DATA
    # ==========================================

    jenis = context.args[0]
    kategori = context.args[1]

    # ==========================================
    # VALIDASI JENIS
    # ==========================================

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

    # ==========================================
    # NOMINAL
    # ==========================================

    try:

        nominal = int(context.args[2])

    except ValueError:

        await update.message.reply_text(
            "❌ Nominal harus berupa angka.\n\n"
            "Contoh:\n"
            "/tambah Pengeluaran Makan 30000 makan siang"
        )

        return

    # ==========================================
    # VALIDASI NOMINAL
    # ==========================================

    if nominal <= 0:

        await update.message.reply_text(
            "❌ Nominal harus lebih dari 0."
        )

        return

    # ==========================================
    # KETERANGAN
    # ==========================================

    keterangan = " ".join(context.args[3:])

    # ==========================================
    # SIMPAN
    # ==========================================

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

    # ==========================================
    # FORMAT RUPIAH
    # ==========================================

    nominal_rupiah = f"Rp{nominal:,}".replace(",", ".")

    # ==========================================
    # CEK PERINGATAN BUDGET
    # ==========================================

    peringatan_budget = None

    try:
        peringatan_budget = await cek_budget_setelah_transaksi(
            kategori=kategori,
            jenis=jenis
        )

        print("DEBUG BUDGET:", peringatan_budget)

    except Exception as e:
        print("ERROR CEK BUDGET:", e)
    
    # ==========================================
    # RESPONSE
    # ==========================================

    pesan = (
        f"âœ… TRANSAKSI TERCATAT\n\n"
        f"ðŸ†” ID: {transaction_id}\n"
        f"ðŸ“… Tanggal: {tanggal.strftime('%d/%m/%Y %H:%M')}\n"
        f"ðŸ“Œ Jenis: {jenis}\n"
        f"ðŸ·ï¸ Kategori: {kategori}\n"
        f"ðŸ’° Nominal: {nominal_rupiah}\n"
        f"ðŸ“ Keterangan: {keterangan or '-'}"
    )

    if peringatan_budget:
        pesan += "\n\n" + peringatan_budget

    await update.message.reply_text(pesan)


# ==========================================
# COMMAND LAMA: MAKAN
# ==========================================

async def makan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:

        await update.message.reply_text(
            "Format yang benar:\n"
            "/makan 25000 makan siang"
        )

        return

    try:

        nominal = int(context.args[0])

    except ValueError:

        await update.message.reply_text(
            "Nominal harus berupa angka.\n"
            "Contoh: /makan 25000"
        )

        return

    keterangan = " ".join(context.args[1:])

    transaction_id, tanggal = add_transaction(
        jenis="Pengeluaran",
        kategori="Makan",
        nominal=nominal,
        keterangan=keterangan
    )

    nominal_rupiah = f"Rp{nominal:,}".replace(",", ".")

    # ==========================================
    # CEK PERINGATAN BUDGET
    # ==========================================

    peringatan_budget = None

    try:
        peringatan_budget = await cek_budget_setelah_transaksi(
            kategori=kategori,
            jenis=jenis
        )

        print("DEBUG BUDGET:", peringatan_budget)

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

    # Cek kondisi budget
    peringatan_budget = await cek_budget_setelah_transaksi(
        kategori=kategori,
        jenis=jenis
    )
    print("DEBUG BUDGET:", peringatan_budget)

    if peringatan_budget:
        pesan += peringatan_budget

    await update.message.reply_text(pesan)
# ==========================================
# COMMAND LAMA: BENSIN
# ==========================================

async def bensin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:

        await update.message.reply_text(
            "Format yang benar:\n"
            "/bensin 50000 isi bensin"
        )

        return

    try:

        nominal = int(context.args[0])

    except ValueError:

        await update.message.reply_text(
            "Nominal harus berupa angka.\n"
            "Contoh: /bensin 50000"
        )

        return

    keterangan = " ".join(context.args[1:])

    transaction_id, tanggal = add_transaction(
        jenis="Pengeluaran",
        kategori="Bensin",
        nominal=nominal,
        keterangan=keterangan
    )

    nominal_rupiah = f"Rp{nominal:,}".replace(",", ".")
    
    # ==========================================
    # CEK BUDGET
    # ==========================================

    peringatan_budget = await cek_budget_setelah_transaksi(
        kategori=kategori,
        jenis=jenis
    )

    print("DEBUG BUDGET:", peringatan_budget)

    pesan = (
        f"âœ… TRANSAKSI TERCATAT\n\n"

        f"ðŸ†” ID: {transaction_id}\n"
        f"ðŸ“… Tanggal: {tanggal.strftime('%d/%m/%Y %H:%M')}\n"
        f"ðŸ“Œ Jenis: {jenis}\n"
        f"ðŸ·ï¸ Kategori: {kategori}\n"
        f"ðŸ’° Nominal: {nominal_rupiah}\n"
        f"ðŸ“ Keterangan: {keterangan or '-'}"
    )

    if peringatan_budget:
        pesan += peringatan_budget

    await update.message.reply_text(pesan)

# ==========================================
# RIWAYAT TRANSAKSI
# ==========================================

async def riwayat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        # Ambil jumlah transaksi
        limit = 10

        if context.args:

            try:
                limit = int(context.args[0])

            except ValueError:

                await update.message.reply_text(
                    "❌ Jumlah transaksi harus berupa angka.\n\n"
                    "Contoh:\n"
                    "/riwayat\n"
                    "/riwayat 20"
                )

                return

        # Batasi agar tidak terlalu banyak
        if limit < 1:
            limit = 1

        if limit > 50:
            limit = 50

        # Ambil data dari Supabase
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

            await update.message.reply_text(
                "📋 Belum ada transaksi."
            )

            return

        pesan = "📋 RIWAYAT TRANSAKSI\n\n"

        for transaksi in data:

            transaction_id = transaksi.get("id", "-")
            jenis = transaksi.get("jenis", "-")
            kategori = transaksi.get("kategori", "-")
            nominal = transaksi.get("nominal", 0)
            keterangan = transaksi.get("keterangan", "-")
            tanggal = transaksi.get("tanggal", "-")

            # Format nominal
            try:
                nominal_rupiah = (
                    f"Rp{int(nominal):,}"
                    .replace(",", ".")
                )

            except (ValueError, TypeError):

                nominal_rupiah = f"Rp{nominal}"

            # Simbol pemasukan/pengeluaran
            if jenis.lower() == "pemasukan":

                simbol = "📥"

            else:

                simbol = "💸"

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

        await update.message.reply_text(
            "❌ Gagal mengambil riwayat transaksi.\n\n"
            "Cek PowerShell untuk melihat error."
        )
# ==========================================
# HAPUS TRANSAKSI
# ==========================================

async def hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:

        await update.message.reply_text(
            "❌ Masukkan ID transaksi yang ingin dihapus.\n\n"
            "Contoh:\n"
            "/hapus 17"
        )

        return

    try:

        transaction_id = int(context.args[0])

    except ValueError:

        await update.message.reply_text(
            "❌ ID transaksi harus berupa angka.\n\n"
            "Contoh:\n"
            "/hapus 17"
        )

        return

    try:

        # Cari transaksi
        response = (
            supabase
            .table("transaksi")
            .select("*")
            .eq("id", transaction_id)
            .execute()
        )

        data = response.data

        if not data:

            await update.message.reply_text(
                f"❌ Transaksi dengan ID #{transaction_id} tidak ditemukan."
            )

            return

        transaksi = data[0]

        jenis = transaksi.get("jenis", "-")
        kategori = transaksi.get("kategori", "-")
        nominal = transaksi.get("nominal", 0)
        keterangan = transaksi.get("keterangan", "-")
        tanggal = transaksi.get("tanggal", "-")

        nominal_rupiah = (
            f"Rp{int(nominal):,}"
            .replace(",", ".")
        )

        # Simpan ID yang menunggu konfirmasi
        user_id = update.effective_user.id

        pending_delete[user_id] = transaction_id

        await update.message.reply_text(

            f"⚠️ KONFIRMASI HAPUS TRANSAKSI\n\n"

            f"🆔 ID: #{transaction_id}\n"
            f"📅 Tanggal: {tanggal}\n"
            f"📌 Jenis: {jenis}\n"
            f"🏷️ Kategori: {kategori}\n"
            f"💰 Nominal: {nominal_rupiah}\n"
            f"📝 Keterangan: {keterangan}\n\n"

            f"Yakin ingin menghapus transaksi ini?\n\n"

            f"Ketik:\n"
            f"YA → hapus transaksi\n"
            f"BATAL → batalkan"
        )

    except Exception as e:

        print("ERROR HAPUS:", e)

        await update.message.reply_text(
            "❌ Gagal mencari transaksi.\n\n"
            "Cek PowerShell untuk melihat error."
        )
# ==========================================
# KONFIRMASI HAPUS
# ==========================================

async def konfirmasi_hapus(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    if user_id not in pending_delete:

        return

    jawaban = update.message.text.strip().lower()

    # ==========================================
    # BATAL
    # ==========================================

    if jawaban == "batal":

        del pending_delete[user_id]

        await update.message.reply_text(
            "❌ Penghapusan dibatalkan.\n\n"
            "Transaksi tetap aman."
        )

        return

    # ==========================================
    # BUKAN YA
    # ==========================================

    if jawaban != "ya":

        await update.message.reply_text(
            "⚠️ Ketik YA untuk menghapus atau BATAL untuk membatalkan."
        )

        return

    transaction_id = pending_delete[user_id]

    try:

        # Hapus dari Supabase
        (
            supabase
            .table("transaksi")
            .delete()
            .eq("id", transaction_id)
            .execute()
        )

        # Hapus status pending
        del pending_delete[user_id]

        await update.message.reply_text(
            f"✅ TRANSAKSI BERHASIL DIHAPUS\n\n"
            f"🆔 ID: #{transaction_id}\n\n"
            f"Transaksi sudah dihapus dari database.\n"
            f"Excel akan mengikuti saat sync dijalankan."
        )

    except Exception as e:

        print("ERROR KONFIRMASI HAPUS:", e)

        await update.message.reply_text(
            "❌ Gagal menghapus transaksi.\n\n"
            "Cek PowerShell untuk melihat error."
        )
# ==========================================
# EDIT TRANSAKSI
# ==========================================

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 3:

        await update.message.reply_text(
            "❌ Format salah.\n\n"
            "Gunakan:\n"
            "/edit [ID] [Kategori] [Nominal] [Keterangan]\n\n"
            "Contoh:\n"
            "/edit 25 Makan 35000 makan malam"
        )

        return

    # ==========================================
    # ID TRANSAKSI
    # ==========================================

    try:

        transaction_id = int(context.args[0])

    except ValueError:

        await update.message.reply_text(
            "❌ ID transaksi harus berupa angka.\n\n"
            "Contoh:\n"
            "/edit 25 Makan 35000 makan malam"
        )

        return

    kategori_baru = context.args[1]

    # ==========================================
    # NOMINAL BARU
    # ==========================================

    try:

        nominal_baru = int(context.args[2])

    except ValueError:

        await update.message.reply_text(
            "❌ Nominal harus berupa angka.\n\n"
            "Contoh:\n"
            "/edit 25 Makan 35000 makan malam"
        )

        return

    if nominal_baru <= 0:

        await update.message.reply_text(
            "❌ Nominal harus lebih dari 0."
        )

        return

    # ==========================================
    # KETERANGAN BARU
    # ==========================================

    keterangan_baru = " ".join(context.args[3:])

    try:

        # Cari transaksi lama
        response = (
            supabase
            .table("transaksi")
            .select("*")
            .eq("id", transaction_id)
            .execute()
        )

        data = response.data

        if not data:

            await update.message.reply_text(
                f"❌ Transaksi dengan ID #{transaction_id} tidak ditemukan."
            )

            return

        transaksi = data[0]

        jenis_lama = transaksi.get("jenis", "-")
        kategori_lama = transaksi.get("kategori", "-")
        nominal_lama = transaksi.get("nominal", 0)
        keterangan_lama = transaksi.get("keterangan", "-")
        tanggal = transaksi.get("tanggal", "-")

        nominal_lama_rupiah = (
            f"Rp{int(nominal_lama):,}"
            .replace(",", ".")
        )

        nominal_baru_rupiah = (
            f"Rp{nominal_baru:,}"
            .replace(",", ".")
        )

        user_id = update.effective_user.id

        # Simpan perubahan sementara
        pending_edit[user_id] = {
            "id": transaction_id,
            "kategori": kategori_baru,
            "nominal": nominal_baru,
            "keterangan": keterangan_baru
        }

        await update.message.reply_text(

            f"✏️ KONFIRMASI EDIT TRANSAKSI\n\n"

            f"🆔 ID: #{transaction_id}\n"
            f"📅 Tanggal: {tanggal}\n"
            f"📌 Jenis: {jenis_lama}\n\n"

            f"DATA LAMA\n"
            f"🏷️ Kategori: {kategori_lama}\n"
            f"💰 Nominal: {nominal_lama_rupiah}\n"
            f"📝 Keterangan: {keterangan_lama}\n\n"

            f"DATA BARU\n"
            f"🏷️ Kategori: {kategori_baru}\n"
            f"💰 Nominal: {nominal_baru_rupiah}\n"
            f"📝 Keterangan: {keterangan_baru or '-'}\n\n"

            f"Yakin ingin menyimpan perubahan?\n\n"
            f"Ketik:\n"
            f"YA → simpan perubahan\n"
            f"BATAL → batalkan"
        )

    except Exception as e:

        print("ERROR EDIT:", e)

        await update.message.reply_text(
            "❌ Gagal mengambil transaksi.\n\n"
            "Cek PowerShell untuk melihat error."
        )
# ==========================================
# KONFIRMASI EDIT
# ==========================================

async def konfirmasi_edit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    if user_id not in pending_edit:

        return

    jawaban = update.message.text.strip().lower()

    # ==========================================
    # BATAL
    # ==========================================

    if jawaban == "batal":

        del pending_edit[user_id]

        await update.message.reply_text(
            "❌ Perubahan dibatalkan.\n\n"
            "Data transaksi tetap seperti semula."
        )

        return

    # ==========================================
    # BUKAN YA
    # ==========================================

    if jawaban != "ya":

        await update.message.reply_text(
            "⚠️ Ketik YA untuk menyimpan perubahan "
            "atau BATAL untuk membatalkan."
        )

        return

    perubahan = pending_edit[user_id]

    transaction_id = perubahan["id"]

    try:

        # UPDATE SUPABASE
        (
            supabase
            .table("transaksi")
            .update({
                "kategori": perubahan["kategori"],
                "nominal": perubahan["nominal"],
                "keterangan": perubahan["keterangan"]
            })
            .eq("id", transaction_id)
            .execute()
        )

        del pending_edit[user_id]

        nominal_rupiah = (
            f"Rp{int(perubahan['nominal']):,}"
            .replace(",", ".")
        )

        await update.message.reply_text(

            f"✅ TRANSAKSI BERHASIL DIUPDATE\n\n"

            f"🆔 ID: #{transaction_id}\n"
            f"🏷️ Kategori: {perubahan['kategori']}\n"
            f"💰 Nominal: {nominal_rupiah}\n"
            f"📝 Keterangan: "
            f"{perubahan['keterangan'] or '-'}\n\n"

            f"Database Supabase sudah diperbarui.\n"
            f"Excel akan mengikuti saat sync dijalankan."
        )

    except Exception as e:

        print("ERROR KONFIRMASI EDIT:", e)

        await update.message.reply_text(
            "❌ Gagal mengupdate transaksi.\n\n"
            "Cek PowerShell untuk melihat error."
        )

# ==========================================
# KONFIRMASI SEMUA
# ==========================================

async def konfirmasi_semua(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    # Kalau sedang proses hapus
    if user_id in pending_delete:

        await konfirmasi_hapus(update, context)
        return

    # Kalau sedang proses edit
    if user_id in pending_edit:

        await konfirmasi_edit(update, context)
        return
# ==========================================
# CEK SALDO
# ==========================================

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        # Ambil seluruh transaksi
        response = (
            supabase
            .table("transaksi")
            .select("jenis, nominal")
            .execute()
        )

        data = response.data

        total_pemasukan = 0
        total_pengeluaran = 0

        for transaksi in data:

            jenis = transaksi.get("jenis", "")
            nominal = transaksi.get("nominal", 0)

            try:
                nominal = int(nominal)
            except (ValueError, TypeError):
                nominal = 0

            if jenis.lower() == "pemasukan":

                total_pemasukan += nominal

            elif jenis.lower() == "pengeluaran":

                total_pengeluaran += nominal

        saldo_sekarang = total_pemasukan - total_pengeluaran

        # Format Rupiah
        pemasukan_rupiah = (
            f"Rp{total_pemasukan:,}"
            .replace(",", ".")
        )

        pengeluaran_rupiah = (
            f"Rp{total_pengeluaran:,}"
            .replace(",", ".")
        )

        saldo_rupiah = (
            f"Rp{saldo_sekarang:,}"
            .replace(",", ".")
        )

        # Tentukan status saldo
        if saldo_sekarang > 0:

            status = "🟢 Saldo masih positif"

        elif saldo_sekarang < 0:

            status = "🔴 Pengeluaran lebih besar dari pemasukan"

        else:

            status = "🟡 Saldo saat ini Rp0"

        await update.message.reply_text(

            f"💰 SALDO KEUANGAN\n\n"

            f"📥 Total Pemasukan\n"
            f"{pemasukan_rupiah}\n\n"

            f"📤 Total Pengeluaran\n"
            f"{pengeluaran_rupiah}\n\n"

            f"━━━━━━━━━━━━━━━━\n"

            f"💵 SALDO\n"
            f"{saldo_rupiah}\n\n"

            f"{status}"

        )

    except Exception as e:

        print("ERROR SALDO:", e)

        await update.message.reply_text(
            "❌ Gagal menghitung saldo.\n\n"
            "Cek PowerShell untuk melihat error."
        )
# ==========================================
# REKAP KEUANGAN
# ==========================================

async def rekap(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        # Bulan berjalan
        sekarang = datetime.now()

        bulan = sekarang.month
        tahun = sekarang.year

        nama_bulan = [
            "Januari",
            "Februari",
            "Maret",
            "April",
            "Mei",
            "Juni",
            "Juli",
            "Agustus",
            "September",
            "Oktober",
            "November",
            "Desember"
        ]

        nama_bulan_sekarang = nama_bulan[bulan - 1]

        # Ambil transaksi
        response = (
            supabase
            .table("transaksi")
            .select("*")
            .execute()
        )

        data = response.data

        # ==========================================
        # VARIABEL PERHITUNGAN
        # ==========================================

        total_pemasukan = 0
        total_pengeluaran = 0

        kategori_pengeluaran = {}
        kategori_pemasukan = {}

        # ==========================================
        # PROSES TRANSAKSI
        # ==========================================

        for transaksi in data:

            tanggal = transaksi.get("tanggal")

            if not tanggal:
                continue

            try:

                tanggal_dt = datetime.fromisoformat(
                    tanggal.replace("Z", "+00:00")
                )

            except (ValueError, TypeError):

                continue

            # Hanya bulan dan tahun sekarang
            if (
                tanggal_dt.month != bulan
                or tanggal_dt.year != tahun
            ):
                continue

            jenis = transaksi.get("jenis", "")
            kategori = transaksi.get("kategori", "Lainnya")
            nominal = transaksi.get("nominal", 0)

            try:

                nominal = int(nominal)

            except (ValueError, TypeError):

                nominal = 0

            # ==========================================
            # PEMASUKAN
            # ==========================================

            if jenis.lower() == "pemasukan":

                total_pemasukan += nominal

                kategori_pemasukan[kategori] = (
                    kategori_pemasukan.get(kategori, 0)
                    + nominal
                )

            # ==========================================
            # PENGELUARAN
            # ==========================================

            elif jenis.lower() == "pengeluaran":

                total_pengeluaran += nominal

                kategori_pengeluaran[kategori] = (
                    kategori_pengeluaran.get(kategori, 0)
                    + nominal
                )

        # ==========================================
        # FORMAT RUPIAH
        # ==========================================

        def rupiah(angka):

            return (
                f"Rp{angka:,}"
                .replace(",", ".")
            )

        # ==========================================
        # BUAT PESAN
        # ==========================================

        pesan = (
            f"📊 REKAP KEUANGAN\n"
            f"{nama_bulan_sekarang.upper()} {tahun}\n\n"
        )

        # ==========================================
        # PEMASUKAN
        # ==========================================

        pesan += "📥 PEMASUKAN\n"

        if kategori_pemasukan:

            for kategori, nominal in sorted(
                kategori_pemasukan.items(),
                key=lambda x: x[1],
                reverse=True
            ):

                pesan += (
                    f"💰 {kategori}: "
                    f"{rupiah(nominal)}\n"
                )

        else:

            pesan += "Tidak ada pemasukan.\n"

        # ==========================================
        # PENGELUARAN
        # ==========================================

        pesan += "\n📤 PENGELUARAN\n"

        if kategori_pengeluaran:

            for kategori, nominal in sorted(
                kategori_pengeluaran.items(),
                key=lambda x: x[1],
                reverse=True
            ):

                pesan += (
                    f"💸 {kategori}: "
                    f"{rupiah(nominal)}\n"
                )

        else:

            pesan += "Tidak ada pengeluaran.\n"

        # ==========================================
        # TOTAL
        # ==========================================

        saldo_bulan = (
            total_pemasukan
            - total_pengeluaran
        )

        pesan += (
            "\n━━━━━━━━━━━━━━━━\n"
            f"📥 Total Masuk: "
            f"{rupiah(total_pemasukan)}\n"
            f"📤 Total Keluar: "
            f"{rupiah(total_pengeluaran)}\n"
            f"💵 Sisa: "
            f"{rupiah(saldo_bulan)}"
        )

        await update.message.reply_text(pesan)

    except Exception as e:

        print("ERROR REKAP:", e)

        await update.message.reply_text(
            "❌ Gagal membuat rekap.\n\n"
            "Cek PowerShell untuk melihat error."
        )
# ==========================================
# HELP
# ==========================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🤖 FINANCE BOT FARHAN\n\n"

        "📝 PENCATATAN TRANSAKSI\n"
        "/tambah Pengeluaran Makan 30000 makan siang\n"
        "/tambah Pengeluaran Bensin 50000 isi bensin\n"
        "/tambah Pemasukan Gaji 5000000 gaji DENSO\n\n"

        "📊 INFORMASI KEUANGAN\n"
        "/saldo → cek saldo saat ini\n"
        "/riwayat → lihat 10 transaksi terakhir\n"
        "/riwayat 20 → lihat 20 transaksi terakhir\n"
        "/rekap → rekap keuangan bulan ini\n\n"

        "✏️ KELOLA TRANSAKSI\n"
        "/edit 25 Makan 35000 makan malam\n"
        "/hapus 25 → hapus transaksi ID 25\n\n"

        "📌 COMMAND LAMA\n"
        "/makan 30000 makan siang\n"
        "/bensin 50000 isi bensin\n\n"

        "💡 Tips:\n"
        "Gunakan /tambah untuk semua jenis transaksi."
    )
# ==========================================
# BUDGET
# ==========================================

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        sekarang = datetime.now(timezone.utc)

        # Awal bulan berjalan
        awal_bulan = sekarang.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        bulan = awal_bulan.date()

        # ==========================================
        # MODE TAMBAH / UPDATE BUDGET
        # ==========================================

        if context.args:

            if len(context.args) < 2:

                await update.message.reply_text(
                    "❌ Format salah.\n\n"
                    "Gunakan:\n"
                    "/budget [Kategori] [Nominal]\n\n"
                    "Contoh:\n"
                    "/budget Makan 900000\n"
                    "/budget Bensin 400000"
                )

                return

            kategori = context.args[0]

            try:

                nominal = int(context.args[1])

            except ValueError:

                await update.message.reply_text(
                    "❌ Nominal budget harus berupa angka.\n\n"
                    "Contoh:\n"
                    "/budget Makan 900000"
                )

                return

            if nominal <= 0:

                await update.message.reply_text(
                    "❌ Nominal budget harus lebih dari 0."
                )

                return

            # Cek apakah budget sudah ada
            existing = (
                supabase
                .table("budget")
                .select("*")
                .eq("kategori", kategori)
                .eq("bulan", str(bulan))
                .execute()
            )

            if existing.data:

                # UPDATE
                (
                    supabase
                    .table("budget")
                    .update({
                        "nominal": nominal
                    })
                    .eq("kategori", kategori)
                    .eq("bulan", str(bulan))
                    .execute()
                )

                status = "✏️ Budget berhasil diperbarui."

            else:

                # INSERT
                (
                    supabase
                    .table("budget")
                    .insert({
                        "kategori": kategori,
                        "bulan": str(bulan),
                        "nominal": nominal
                    })
                    .execute()
                )

                status = "✅ Budget berhasil dibuat."

            nominal_rupiah = (
                f"Rp{nominal:,}"
                .replace(",", ".")
            )

            await update.message.reply_text(
                f"{status}\n\n"
                f"🏷️ Kategori: {kategori}\n"
                f"📅 Bulan: {bulan.strftime('%m/%Y')}\n"
                f"💰 Budget: {nominal_rupiah}"
            )

            return

        # ==========================================
        # MODE LIHAT BUDGET
        # ==========================================

        response = (
            supabase
            .table("budget")
            .select("*")
            .eq("bulan", str(bulan))
            .execute()
        )

        budget_data = response.data

        if not budget_data:

            await update.message.reply_text(
                "💰 BELUM ADA BUDGET\n\n"
                "Buat budget dengan format:\n\n"
                "/budget Makan 900000\n"
                "/budget Bensin 400000"
            )

            return

        # ==========================================
        # AMBIL TRANSAKSI BULAN INI
        # ==========================================

        transaksi_response = (
            supabase
            .table("transaksi")
            .select("kategori, nominal, jenis, tanggal")
            .execute()
        )

        transaksi_data = transaksi_response.data

        pemakaian = {}

        for transaksi in transaksi_data:

            jenis = transaksi.get("jenis", "")
            kategori = transaksi.get("kategori", "")
            nominal_transaksi = transaksi.get("nominal", 0)
            tanggal = transaksi.get("tanggal")

            if jenis.lower() != "pengeluaran":
                continue

            if not tanggal:
                continue

            try:

                tanggal_dt = datetime.fromisoformat(
                    tanggal.replace("Z", "+00:00")
                )

            except (ValueError, TypeError):

                continue

            if (
                tanggal_dt.year != sekarang.year
                or tanggal_dt.month != sekarang.month
            ):
                continue

            try:

                nominal_transaksi = int(nominal_transaksi)

            except (ValueError, TypeError):

                nominal_transaksi = 0

            pemakaian[kategori] = (
                pemakaian.get(kategori, 0)
                + nominal_transaksi
            )

        # ==========================================
        # FORMAT
        # ==========================================

        def rupiah(angka):

            return (
                f"Rp{angka:,}"
                .replace(",", ".")
            )

        pesan = (
            f"💰 BUDGET "
            f"{sekarang.strftime('%B').upper()} "
            f"{sekarang.year}\n\n"
        )

        for item in budget_data:

            kategori = item.get("kategori", "-")
            budget_nominal = item.get("nominal", 0)

            try:

                budget_nominal = int(budget_nominal)

            except (ValueError, TypeError):

                budget_nominal = 0

            terpakai = pemakaian.get(kategori, 0)

            sisa = budget_nominal - terpakai

            if budget_nominal > 0:

                persen = (
                    terpakai / budget_nominal
                ) * 100

            else:

                persen = 0

            # ==========================================
            # STATUS
            # ==========================================

            if sisa < 0:

                status = (
                    f"🚨 MELEBIHI "
                    f"{rupiah(abs(sisa))}"
                )

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

        await update.message.reply_text(
            "❌ Gagal memproses budget.\n\n"
            "Cek PowerShell untuk melihat error."
        )
# ==========================================
# CEK PERINGATAN BUDGET
# ==========================================

async def cek_budget_setelah_transaksi(
    kategori: str,
    jenis: str
):

    try:

        if jenis.lower() != "pengeluaran":
            return None

        sekarang = datetime.now(timezone.utc)

        bulan = sekarang.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        ).date()

        # ==========================================
        # CARI BUDGET
        # ==========================================

        budget_response = (
            supabase
            .table("budget")
            .select("kategori, nominal")
            .eq("bulan", str(bulan))
            .execute()
        )

        budget_data = budget_response.data
        print("DEBUG KATEGORI:", kategori)
        print("DEBUG JENIS:", jenis)
        print("DEBUG BULAN:", bulan)
        print("DEBUG DATA BUDGET:", budget_data)

        budget_item = None

        for item in budget_data:

            if (
                str(item.get("kategori", "")).strip().lower()
                == kategori.strip().lower()
            ):
                budget_item = item
                break

        if not budget_item:
            return None

        budget_nominal = int(
            budget_item.get("nominal", 0)
        )

        # ==========================================
        # AMBIL SEMUA TRANSAKSI
        # ==========================================

        transaksi_response = (
            supabase
            .table("transaksi")
            .select(
                "kategori, nominal, jenis, tanggal"
            )
            .eq("jenis", "Pengeluaran")
            .execute()
        )

        terpakai = 0

        for transaksi in transaksi_response.data:

            transaksi_kategori = str(
                transaksi.get("kategori", "")
            ).strip().lower()

            # Cocokkan kategori tanpa peduli huruf besar/kecil
            if transaksi_kategori != kategori.strip().lower():
                continue

            tanggal = transaksi.get("tanggal")

            if not tanggal:
                continue

            try:

                tanggal_dt = datetime.fromisoformat(
                    tanggal.replace("Z", "+00:00")
                )

            except (ValueError, TypeError):

                continue

            # Pastikan bulan dan tahun sama
            if (
                tanggal_dt.year == sekarang.year
                and tanggal_dt.month == sekarang.month
            ):

                terpakai += int(
                    transaksi.get("nominal", 0)
                )

        # ==========================================
        # HITUNG
        # ==========================================

        if budget_nominal <= 0:
            return None

        persen = (
            terpakai / budget_nominal
        ) * 100

        sisa = budget_nominal - terpakai

        def rupiah(angka):

            return (
                f"Rp{abs(int(angka)):,}"
                .replace(",", ".")
            )

        # ==========================================
        # BUDGET TERLEWATI
        # ==========================================

        if terpakai > budget_nominal:

            return (
                f"\n\n"
                f"🚨 PERINGATAN BUDGET\n\n"
                f"🏷️ {kategori}\n"
                f"💰 Budget: {rupiah(budget_nominal)}\n"
                f"💸 Terpakai: {rupiah(terpakai)}\n"
                f"🔴 Kelebihan: {rupiah(sisa)}\n"
                f"📊 Pemakaian: {persen:.0f}%\n\n"
                f"🚨 Budget kategori ini "
                f"sudah terlewati."
            )

        # ==========================================
        # BUDGET ≥ 80%
        # ==========================================

        if persen >= 80:

            return (
                f"\n\n"
                f"⚠️ PERINGATAN BUDGET\n\n"
                f"🏷️ {kategori}\n"
                f"💰 Budget: {rupiah(budget_nominal)}\n"
                f"💸 Terpakai: {rupiah(terpakai)}\n"
                f"🟢 Sisa: {rupiah(sisa)}\n"
                f"📊 Pemakaian: {persen:.0f}%\n\n"
                f"⚠️ Budget sudah hampir habis."
            )

        return None

    except Exception as e:

        print(
            "ERROR CEK BUDGET:",
            repr(e)
        )

        return None
# ==========================================
# MAIN
# ==========================================
# ==========================================
# LAPORAN BULANAN PRO
# ==========================================

async def laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        # ==========================================
        # WAKTU
        # ==========================================

        sekarang = datetime.now(timezone.utc)

        tahun = sekarang.year
        bulan = sekarang.month

        nama_bulan = [
            "Januari",
            "Februari",
            "Maret",
            "April",
            "Mei",
            "Juni",
            "Juli",
            "Agustus",
            "September",
            "Oktober",
            "November",
            "Desember"
        ][bulan - 1]

        # ==========================================
        # FORMAT RUPIAH
        # ==========================================

        def rupiah(angka):

            angka = int(angka)

            if angka < 0:
                return f"-Rp{abs(angka):,}".replace(",", ".")

            return f"Rp{angka:,}".replace(",", ".")

        # ==========================================
        # AMBIL TRANSAKSI
        # ==========================================

        transaksi_response = (
            supabase
            .table("transaksi")
            .select(
                "id, jenis, kategori, nominal, tanggal"
            )
            .execute()
        )

        data = transaksi_response.data

        pemasukan = 0
        pengeluaran = 0
        jumlah_transaksi = 0

        kategori_pengeluaran = {}

        # ==========================================
        # FILTER TRANSAKSI BULAN BERJALAN
        # ==========================================

        for transaksi in data:

            tanggal = transaksi.get("tanggal")

            if not tanggal:
                continue

            try:

                tanggal_dt = datetime.fromisoformat(
                    tanggal.replace("Z", "+00:00")
                )

            except (ValueError, TypeError):

                continue

            if (
                tanggal_dt.year != tahun
                or tanggal_dt.month != bulan
            ):
                continue

            jumlah_transaksi += 1

            jenis = str(
                transaksi.get("jenis", "")
            ).strip().lower()

            kategori = str(
                transaksi.get("kategori", "Lainnya")
            ).strip()

            try:

                nominal = int(
                    transaksi.get("nominal", 0)
                )

            except (ValueError, TypeError):

                nominal = 0

            # ==========================================
            # PEMASUKAN
            # ==========================================

            if jenis == "pemasukan":

                pemasukan += nominal

            # ==========================================
            # PENGELUARAN
            # ==========================================

            elif jenis == "pengeluaran":

                pengeluaran += nominal

                key = kategori.lower()

                if key not in kategori_pengeluaran:

                    kategori_pengeluaran[key] = {
                        "nama": kategori,
                        "nominal": 0
                    }

                kategori_pengeluaran[key]["nominal"] += nominal

        # ==========================================
        # SALDO
        # ==========================================

        saldo = pemasukan - pengeluaran

        # ==========================================
        # SORT KATEGORI
        # ==========================================

        kategori_sorted = sorted(
            kategori_pengeluaran.values(),
            key=lambda x: x["nominal"],
            reverse=True
        )

        # ==========================================
        # AMBIL BUDGET BULAN INI
        # ==========================================

        tanggal_bulan = (
            f"{tahun}-{bulan:02d}-01"
        )

        budget_response = (
            supabase
            .table("budget")
            .select("kategori, nominal")
            .eq("bulan", tanggal_bulan)
            .execute()
        )

        budget_data = budget_response.data

        # ==========================================
        # BUAT DICTIONARY BUDGET
        # ==========================================

        budget_dict = {}

        for item in budget_data:

            kategori_budget = str(
                item.get("kategori", "")
            ).strip()

            try:

                nominal_budget = int(
                    item.get("nominal", 0)
                )

            except (ValueError, TypeError):

                nominal_budget = 0

            budget_dict[
                kategori_budget.lower()
            ] = {
                "nama": kategori_budget,
                "nominal": nominal_budget
            }

        # ==========================================
        # HEADER LAPORAN
        # ==========================================

        pesan = (
            f"📊 LAPORAN {nama_bulan.upper()} {tahun}\n"
            f"━━━━━━━━━━━━━━━━\n\n"

            f"📥 PEMASUKAN\n"
            f"{rupiah(pemasukan)}\n\n"

            f"💸 PENGELUARAN\n"
            f"{rupiah(pengeluaran)}\n\n"
        )

        # ==========================================
        # SALDO
        # ==========================================

        if saldo > 0:

            pesan += (
                f"💰 SALDO BERSIH\n"
                f"🟢 {rupiah(saldo)}\n\n"
            )

        elif saldo < 0:

            pesan += (
                f"💰 SALDO BERSIH\n"
                f"🔴 {rupiah(saldo)}\n\n"
            )

        else:

            pesan += (
                f"💰 SALDO BERSIH\n"
                f"🟡 {rupiah(saldo)}\n\n"
            )

        # ==========================================
        # JUMLAH TRANSAKSI
        # ==========================================

        pesan += (
            f"📋 TRANSAKSI\n"
            f"{jumlah_transaksi} transaksi\n\n"
        )

        # ==========================================
        # PENGELUARAN PER KATEGORI
        # ==========================================

        if kategori_sorted:

            pesan += (
                "🏷️ PENGELUARAN PER KATEGORI\n\n"
            )

            for item in kategori_sorted:

                nama = item["nama"]
                nominal = item["nominal"]

                if pengeluaran > 0:

                    persen = (
                        nominal
                        / pengeluaran
                    ) * 100

                else:

                    persen = 0

                pesan += (
                    f"• {nama}: "
                    f"{rupiah(nominal)} "
                    f"({persen:.0f}%)\n"
                )

            pesan += "\n"

        else:

            pesan += (
                "🏷️ PENGELUARAN PER KATEGORI\n\n"
                "Belum ada pengeluaran.\n\n"
            )

        # ==========================================
        # PENGELUARAN TERBESAR
        # ==========================================

        if kategori_sorted:

            terbesar = kategori_sorted[0]

            pesan += (
                "🏆 PENGELUARAN TERBESAR\n"
                f"{terbesar['nama']}: "
                f"{rupiah(terbesar['nominal'])}\n\n"
            )

        # ==========================================
        # ANALISIS BUDGET
        # ==========================================

        if budget_dict:

            pesan += (
                "💳 STATUS BUDGET\n\n"
            )

            # Gabungkan kategori budget dan transaksi
            semua_kategori = set(
                list(budget_dict.keys())
                + list(kategori_pengeluaran.keys())
            )

            for key in sorted(semua_kategori):

                nama = key

                budget_nominal = 0
                terpakai = 0

                # Budget
                if key in budget_dict:

                    nama = budget_dict[key]["nama"]
                    budget_nominal = budget_dict[key]["nominal"]

                # Pengeluaran
                if key in kategori_pengeluaran:

                    nama = kategori_pengeluaran[key]["nama"]
                    terpakai = kategori_pengeluaran[key]["nominal"]

                # Jika tidak ada budget
                if budget_nominal <= 0:

                    pesan += (
                        f"• {nama}\n"
                        f"  Terpakai: {rupiah(terpakai)}\n"
                        f"  ⚪ Belum ada budget\n\n"
                    )

                    continue

                sisa = budget_nominal - terpakai

                persen_budget = (
                    terpakai
                    / budget_nominal
                ) * 100

                # ==========================================
                # STATUS
                # ==========================================

                if terpakai > budget_nominal:

                    status = (
                        f"🚨 MELEBIHI "
                        f"{rupiah(abs(sisa))}"
                    )

                elif persen_budget >= 80:

                    status = (
                        "⚠️ MENDEKATI BATAS"
                    )

                else:

                    status = (
                        "🟢 AMAN"
                    )

                pesan += (
                    f"• {nama}\n"
                    f"  Budget: {rupiah(budget_nominal)}\n"
                    f"  Terpakai: {rupiah(terpakai)}\n"
                    f"  Sisa: {rupiah(sisa)}\n"
                    f"  Pemakaian: "
                    f"{persen_budget:.0f}%\n"
                    f"  Status: {status}\n\n"
                )

        else:

            pesan += (
                "💳 STATUS BUDGET\n\n"
                "⚪ Belum ada budget "
                "untuk bulan ini.\n\n"
            )

        # ==========================================
        # STATUS KEUANGAN
        # ==========================================

        pesan += (
            "━━━━━━━━━━━━━━━━\n"
        )

        if saldo > 0:

            pesan += (
                "🟢 KONDISI KEUANGAN\n"
                "Keuangan bulan ini SURPLUS."
            )

        elif saldo < 0:

            pesan += (
                "🔴 KONDISI KEUANGAN\n"
                "Pengeluaran lebih besar "
                "daripada pemasukan."
            )

        else:

            pesan += (
                "🟡 KONDISI KEUANGAN\n"
                "Pemasukan dan pengeluaran "
                "seimbang."
            )

        # ==========================================
        # KIRIM
        # ==========================================

        await update.message.reply_text(pesan)

    except Exception as e:

        print("ERROR LAPORAN:", repr(e))

        await update.message.reply_text(
            "❌ Gagal membuat laporan bulanan.\n\n"
            "Cek PowerShell untuk melihat error."
        )

# ==========================================
# STATISTIK KEUANGAN
# ==========================================

async def statistik(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        sekarang = datetime.now(timezone.utc)

        tahun = sekarang.year
        bulan = sekarang.month

        nama_bulan = [
            "Januari", "Februari", "Maret", "April",
            "Mei", "Juni", "Juli", "Agustus",
            "September", "Oktober", "November", "Desember"
        ][bulan - 1]

        # ==========================================
        # AMBIL TRANSAKSI
        # ==========================================

        response = (
            supabase
            .table("transaksi")
            .select("id, jenis, kategori, nominal, tanggal")
            .execute()
        )

        data = response.data

        pemasukan = 0
        pengeluaran = 0

        jumlah_pemasukan = 0
        jumlah_pengeluaran = 0

        kategori_pengeluaran = {}

        # ==========================================
        # FILTER BULAN BERJALAN
        # ==========================================

        for transaksi in data:

            tanggal = transaksi.get("tanggal")

            if not tanggal:
                continue

            try:
                tanggal_dt = datetime.fromisoformat(
                    tanggal.replace("Z", "+00:00")
                )

            except (ValueError, TypeError):
                continue

            if (
                tanggal_dt.year != tahun
                or tanggal_dt.month != bulan
            ):
                continue

            jenis = str(
                transaksi.get("jenis", "")
            ).strip().lower()

            kategori = str(
                transaksi.get("kategori", "Lainnya")
            ).strip()

            try:
                nominal = int(
                    transaksi.get("nominal", 0)
                )
            except (ValueError, TypeError):
                nominal = 0

            # ==========================================
            # PEMASUKAN
            # ==========================================

            if jenis == "pemasukan":

                pemasukan += nominal
                jumlah_pemasukan += 1

            # ==========================================
            # PENGELUARAN
            # ==========================================

            elif jenis == "pengeluaran":

                pengeluaran += nominal
                jumlah_pengeluaran += 1

                kategori_key = kategori.lower()

                if kategori_key not in kategori_pengeluaran:

                    kategori_pengeluaran[kategori_key] = {
                        "nama": kategori,
                        "nominal": 0
                    }

                kategori_pengeluaran[
                    kategori_key
                ]["nominal"] += nominal

        # ==========================================
        # PERHITUNGAN
        # ==========================================

        total_transaksi = (
            jumlah_pemasukan
            + jumlah_pengeluaran
        )

        if jumlah_pengeluaran > 0:

            rata_pengeluaran = (
                pengeluaran / jumlah_pengeluaran
            )

        else:

            rata_pengeluaran = 0

        saldo_bersih = (
            pemasukan - pengeluaran
        )

        # ==========================================
        # FORMAT RUPIAH
        # ==========================================

        def rupiah(angka):

            return (
                f"Rp{int(angka):,}"
                .replace(",", ".")
            )

        # ==========================================
        # KATEGORI TERBOROS
        # ==========================================

        kategori_sorted = sorted(
            kategori_pengeluaran.values(),
            key=lambda x: x["nominal"],
            reverse=True
        )

        # ==========================================
        # BUAT PESAN
        # ==========================================

        pesan = (
            f"📈 STATISTIK KEUANGAN\n"
            f"━━━━━━━━━━━━━━━━\n\n"

            f"📅 {nama_bulan} {tahun}\n\n"

            f"💰 TOTAL PEMASUKAN\n"
            f"{rupiah(pemasukan)}\n\n"

            f"💸 TOTAL PENGELUARAN\n"
            f"{rupiah(pengeluaran)}\n\n"

            f"📊 RATA-RATA PENGELUARAN\n"
            f"{rupiah(rata_pengeluaran)} / transaksi\n\n"

            f"📋 TRANSAKSI\n"
            f"📥 Pemasukan   : {jumlah_pemasukan}\n"
            f"💸 Pengeluaran : {jumlah_pengeluaran}\n"
            f"📊 Total       : {total_transaksi}\n\n"
        )

        # ==========================================
        # KATEGORI TERBOROS
        # ==========================================

        if kategori_sorted:

            terbesar = kategori_sorted[0]

            nama_terbesar = terbesar["nama"]
            nominal_terbesar = terbesar["nominal"]

            if pengeluaran > 0:

                persen_terbesar = (
                    nominal_terbesar
                    / pengeluaran
                ) * 100

            else:

                persen_terbesar = 0

            pesan += (
                f"🏆 KATEGORI TERBOROS\n"
                f"🏷️ {nama_terbesar}\n"
                f"{rupiah(nominal_terbesar)} "
                f"({persen_terbesar:.0f}%)\n\n"
            )

        # ==========================================
        # ANALISIS KEUANGAN
        # ==========================================

        pesan += "⚠️ ANALISIS\n"

        if total_transaksi == 0:

            pesan += (
                "Belum ada transaksi "
                "pada bulan ini."
            )

        elif pengeluaran > pemasukan:

            pesan += (
                "Pengeluaran kamu lebih besar "
                "daripada pemasukan bulan ini.\n\n"
                "💡 Perhatikan pengeluaran "
                "terutama pada kategori terbesar."
            )

        elif pengeluaran == pemasukan:

            pesan += (
                "Pemasukan dan pengeluaran "
                "berada pada jumlah yang sama.\n\n"
                "💡 Usahakan mulai menyisihkan "
                "sebagian pemasukan untuk tabungan."
            )

        else:

            pesan += (
                "Kondisi keuangan bulan ini "
                "masih positif.\n\n"
                "💡 Pertahankan pengeluaran "
                "agar tetap di bawah pemasukan."
            )

        # ==========================================
        # RESPONSE
        # ==========================================

        pesan += (
            "\n━━━━━━━━━━━━━━━━"
        )

        await update.message.reply_text(pesan)

    except Exception as e:

        print("ERROR STATISTIK:", e)

        await update.message.reply_text(
            "❌ Gagal membuat statistik.\n\n"
            "Cek PowerShell untuk melihat error."
        )

# ==========================================
# KATEGORI PENGELUARAN
# ==========================================

async def kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        sekarang = datetime.now(timezone.utc)

        tahun = sekarang.year
        bulan = sekarang.month

        nama_bulan = [
            "Januari", "Februari", "Maret", "April",
            "Mei", "Juni", "Juli", "Agustus",
            "September", "Oktober", "November", "Desember"
        ][bulan - 1]

        # ==========================================
        # FILTER KATEGORI
        # ==========================================

        kategori_filter = None

        if context.args:
            kategori_filter = " ".join(context.args).strip().lower()

        # ==========================================
        # AMBIL TRANSAKSI
        # ==========================================

        response = (
            supabase
            .table("transaksi")
            .select("id, jenis, kategori, nominal, tanggal")
            .eq("jenis", "Pengeluaran")
            .execute()
        )

        data = response.data

        kategori_data = {}

        # ==========================================
        # FILTER BULAN
        # ==========================================

        for transaksi in data:

            tanggal = transaksi.get("tanggal")

            if not tanggal:
                continue

            try:

                tanggal_dt = datetime.fromisoformat(
                    tanggal.replace("Z", "+00:00")
                )

            except (ValueError, TypeError):

                continue

            if (
                tanggal_dt.year != tahun
                or tanggal_dt.month != bulan
            ):
                continue

            nama_kategori = str(
                transaksi.get("kategori", "Lainnya")
            ).strip()

            # ==========================================
            # FILTER KATEGORI TERTENTU
            # ==========================================

            if kategori_filter:

                if nama_kategori.lower() != kategori_filter:
                    continue

            try:

                nominal = int(
                    transaksi.get("nominal", 0)
                )

            except (ValueError, TypeError):

                nominal = 0

            key = nama_kategori.lower()

            if key not in kategori_data:

                kategori_data[key] = {
                    "nama": nama_kategori,
                    "nominal": 0,
                    "jumlah": 0
                }

            kategori_data[key]["nominal"] += nominal
            kategori_data[key]["jumlah"] += 1

        # ==========================================
        # BELUM ADA DATA
        # ==========================================

        if not kategori_data:

            if kategori_filter:

                await update.message.reply_text(
                    f"📊 KATEGORI {kategori_filter.upper()}\n\n"
                    f"📅 {nama_bulan} {tahun}\n\n"
                    "⚪ Belum ada pengeluaran "
                    "untuk kategori ini."
                )

            else:

                await update.message.reply_text(
                    f"📊 PENGELUARAN PER KATEGORI\n\n"
                    f"📅 {nama_bulan} {tahun}\n\n"
                    "⚪ Belum ada pengeluaran "
                    "bulan ini."
                )

            return

        # ==========================================
        # SORTING
        # ==========================================

        kategori_sorted = sorted(
            kategori_data.values(),
            key=lambda x: x["nominal"],
            reverse=True
        )

        total_pengeluaran = sum(
            item["nominal"]
            for item in kategori_sorted
        )

        # ==========================================
        # FORMAT RUPIAH
        # ==========================================

        def rupiah(angka):

            return (
                f"Rp{int(angka):,}"
                .replace(",", ".")
            )

        # ==========================================
        # HEADER
        # ==========================================

        if kategori_filter:

            pesan = (
                f"📊 DETAIL KATEGORI\n"
                f"━━━━━━━━━━━━━━━━\n\n"
                f"🏷️ {kategori_sorted[0]['nama']}\n"
                f"📅 {nama_bulan} {tahun}\n\n"
            )

        else:

            pesan = (
                f"📊 PENGELUARAN PER KATEGORI\n"
                f"━━━━━━━━━━━━━━━━\n\n"
                f"📅 {nama_bulan} {tahun}\n\n"
            )

        # ==========================================
        # DETAIL KATEGORI
        # ==========================================

        for item in kategori_sorted:

            nama = item["nama"]
            nominal = item["nominal"]
            jumlah = item["jumlah"]

            if total_pengeluaran > 0:

                persen = (
                    nominal
                    / total_pengeluaran
                ) * 100

            else:

                persen = 0

            # Progress bar sederhana
            jumlah_bar = int(persen / 5)

            if jumlah_bar < 1 and persen > 0:
                jumlah_bar = 1

            bar = "█" * jumlah_bar

            pesan += (
                f"🏷️ {nama}\n"
                f"💸 {rupiah(nominal)}\n"
                f"{bar} {persen:.0f}%\n"
                f"📋 {jumlah} transaksi\n\n"
            )

        # ==========================================
        # TOTAL
        # ==========================================

        pesan += (
            f"━━━━━━━━━━━━━━━━\n"
            f"💰 TOTAL PENGELUARAN\n"
            f"{rupiah(total_pengeluaran)}\n\n"
        )

        # ==========================================
        # KATEGORI TERBESAR
        # ==========================================

        if not kategori_filter:

            terbesar = kategori_sorted[0]

            pesan += (
                f"🏆 TERBESAR\n"
                f"{terbesar['nama']} — "
                f"{rupiah(terbesar['nominal'])}\n\n"
            )

        # ==========================================
        # JUMLAH KATEGORI
        # ==========================================

        pesan += (
            f"📌 JUMLAH KATEGORI\n"
            f"{len(kategori_sorted)} kategori"
        )

        # ==========================================
        # RESPONSE
        # ==========================================

        await update.message.reply_text(pesan)

    except Exception as e:

        print("ERROR KATEGORI:", e)

        await update.message.reply_text(
            "❌ Gagal mengambil data kategori.\n\n"
            "Cek PowerShell untuk melihat error."
        )

# ==========================================
# TAMBAH TARGET KEUANGAN
# ==========================================

async def target(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        # ==========================================
        # CEK FORMAT
        # ==========================================

        if len(context.args) < 2:

            await update.message.reply_text(
                "❌ Format salah.\n\n"
                "Gunakan:\n"
                "/target [Nama Target] [Nominal Target] [Setoran Bulanan]\n\n"
                "Contoh:\n"
                "/target Laptop 6000000 500000\n"
                "/target Liburan 3000000 300000"
            )

            return

        # ==========================================
        # NAMA TARGET
        # ==========================================

        nama_target = context.args[0].strip()

        # ==========================================
        # NOMINAL TARGET
        # ==========================================

        try:

            target_nominal = int(context.args[1])

        except ValueError:

            await update.message.reply_text(
                "❌ Nominal target harus berupa angka.\n\n"
                "Contoh:\n"
                "/target Laptop 6000000 500000"
            )

            return

        # ==========================================
        # SETORAN BULANAN
        # ==========================================

        if len(context.args) >= 3:

            try:

                setoran_bulanan = int(context.args[2])

            except ValueError:

                await update.message.reply_text(
                    "❌ Setoran bulanan harus berupa angka.\n\n"
                    "Contoh:\n"
                    "/target Laptop 6000000 500000"
                )

                return

        else:

            setoran_bulanan = 0

        # ==========================================
        # VALIDASI NOMINAL
        # ==========================================

        if target_nominal <= 0:

            await update.message.reply_text(
                "❌ Nominal target harus lebih dari 0."
            )

            return

        if setoran_bulanan < 0:

            await update.message.reply_text(
                "❌ Setoran bulanan tidak boleh negatif."
            )

            return

        # ==========================================
        # CEK TARGET DUPLIKAT
        # ==========================================

        existing = (
            supabase
            .table("target_keuangan")
            .select("id, nama_target")
            .ilike("nama_target", nama_target)
            .execute()
        )

        if existing.data:

            await update.message.reply_text(
                f"⚠️ Target '{nama_target}' sudah ada.\n\n"
                "Gunakan nama target yang berbeda."
            )

            return

        # ==========================================
        # SIMPAN TARGET
        # ==========================================

        response = (
            supabase
            .table("target_keuangan")
            .insert({
                "nama_target": nama_target,
                "target_nominal": target_nominal,
                "terkumpul": 0,
                "setoran_bulanan": setoran_bulanan
            })
            .execute()
        )

        if not response.data:

            await update.message.reply_text(
                "❌ Target gagal disimpan."
            )

            return

        data = response.data[0]

        target_id = data.get("id")

        # ==========================================
        # FORMAT RUPIAH
        # ==========================================

        def rupiah(angka):

            return (
                f"Rp{int(angka):,}"
                .replace(",", ".")
            )

        # ==========================================
        # RESPONSE
        # ==========================================

        await update.message.reply_text(

            f"🎯 TARGET BERHASIL DIBUAT\n"
            f"━━━━━━━━━━━━━━━━\n\n"

            f"🆔 ID: {target_id}\n"
            f"🏷️ Target: {nama_target}\n"
            f"💰 Target Nominal: "
            f"{rupiah(target_nominal)}\n"
            f"💵 Terkumpul: "
            f"{rupiah(0)}\n"
            f"📥 Setoran/Bulan: "
            f"{rupiah(setoran_bulanan)}\n\n"

            f"📊 Progress: 0%\n\n"

            f"💡 Gunakan /setor nanti "
            f"untuk menambahkan uang ke target."
        )

    except Exception as e:

        print("ERROR TARGET:", e)

        await update.message.reply_text(
            "❌ Gagal membuat target.\n\n"
            "Cek PowerShell untuk melihat error."
        )


# ==========================================
# SETOR KE TARGET KEUANGAN
# ==========================================

async def setor(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        # ==========================================
        # CEK FORMAT
        # ==========================================

        if len(context.args) != 2:

            await update.message.reply_text(
                "❌ Format salah.\n\n"
                "Gunakan:\n"
                "/setor [ID Target] [Nominal]\n\n"
                "Contoh:\n"
                "/setor 1 500000"
            )

            return

        # ==========================================
        # ID TARGET
        # ==========================================

        try:

            target_id = int(context.args[0])

        except ValueError:

            await update.message.reply_text(
                "❌ ID target harus berupa angka.\n\n"
                "Contoh:\n"
                "/setor 1 500000"
            )

            return

        # ==========================================
        # NOMINAL SETORAN
        # ==========================================

        try:

            nominal_setoran = int(context.args[1])

        except ValueError:

            await update.message.reply_text(
                "❌ Nominal setoran harus berupa angka.\n\n"
                "Contoh:\n"
                "/setor 1 500000"
            )

            return

        # ==========================================
        # VALIDASI NOMINAL
        # ==========================================

        if nominal_setoran <= 0:

            await update.message.reply_text(
                "❌ Nominal setoran harus lebih dari 0."
            )

            return

        # ==========================================
        # CARI TARGET
        # ==========================================

        response = (
            supabase
            .table("target_keuangan")
            .select(
                "id, nama_target, target_nominal, "
                "terkumpul, setoran_bulanan"
            )
            .eq("id", target_id)
            .execute()
        )

        if not response.data:

            await update.message.reply_text(
                f"❌ Target dengan ID {target_id} "
                "tidak ditemukan."
            )

            return

        target_data = response.data[0]

        nama_target = target_data.get(
            "nama_target",
            "-"
        )

        target_nominal = int(
            target_data.get(
                "target_nominal",
                0
            )
        )

        terkumpul_lama = int(
            target_data.get(
                "terkumpul",
                0
            )
        )

        setoran_bulanan = int(
            target_data.get(
                "setoran_bulanan",
                0
            )
        )

        # ==========================================
        # HITUNG TERKUMPUL BARU
        # ==========================================

        terkumpul_baru = (
            terkumpul_lama
            + nominal_setoran
        )

        # Jangan biarkan progress lebih dari 100%
        progress = (
            terkumpul_baru
            / target_nominal
        ) * 100

        if progress > 100:
            progress = 100

        kekurangan = (
            target_nominal
            - terkumpul_baru
        )

        if kekurangan < 0:
            kekurangan = 0

        # ==========================================
        # UPDATE DATABASE
        # ==========================================

        update_response = (
            supabase
            .table("target_keuangan")
            .update({
                "terkumpul": terkumpul_baru
            })
            .eq("id", target_id)
            .execute()
        )

        if not update_response.data:

            await update.message.reply_text(
                "❌ Gagal memperbarui target."
            )

            return

        # ==========================================
        # FORMAT RUPIAH
        # ==========================================

        def rupiah(angka):

            return (
                f"Rp{int(angka):,}"
                .replace(",", ".")
            )

        # ==========================================
        # STATUS TARGET
        # ==========================================

        if terkumpul_baru >= target_nominal:

            status = (
                "🎉 TARGET TERCAPAI!\n\n"
                "Selamat bro! Target keuangan "
                "ini sudah tercapai. 🔥"
            )

        elif progress >= 75:

            status = "🔥 Hampir tercapai!"

        elif progress >= 50:

            status = "💪 Lebih dari setengah jalan!"

        elif progress >= 25:

            status = "🚀 Progress bagus!"

        else:

            status = "🌱 Baru mulai, tetap konsisten!"

        # ==========================================
        # PROGRESS BAR
        # ==========================================

        jumlah_bar = int(progress / 10)

        if jumlah_bar > 10:
            jumlah_bar = 10

        bar = (
            "█" * jumlah_bar
            + "░" * (10 - jumlah_bar)
        )

        # ==========================================
        # RESPONSE
        # ==========================================

        await update.message.reply_text(

            f"💰 SETORAN BERHASIL\n"
            f"━━━━━━━━━━━━━━━━\n\n"

            f"🆔 ID Target: {target_id}\n"
            f"🏷️ Target: {nama_target}\n\n"

            f"💵 Setoran: "
            f"{rupiah(nominal_setoran)}\n"
            f"💰 Terkumpul: "
            f"{rupiah(terkumpul_baru)}\n"
            f"🎯 Target: "
            f"{rupiah(target_nominal)}\n"
            f"📉 Kekurangan: "
            f"{rupiah(kekurangan)}\n\n"

            f"📊 Progress\n"
            f"{bar} {progress:.0f}%\n\n"

            f"{status}"
        )

    except Exception as e:

        print("ERROR SETOR:", e)

        await update.message.reply_text(
            "❌ Gagal melakukan setoran.\n\n"
            "Cek PowerShell untuk melihat error."
        )

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

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            konfirmasi_semua
        )
    )
    print("Finance Bot berjalan...")

    app.run_polling()


if __name__ == "__main__":
    main()